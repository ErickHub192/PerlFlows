import time
import json
import logging
import hashlib
import re
import asyncio
from typing import Any, Dict, List, Optional
from contextvars import ContextVar

from jsonschema import validate, ValidationError
from redis.asyncio import Redis

from app.exceptions.llm_exceptions import JSONParsingException, LLMConnectionException
from app.exceptions.api_exceptions import WorkflowProcessingException
from app.core.config import settings
from app.ai.llm_clients.protocol import LLMClientProtocol
from app.ai.llm_factory import LLMClientFactory
from app.schemas.validation_schemas import LLM_RESPONSE_SCHEMA, PLAN_SCHEMA

# Context variables for token tracking
_token_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar('token_context', default=None)

# --- Redis helper (lazy singleton) ---
_redis: Optional[Redis] = None

async def get_redis() -> Redis:
    """Devuelve una conexión redis.asyncio.Redis reutilizable con health check."""
    global _redis
    if _redis is None or not await _redis.ping():
        if _redis:
            await _redis.close()
        _redis = Redis.from_url(settings.REDIS_URL, health_check_interval=30)
    return _redis


@LLMClientFactory.register
class LLMService:
    """
    Servicio que orquesta llamadas al LLM con caché Redis:
      1) Reconstruye el prompt completo.
      2) Busca en Redis por SHA256(prompt).
      3) Si hay hit, devuelve el valor cacheado.
      4) Si no, invoca al LLM, valida la respuesta y la guarda en Redis.
      5) Mide latencia e incluye _llm_duration_ms en la salida.
    """

    def __init__(self, api_key: str, model: str, model_info: dict = None):
        self.logger = logging.getLogger(__name__)
        self.model = model
        self.client: LLMClientProtocol = LLMClientFactory.create(api_key, model)
        self.embed_model: str = getattr(settings, "DEFAULT_EMBED_MODEL", settings.DEFAULT_EMBED_MODEL)
        self.model_info = model_info  # Can be pre-populated or loaded later
        self.usage_tracker = None  # Optional usage tracking

        if not self.embed_model:
            self.logger.warning(
                "No EMBED_MODEL configurado, se usará %s", settings.DEFAULT_EMBED_MODEL
            )

    async def load_model_info(self):
        """
        Load model information from database via LLMClientFactory
        """
        try:
            self.model_info = await LLMClientFactory.get_model_info(self.model)
            if self.model_info:
                self.logger.info(f"Loaded model info for {self.model}: {self.model_info['display_name']}")
        except Exception as e:
            self.logger.warning(f"Could not load model info for {self.model}: {e}")

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost for token usage using model info
        """
        if not self.model_info:
            return 0.0
        
        input_cost = (input_tokens / 1000) * self.model_info.get('input_cost_per_1k', 0)
        output_cost = (output_tokens / 1000) * self.model_info.get('output_cost_per_1k', 0)
        return input_cost + output_cost

    def extract_token_usage(self, llm_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract token usage from LLM response and calculate cost
        """
        usage_info = {
            'input_tokens': 0,
            'output_tokens': 0,
            'total_tokens': 0,
            'cost': 0.0
        }
        
        # Try to extract from OpenAI-style response
        if 'usage' in llm_response:
            usage = llm_response['usage']
            usage_info.update({
                'input_tokens': usage.get('prompt_tokens', 0),
                'output_tokens': usage.get('completion_tokens', 0),
                'total_tokens': usage.get('total_tokens', 0)
            })
        
        # Calculate cost if we have model info
        if usage_info['input_tokens'] or usage_info['output_tokens']:
            usage_info['cost'] = self.calculate_cost(
                usage_info['input_tokens'],
                usage_info['output_tokens']
            )
        
        return usage_info
    
    def enable_usage_tracking(self):
        """Enable usage tracking for this LLM service instance"""
        from app.services.agent_execution_service import TokenUsageTracker
        self.usage_tracker = TokenUsageTracker()
        return self.usage_tracker
    
    async def run_with_tracking(
        self,
        system_prompt: str,
        short_term: List[Dict[str, Any]],
        long_term: List[Dict[str, Any]],
        user_prompt: str,
        temperature: float = 0.0,
        mode: str = None
    ) -> Dict[str, Any]:
        """
        Run LLM with integrated usage tracking - eliminates need for CostTrackingLLMService
        """
        import time
        
        start_time = time.time()
        
        try:
            # Load model info if not already loaded
            if self.model_info is None:
                await self.load_model_info()
            
            # Call the original run method
            result = await self.run(
                system_prompt=system_prompt,
                short_term=short_term,
                long_term=long_term,
                user_prompt=user_prompt,
                temperature=temperature,
                mode=mode
            )
            
            # Extract token usage and calculate cost
            usage_info = self.extract_token_usage(result)
            
            # Track usage if tracker is enabled
            if self.usage_tracker:
                self.usage_tracker.add_request(
                    usage_info['input_tokens'],
                    usage_info['output_tokens'],
                    usage_info['cost']
                )
            
            # Add usage info to result
            result['_token_usage'] = {
                **usage_info,
                'duration_seconds': time.time() - start_time
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in run_with_tracking: {e}")
            raise

    async def run(
        self,
        system_prompt: str,
        short_term: List[Dict[str, Any]],
        long_term: List[Dict[str, Any]],
        user_prompt: str,
        temperature: float = 0.0,
        mode: str | None = None,
        tools: List[Dict[str, Any]] | None = None
    ) -> Dict[str, Any]:
        if short_term is None or long_term is None:
            raise ValueError("short_term y long_term deben ser listas, no None")

        logger = self.logger
        start = time.perf_counter()

        # 1) Construcción de mensajes
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                *[{"role": m.get("role", "assistant"), "content": m["result"]} for m in short_term],
                *[{"role": m.get("role", "assistant"), "content": m["result"]} for m in long_term],
                {"role": "user", "content": user_prompt},
            ]
        except (KeyError, TypeError) as e:
            logger.error("Error construyendo mensajes: %s", e, exc_info=True)
            raise WorkflowProcessingException(f"Error construyendo mensajes para LLM: {e}")

        # 2) Cache lookup en Redis
        payload = json.dumps({
            "system": system_prompt,
            "short": [m["result"] for m in short_term],
            "long":  [m["result"] for m in long_term],
            "user":  user_prompt,
            "temp":  temperature,
            "mode":  mode,
            "tools": tools,
        }, sort_keys=True, ensure_ascii=False)
        cache_key = "llm:" + hashlib.sha256(payload.encode()).hexdigest()
        redis = await get_redis()
        try:
            cached = await redis.get(cache_key)
        except Exception as e:
            logger.warning("Error leyendo cache Redis: %s", e, exc_info=True)
            cached = None

        if cached:
            logger.info("LLMService cache HIT %s", cache_key)
            return json.loads(cached)

        # 3) Si no hay caché, invocar al LLM
        call_args: Dict[str, Any] = {
            "messages": messages,
            "temperature": temperature,
        }
        if mode is not None:
            call_args["mode"] = mode
        if tools is not None:
            call_args["tools"] = tools
        logger.debug("LLMService run payload:\n%s", json.dumps(call_args, indent=2, ensure_ascii=False))

        try:
            response = await self.client.chat_completion(**call_args)
            
            # 🎯 INTERCEPTAR TOKENS AUTOMÁTICAMENTE
            await self._process_token_usage(response)
            
            # 🔧 NUEVO: Debug de function calls
            logger.info(f"🔧 Response received, tools provided: {tools is not None}")
            if tools:
                logger.info(f"🔧 {len(tools)} tools were available to LLM:")
                for tool in tools:
                    logger.info(f"  - {tool['function']['name']}")
                    
                has_tool_calls = self._has_tool_calls(response)
                logger.info(f"🔧 LLM used function calls: {has_tool_calls}")
                
                if has_tool_calls:
                    content = await self._handle_function_calls(response, messages, call_args)
                    logger.info("✅ Function calls executed successfully")
                else:
                    content = self._extract_llm_content(response)
                    logger.warning(f"❌ LLM IGNORED function tools! Responded directly with {len(content)} chars")
                    logger.warning(f"🔧 Response preview: {content[:200]}...")
            else:
                content = self._extract_llm_content(response)
                logger.info("🔧 No tools provided, using direct response")
                
        except JSONParsingException:
            # Propagamos el error de parseo específico
            raise
        except Exception as e:
            logger.error("Error conectando al LLM: %s", e, exc_info=True)
            raise LLMConnectionException(f"Error conectando al LLM: {e}")

        # 4) Parseo y validación de JSON
        try:
            output = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error("LLM response not valid JSON: %s\nContent: %.500s", e, content, exc_info=True)
            raise JSONParsingException(f"LLM response not valid JSON: {e}")

        # a) NodeSelectionService: omitimos validación
        if "nodes" in output and "questions" in output:
            logger.debug("NodeSelectionService output: skipping schema validation")

        # b) Orchestrator solo plan
        elif "steps" in output and "final_output" not in output:
            try:
                validate(instance=output, schema=PLAN_SCHEMA)
            except ValidationError as e:
                logger.error("Plan schema validation failed: %s\nOutput: %.500s", e, json.dumps(output), exc_info=True)
                raise WorkflowProcessingException(f"Plan schema validation failed: {e}")

        # c) Orchestrator plan + resultado final
        elif "steps" in output and "final_output" in output:
            try:
                validate(instance=output, schema=LLM_RESPONSE_SCHEMA)
            except ValidationError as e:
                logger.error("Full schema validation failed: %s\nOutput: %.500s", e, json.dumps(output), exc_info=True)
                raise WorkflowProcessingException(f"Full schema validation failed: {e}")

        else:
            logger.warning("Unexpected response format, keys=%s", list(output.keys()))

        # 5) Medición de latencia
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info("LLM run took %d ms", duration_ms)
        output["_llm_duration_ms"] = duration_ms

        # 6) Almacenar en caché en Redis
        try:
            await redis.set(
                cache_key,
                json.dumps(output, ensure_ascii=False),
                ex=settings.CACHE_TTL_SECONDS
            )
            logger.info("LLMService cache SET %s (TTL %ds)", cache_key, settings.CACHE_TTL_SECONDS)
        except Exception as e:
            logger.warning("Error guardando cache Redis: %s", e, exc_info=True)

        return output
    
    async def _process_token_usage(self, response: Any):
        """
        🎯 INTERCEPTOR AUTOMÁTICO DE TOKENS
        Procesa automáticamente el uso de tokens y lo registra si hay contexto activo
        """
        try:
            # Obtener contexto de tracking si existe
            context = _token_context.get()
            if not context:
                return  # No hay contexto de tracking activo
            
            # Extraer información de tokens
            token_info = self._extract_tokens_from_response(response)
            if not token_info or token_info.get("total_tokens", 0) == 0:
                return  # No hay tokens para procesar
            
            # Registrar tokens en background
            asyncio.create_task(self._record_token_usage_async(token_info, context))
            
            self.logger.info(f"📊 Auto-tracked {token_info['total_tokens']} tokens for user {context.get('user_id')}")
            
        except Exception as e:
            self.logger.error(f"❌ Error in token auto-tracking: {e}")
    
    def _extract_tokens_from_response(self, response: Any) -> Optional[Dict[str, Any]]:
        """
        Extrae tokens de la respuesta del LLM en diferentes formatos
        """
        try:
            # OpenAI format
            if hasattr(response, "usage"):
                usage = response.usage
                return {
                    "input_tokens": getattr(usage, "prompt_tokens", 0),
                    "output_tokens": getattr(usage, "completion_tokens", 0), 
                    "total_tokens": getattr(usage, "total_tokens", 0),
                    "model": getattr(response, "model", self.model)
                }
            
            # Dict format
            if isinstance(response, dict) and "usage" in response:
                usage = response["usage"]
                return {
                    "input_tokens": usage.get("prompt_tokens", 0),
                    "output_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                    "model": response.get("model", self.model)
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting tokens: {e}")
            return None
    
    async def _record_token_usage_async(self, token_info: Dict[str, Any], context: Dict[str, Any]):
        """
        Registra el uso de tokens de forma asíncrona usando el TokenManager
        """
        try:
            # Importar aquí para evitar circular imports
            from app.core.token_system import get_token_manager
            from app.core.token_manager import TokenUsage, OperationType
            
            token_manager = get_token_manager()
            
            # Crear objeto de uso
            usage = TokenUsage(
                input_tokens=token_info["input_tokens"],
                output_tokens=token_info["output_tokens"],
                model_used=token_info.get("model", self.model),
                operation_type=OperationType(context.get("operation_type", "workflow")),
                user_id=context["user_id"],
                workflow_id=context.get("workflow_id"),
                execution_id=context.get("execution_id")
            )
            
            # Registrar uso
            await token_manager.record_usage(usage)
            
        except Exception as e:
            self.logger.error(f"Error recording token usage: {e}")

    def _has_tool_calls(self, response: Any) -> bool:
        """
        Verifica si la respuesta del LLM contiene function calls
        """
        try:
            # OpenAI response format
            if hasattr(response, "choices") and response.choices:
                message = response.choices[0].message
                return hasattr(message, "tool_calls") and message.tool_calls is not None
            
            # Dict response format    
            if isinstance(response, dict) and "choices" in response:
                choice = response["choices"][0]
                if "message" in choice:
                    return "tool_calls" in choice["message"] and choice["message"]["tool_calls"] is not None
                    
            return False
        except (IndexError, KeyError, AttributeError):
            return False
    
    async def _handle_function_calls(self, response: Any, original_messages: List[Dict], call_args: Dict) -> str:
        """
        Maneja function calls del LLM ejecutando las funciones y obteniendo respuesta final
        """
        logger = self.logger
        
        try:
            # Extraer tool calls de la respuesta
            tool_calls = self._extract_tool_calls(response)
            logger.info(f"🔧 LLM hizo {len(tool_calls)} function calls")
            
            # Agregar el mensaje del assistant con tool calls
            assistant_message = {
                "role": "assistant", 
                "content": None,
                "tool_calls": tool_calls
            }
            
            # Ejecutar cada function call y recopilar resultados
            tool_messages = []
            for tool_call in tool_calls:
                try:
                    result = await self._execute_function_call(tool_call)
                    tool_messages.append({
                        "role": "tool",
                        "content": json.dumps(result, ensure_ascii=False),
                        "tool_call_id": tool_call.get("id", "")
                    })
                    logger.info(f"✅ Function call {tool_call['function']['name']} ejecutado exitosamente")
                except Exception as e:
                    logger.error(f"❌ Error ejecutando function call {tool_call['function']['name']}: {e}")
                    tool_messages.append({
                        "role": "tool", 
                        "content": json.dumps({"error": str(e)}, ensure_ascii=False),
                        "tool_call_id": tool_call.get("id", "")
                    })
            
            # Construir mensajes actualizados para segunda llamada
            updated_messages = original_messages + [assistant_message] + tool_messages
            
            # Segunda llamada al LLM con los resultados de las funciones
            follow_up_args = {**call_args}
            follow_up_args["messages"] = updated_messages
            
            logger.info("🔄 Haciendo segunda llamada al LLM con resultados de function calls")
            follow_up_response = await self.client.chat_completion(**follow_up_args)
            
            return self._extract_llm_content(follow_up_response)
            
        except Exception as e:
            logger.error(f"❌ Error procesando function calls: {e}")
            raise
    
    def _extract_tool_calls(self, response: Any) -> List[Dict]:
        """
        Extrae tool calls de la respuesta del LLM
        """
        try:
            # OpenAI response format
            if hasattr(response, "choices") and response.choices:
                message = response.choices[0].message
                if hasattr(message, "tool_calls") and message.tool_calls:
                    return [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in message.tool_calls
                    ]
            
            # Dict response format
            if isinstance(response, dict) and "choices" in response:
                choice = response["choices"][0]
                if "message" in choice and "tool_calls" in choice["message"]:
                    return choice["message"]["tool_calls"]
                    
            return []
        except (IndexError, KeyError, AttributeError):
            return []
    
    async def _execute_function_call(self, tool_call: Dict) -> Dict:
        """
        Ejecuta un function call específico
        """
        function_name = tool_call["function"]["name"]
        arguments = tool_call["function"]["arguments"]
        
        # Parse arguments si es string JSON
        if isinstance(arguments, str):
            try:
                parsed_args = json.loads(arguments)
            except json.JSONDecodeError:
                parsed_args = {}
        else:
            parsed_args = arguments or {}
        
        # Ejecutar la función usando el factory de handlers
        from app.connectors.factory import get_registered_handlers
        handlers = get_registered_handlers()
        
        if function_name not in handlers:
            raise ValueError(f"Function {function_name} not found in registered handlers")
        
        handler_class = handlers[function_name]
        handler_instance = handler_class({})  # Empty creds for now
        
        return await handler_instance.execute(parsed_args, {})

    def _extract_llm_content(self, response: Any) -> str:
        """
        Extrae el contenido de la respuesta del LLM de manera generalizada.
        Maneja diferentes formatos de respuesta según el proveedor.
        """
        try:
            # Debug: Log response structure
            self.logger.debug(f"🔧 Extracting content from response type: {type(response)}")
            
            # Compatibilidad con OpenAI
            if hasattr(response, "choices") and hasattr(response.choices[0], "message"):
                content = response.choices[0].message.content or ""
                self.logger.debug(f"🔧 OpenAI format content length: {len(content)}")
                if not content:
                    self.logger.warning(f"🔧 Empty content in OpenAI response. Message: {response.choices[0].message}")
                return content

            # Compatibilidad con respuestas dict
            if isinstance(response, dict):
                if "choices" in response and isinstance(response["choices"], list):
                    choice = response["choices"][0]
                    if isinstance(choice, dict) and "message" in choice:
                        content = choice["message"].get("content", "")
                        self.logger.debug(f"🔧 Dict format content length: {len(content)}")
                        if not content:
                            self.logger.warning(f"🔧 Empty content in dict response. Message: {choice['message']}")
                        return content
                if "content" in response:
                    return response["content"]
                if "text" in response:
                    return response["text"]

            # Si ya es string
            if isinstance(response, str):
                return response

            # Fallback genérico
            self.logger.warning("Formato de respuesta LLM desconocido: %s", type(response))
            return str(response)

        except Exception as e:
            self.logger.error("Error extrayendo contenido de respuesta LLM: %s", e, exc_info=True)
            raise JSONParsingException(f"Error procesando respuesta del LLM: {e}")

    async def embed(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> List[List[float]]:
        model_to_use = model or self.embed_model
        try:
            if not texts:
                raise ValueError("La lista de textos no puede estar vacía")
            self.logger.debug("Generando embedding para %d textos con %s", len(texts), model_to_use)
            return await self.client.embed(texts=texts, model=model_to_use)
        except Exception as e:
            self.logger.error("Error generando embeddings con %s: %s", model_to_use, e, exc_info=True)
            raise WorkflowProcessingException(f"Error generando embeddings: {e}")


# Global singleton instance
_llm_service_instance: Optional[LLMService] = None

def get_llm_service() -> LLMService:
    """
    Singleton factory para LLMService - garantiza una sola instancia compartida.
    Esto asegura que el workflow planner, OAuth bridge y todos los servicios 
    usen el MISMO LLM con contexto histórico compartido.
    """
    global _llm_service_instance
    
    if _llm_service_instance is None:
        try:
            logging.getLogger(__name__).info("Creating SINGLETON LLMService instance")
            _llm_service_instance = LLMService(
                api_key=settings.LLM_API_KEY,
                model=settings.DEFAULT_LLM_MODEL
            )
        except Exception as e:
            logging.getLogger(__name__).error("Error inicializando LLMService: %s", e, exc_info=True)
            raise WorkflowProcessingException(f"Error inicializando LLMService: {e}")
    
    return _llm_service_instance


def get_llm_client() -> LLMClientProtocol:
    try:
        return LLMClientFactory.create(
            settings.LLM_API_KEY,
            settings.DEFAULT_LLM_MODEL
        )
    except Exception as e:
        logging.getLogger(__name__).error("Error inicializando LLMClient: %s", e, exc_info=True)
        raise WorkflowProcessingException(f"Error inicializando LLMClient: {e}")


# 🎯 FUNCIONES HELPER PARA TOKEN TRACKING

def set_token_context(
    user_id: int,
    operation_type: str = "workflow",
    workflow_id: Optional[str] = None,
    execution_id: Optional[str] = None
):
    """
    Establece el contexto de tracking de tokens
    
    Usage:
    set_token_context(user_id=123, workflow_id="flow_456")
    # Todas las llamadas LLM posteriores serán tracked automáticamente
    """
    context = {
        "user_id": user_id,
        "operation_type": operation_type,
        "workflow_id": workflow_id,
        "execution_id": execution_id
    }
    _token_context.set(context)

def clear_token_context():
    """Limpia el contexto de tracking de tokens"""
    _token_context.set(None)

def get_token_context() -> Optional[Dict[str, Any]]:
    """Obtiene el contexto actual de tracking"""
    return _token_context.get()

# Context manager para uso más elegante
from contextlib import asynccontextmanager

@asynccontextmanager
async def token_tracking_context(
    user_id: int,
    operation_type: str = "workflow",
    workflow_id: Optional[str] = None,
    execution_id: Optional[str] = None
):
    """
    Context manager para tracking automático de tokens
    
    Usage:
    async with token_tracking_context(user_id=123, workflow_id="flow_456"):
        # Todas las llamadas LLM aquí serán tracked automáticamente
        result = await llm_service.run(...)
    """
    set_token_context(user_id, operation_type, workflow_id, execution_id)
    try:
        yield
    finally:
        clear_token_context()
