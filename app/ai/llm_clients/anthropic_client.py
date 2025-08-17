# app/ai/llm_clients/anthropic_client.py
"""
Anthropic Claude Client - Implementación para Anthropic Claude API
"""
import logging
import json
from typing import Any, Dict, List

from app.ai.llm_factory import LLMClientFactory
from .protocol import LLMClientProtocol
from app.exceptions.api_exceptions import WorkflowProcessingException
from .provider_registry import LLMProvider, ModelOption, provider_registry
from typing import List

@LLMClientFactory.register
class AnthropicClient(LLMClientProtocol):
    """
    Cliente de Anthropic Claude
    Implementa el protocolo LLM para modelos Claude
    """

    @staticmethod
    def can_handle_model(model: str) -> bool:
        return model.startswith("claude-") or "claude" in model.lower()

    def __init__(self, api_key: str, model: str):
        """
        Inicializa el cliente Anthropic

        Args:
            api_key: Clave de API de Anthropic
            model: Identificador del modelo Claude
        """
        self.logger = logging.getLogger(__name__)
        self.model = model
        
        try:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=api_key)
        except ImportError:
            self.logger.error("anthropic package not installed")
            raise WorkflowProcessingException("Anthropic client requires 'anthropic' package")
        except Exception as e:
            self.logger.error("Error initializing AnthropicClient: %s", e, exc_info=True)
            raise WorkflowProcessingException(f"Error initializing AnthropicClient: {e}")

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        **kwargs: Any
    ) -> Any:
        """
        Envía una petición de chat-completion a la API de Anthropic

        Args:
            messages: Lista de mensajes {'role': str, 'content': str}
            temperature: Controla la aleatoriedad (0.0-1.0)
            **kwargs: Parámetros adicionales de Anthropic

        Returns:
            El objeto de respuesta de Anthropic
        """
        try:
            # Convertir formato OpenAI a formato Anthropic
            anthropic_messages = self._convert_messages_format(messages)
            
            params: Dict[str, Any] = {
                "model": self.model,
                "messages": anthropic_messages,
                "temperature": temperature,
                "max_tokens": kwargs.get("max_tokens", 2000)
            }
            
            # Agregar parámetros específicos de Anthropic
            if "system" in kwargs:
                params["system"] = kwargs["system"]
            
            self.logger.debug("AnthropicClient payload:\n%s", json.dumps(params, indent=2, ensure_ascii=False))

            response = await self._client.messages.create(**params)
            return response

        except Exception as e:
            self.logger.error("AnthropicClient error: %s", e, exc_info=True)
            raise WorkflowProcessingException(f"Anthropic API error: {e}")

    def _convert_messages_format(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Convierte mensajes de formato OpenAI a formato Anthropic
        """
        converted = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            # Anthropic usa "user" y "assistant" (no "system")
            if role == "system":
                # En Anthropic, system messages van en el parámetro system
                continue
            elif role in ["user", "assistant"]:
                converted.append({
                    "role": role,
                    "content": content
                })
        
        return converted

    async def embed(self, texts: List[str], model: str) -> List[List[float]]:
        """
        Anthropic no tiene API de embeddings nativa
        Implementación placeholder
        """
        raise WorkflowProcessingException("Anthropic does not provide embeddings API")

    def export_kv_cache(self) -> bytes:
        """Anthropic no soporta KV cache export"""
        return b""

    def load_kv_cache(self, kv_bytes: bytes) -> None:
        """Anthropic no soporta KV cache loading"""
        pass


class AnthropicProvider(LLMProvider):
    """
    Anthropic Provider - Uses database as single source of truth for models
    """
    
    def __init__(self, model_repo=None):
        self._model_repo = model_repo
        self._models_cache = None
    
    @property
    def provider_id(self) -> str:
        return "anthropic"
    
    @property
    def provider_name(self) -> str:
        return "Anthropic"
    
    @property
    def description(self) -> str:
        return "Claude 3 family - advanced reasoning with large context windows"
    
    @property
    def api_key_format(self) -> str:
        return "sk-ant-..."
    
    @property
    def website(self) -> str:
        return "https://anthropic.com"
    
    @property
    def pricing_url(self) -> str:
        return "https://docs.anthropic.com/claude/docs/models-overview#model-comparison"
    
    async def _load_models_from_database(self) -> list[ModelOption]:
        """Load models from database"""
        if not self._model_repo:
            return []
        
        models = await self._model_repo.get_by_provider_key("anthropic")
        return [
            ModelOption(
                id=model.model_key,
                name=model.display_name,
                description=model.description or "",
                recommended=model.is_recommended,
                is_default=model.is_default
            )
            for model in models
            if model.is_active
        ]
    
    def get_available_models(self) -> list[ModelOption]:
        """Returns models from cache or empty list if not loaded"""
        return self._models_cache or []
    
    def get_capabilities(self) -> list[str]:
        return [
            "text_generation",
            "code_generation",
            "chat_conversation", 
            "vision_understanding",
            "large_context",
            "constitutional_ai"
        ]

# Note: Provider registration now happens at startup with dependency injection