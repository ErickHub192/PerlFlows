# app/handlers/ai_agent_handler.py
"""
AI Agent Handler - Single source of truth wrapper
Refactored to delegate all business logic to AIAgentService
"""
import time
import logging
from uuid import UUID
from typing import Any, Dict, Optional

from .connector_handler import ActionHandler
from app.exceptions.api_exceptions import HandlerError, InvalidDataException
from app.connectors.factory import register_node, register_tool
from app.services.ai_agent_service import AIAgentService
from app.repositories.ai_agent_repository import get_ai_agent_repository
from app.repositories.agent_run_repository import get_agent_run_repository

logger = logging.getLogger(__name__)

@register_node("AI_Agent.run_agent")
@register_tool("AI_Agent.run_agent")
class AIAgentHandler(ActionHandler):
    """
    AI Agent Handler - Single source of truth for agent execution
    
    This handler acts as a thin wrapper around AIAgentService,
    providing the tool/node interface while delegating all 
    business logic to the service layer.
    
    ARCHITECTURAL PRINCIPLE:
    - Handler = Interface layer (validation, formatting)  
    - Service = Business logic (execution, memory, reasoning)
    - No duplication of agent execution logic
    """

    def __init__(self, creds: Dict[str, Any]):
        super().__init__(creds)
        self.creds = creds
        # Service will be injected on each execution to avoid state issues
        self._ai_agent_service: Optional[AIAgentService] = None

    async def execute(
        self,
        params: Dict[str, Any],
        creds: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Execute AI Agent using AIAgentService as single source of truth.
        
        This handler acts as a thin wrapper, delegating all business logic
        to the service layer to maintain clean architecture.
        """
        start_time = time.perf_counter()
        logger.info("AI_AGENT_HANDLER: Iniciando ejecución de agente AI")
        logger.debug(f"AI_AGENT_HANDLER: Parámetros recibidos: {params}")
        logger.debug(f"AI_AGENT_HANDLER: Credenciales recibidas: {bool(creds)}")
        
        try:
            # 1. Validate and extract agent_id
            logger.debug("AI_AGENT_HANDLER: Validando y extrayendo agent_id")
            agent_id = self._validate_and_extract_agent_id(creds or self.creds)
            logger.info(f"AI_AGENT_HANDLER: Agent ID extraído: {agent_id}")
            
            # 2. Extract and validate execution parameters
            logger.debug("AI_AGENT_HANDLER: Extrayendo y validando parámetros de ejecución")
            execution_params = self._extract_and_validate_params(params, creds or self.creds)
            logger.info(f"AI_AGENT_HANDLER: Parámetros validados para prompt: {execution_params['user_prompt'][:100]}...")
            
            # 3. Get AI Agent Service (dependency injection)
            logger.debug("AI_AGENT_HANDLER: Obteniendo AI Agent Service")
            ai_agent_service = await self._get_ai_agent_service()
            
            # 4. Execute agent via service (SINGLE SOURCE OF TRUTH)
            logger.info(f"AI_AGENT_HANDLER: Ejecutando agente {agent_id} vía service")
            result = await ai_agent_service.execute_agent(
                agent_id=agent_id,
                user_prompt=execution_params["user_prompt"],
                user_id=execution_params.get("user_id"),
                temperature=execution_params.get("temperature"),
                max_iterations=execution_params.get("max_iterations"),
                api_key=execution_params["api_key"],
                session_id=execution_params.get("session_id")
            )
            
            logger.info(f"AI_AGENT_HANDLER: Ejecución completada para agente {agent_id}")
            logger.debug(f"AI_AGENT_HANDLER: Resultado del service: {result.get('success', False)}")
            
            # 5. Format response for handler interface
            formatted_result = self._format_handler_response(result, start_time)
            logger.info(f"AI_AGENT_HANDLER: Respuesta formateada exitosamente")
            return formatted_result
            
        except InvalidDataException as e:
            logger.warning(f"AI_AGENT_HANDLER: Error de validación: {e}")
            return self._format_error_response(str(e), "VALIDATION_ERROR", start_time)
        except HandlerError as e:
            logger.error(f"AI_AGENT_HANDLER: Error del handler: {e}")
            logger.exception("AI_AGENT_HANDLER: Stack trace del error del handler")
            return self._format_error_response(str(e), "HANDLER_ERROR", start_time)
        except Exception as e:
            logger.error(f"AI_AGENT_HANDLER: Error inesperado: {e}")
            logger.exception("AI_AGENT_HANDLER: Stack trace completo del error inesperado")
            return self._format_error_response(f"Internal error: {str(e)}", "INTERNAL_ERROR", start_time)

    async def _get_ai_agent_service(self) -> AIAgentService:
        """
        Get AI Agent Service with proper dependency injection.
        
        In a real application, this would use a DI container.
        For now, we manually inject dependencies.
        """
        if self._ai_agent_service is None:
            # Import here to avoid circular imports
            from app.db.database import get_db
            
            # Get database session
            db_gen = get_db()
            db = await db_gen.__anext__()
            
            # Get repositories
            ai_agent_repo = get_ai_agent_repository(db)
            agent_run_repo = get_agent_run_repository(db)
            
            # Create service
            self._ai_agent_service = AIAgentService(
                ai_agent_repository=ai_agent_repo,
                agent_run_repository=agent_run_repo
            )
            
            logger.debug("AI Agent Service initialized for handler")
        
        return self._ai_agent_service

    def _validate_and_extract_agent_id(self, creds: Dict[str, Any]) -> UUID:
        """Validate and extract agent_id from credentials"""
        if not creds or not isinstance(creds, dict):
            raise InvalidDataException("Credentials are required")
        
        agent_id_str = creds.get("agent_id")
        if not agent_id_str:
            raise InvalidDataException("agent_id is required in credentials")
        
        try:
            return UUID(str(agent_id_str))
        except (ValueError, TypeError) as e:
            raise InvalidDataException(f"Invalid agent_id format: {agent_id_str}")

    def _extract_and_validate_params(self, params: Dict[str, Any], creds: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and validate execution parameters"""
        if not params or not isinstance(params, dict):
            raise InvalidDataException("Parameters are required")
        
        # Extract required user_prompt
        user_prompt = params.get("prompt") or params.get("user_prompt")
        if not user_prompt:
            raise InvalidDataException("prompt or user_prompt is required")
        
        # Extract API key
        api_key = creds.get("api_key") or params.get("api_key")
        if not api_key:
            raise InvalidDataException("api_key is required")
        
        # Extract optional parameters with defaults
        execution_params = {
            "user_prompt": str(user_prompt),
            "api_key": str(api_key),
            "user_id": params.get("user_id"),
            "temperature": params.get("temperature"),
            "max_iterations": params.get("max_iterations"),
            "session_id": params.get("session_id")
        }
        
        # Validate parameter types
        if execution_params["temperature"] is not None:
            try:
                execution_params["temperature"] = float(execution_params["temperature"])
                if not (0.0 <= execution_params["temperature"] <= 2.0):
                    raise InvalidDataException("temperature must be between 0.0 and 2.0")
            except (ValueError, TypeError):
                raise InvalidDataException("temperature must be a valid number")
        
        if execution_params["max_iterations"] is not None:
            try:
                execution_params["max_iterations"] = int(execution_params["max_iterations"])
                if execution_params["max_iterations"] <= 0:
                    raise InvalidDataException("max_iterations must be positive")
            except (ValueError, TypeError):
                raise InvalidDataException("max_iterations must be a valid integer")
        
        if execution_params["user_id"] is not None:
            try:
                execution_params["user_id"] = int(execution_params["user_id"])
            except (ValueError, TypeError):
                raise InvalidDataException("user_id must be a valid integer")
        
        return execution_params

    def _format_handler_response(self, service_result: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        """Format service result for handler interface"""
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Extract service result data
        success = service_result.get("success", False)
        agent_response = service_result.get("agent_response", {})
        execution_metadata = service_result.get("execution_metadata", {})
        
        if success:
            return {
                "status": "success",
                "output": agent_response.get("content", ""),
                "agent_response": agent_response,
                "execution_metadata": execution_metadata,
                "duration_ms": duration_ms,
                "handler": "AIAgentHandler",
                "execution_source": "service"  # Indicate this came from service layer
            }
        else:
            error_message = service_result.get("error", "Agent execution failed")
            return {
                "status": "error",
                "output": None,
                "error": error_message,
                "execution_metadata": execution_metadata,
                "duration_ms": duration_ms,
                "handler": "AIAgentHandler",
                "execution_source": "service"
            }

    def _format_error_response(self, error_message: str, error_code: str, start_time: float) -> Dict[str, Any]:
        """Format error response with consistent structure"""
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        
        return {
            "status": "error",
            "output": None,
            "error": error_message,
            "error_code": error_code,
            "duration_ms": duration_ms,
            "handler": "AIAgentHandler",
            "execution_source": "handler"  # Error occurred in handler layer
        }


