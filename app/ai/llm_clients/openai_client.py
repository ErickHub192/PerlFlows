import logging
import json
from typing import Any, Dict, List

from openai import AsyncOpenAI, BadRequestError, RateLimitError, APIError
from openai.types.chat import ChatCompletion
from openai.types.embedding import Embedding

from app.core.config import settings
from app.ai.llm_factory import LLMClientFactory
from .protocol import LLMClientProtocol
from app.exceptions.api_exceptions import WorkflowProcessingException
from .provider_registry import LLMProvider, ModelOption, provider_registry
from typing import List


@LLMClientFactory.register
class OpenAIClient(LLMClientProtocol):
    """
    Cliente de OpenAI sencillo, sin precarga de cache local.
    Encapsula llamadas a chat.completions y embeddings.
    """

    @staticmethod
    def can_handle_model(model: str) -> bool:
        return model.startswith("gpt-") or model.startswith("gpt_")

    def __init__(self, api_key: str, model: str):
        """
        Inicializa el cliente OpenAI con API key y modelo.

        Args:
            api_key: Clave de API de OpenAI.
            model: Identificador del modelo a usar en cada petición.
        """
        self.logger = logging.getLogger(__name__)
        client_kwargs: Dict[str, Any] = {"api_key": api_key}
        if settings.LLM_BASE_URL:
            client_kwargs["base_url"] = settings.LLM_BASE_URL
        else:
            self.logger.info("LLM_BASE_URL no definido; usando api.openai.com por defecto")

        try:
            self._client = AsyncOpenAI(**client_kwargs)
            self.model = model
        except Exception as e:
            self.logger.error("Error inicializando OpenAIClient: %s", e, exc_info=True)
            raise WorkflowProcessingException(f"Error inicializando OpenAIClient: {e}")

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        **kwargs: Any
    ) -> ChatCompletion:
        """
        Envía una petición de chat-completion a la API de OpenAI.

        Args:
            messages: Lista de mensajes {'role': str, 'content': str}.
            temperature: Controla la aleatoriedad (0.0-2.0).
            **kwargs: Cualquier parámetro válido de la API OpenAI (p.ej. max_tokens).

        Returns:
            El objeto ChatCompletion de OpenAI.
        """
        params: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        params.update(kwargs)

        self.logger.debug("OpenAIClient payload:\n%s", json.dumps(params, indent=2, ensure_ascii=False))

        try:
            resp = await self._client.chat.completions.create(**params)
            return resp

        except BadRequestError as e:
            body = getattr(e, "httpx_response", None)
            body = body.text if body else None
            self.logger.error("OpenAI 400 BadRequestError: %s\nBody: %s", e, body, exc_info=True)
            raise WorkflowProcessingException(f"OpenAI API Bad Request: {e}")

        except RateLimitError as e:
            self.logger.error("OpenAI RateLimitError: %s", e, exc_info=True)
            raise WorkflowProcessingException(f"OpenAI API Rate Limit: {e}")

        except APIError as e:
            self.logger.error("OpenAI APIError: %s", e, exc_info=True)
            raise WorkflowProcessingException(f"OpenAI API error: {e}")

        except Exception as e:
            self.logger.error("OpenAIClient unexpected error: %s", e, exc_info=True)
            raise WorkflowProcessingException(f"Error en llamada a OpenAI: {e}")

    async def embed(self, texts: List[str], model: str) -> List[List[float]]:
        """
        Genera embeddings usando la API de OpenAI.

        Args:
            texts: Lista de textos a vectorizar.
            model: Modelo de embeddings (p.ej. "text-embedding-ada-002").

        Returns:
            Lista de vectores de floats.
        """
        try:
            if not texts:
                raise ValueError("La lista de textos no puede estar vacía")
            self.logger.debug("OpenAIClient generating embeddings: %d texts via %s", len(texts), model)
            resp = await self._client.embeddings.create(model=model, input=texts)
            if not resp.data:
                raise WorkflowProcessingException("No se recibieron embeddings en la respuesta")
            return [item.embedding for item in resp.data]

        except BadRequestError as e:
            self.logger.error("OpenAI embeddings BadRequestError: %s", e, exc_info=True)
            raise WorkflowProcessingException(f"Error en solicitud de embeddings: {e}")

        except Exception as e:
            self.logger.error("Error generando embeddings: %s", e, exc_info=True)
            raise WorkflowProcessingException(f"Error generando embeddings: {e}")


class OpenAIProvider(LLMProvider):
    """
    OpenAI Provider - Uses database as single source of truth for models
    """
    
    def __init__(self, model_repo=None):
        self._model_repo = model_repo
        self._models_cache = None
    
    @property
    def provider_id(self) -> str:
        return "openai"
    
    @property
    def provider_name(self) -> str:
        return "OpenAI"
    
    @property
    def description(self) -> str:
        return "GPT models family - most popular and widely used LLMs"
    
    @property
    def api_key_format(self) -> str:
        return "sk-..."
    
    @property
    def website(self) -> str:
        return "https://openai.com"
    
    @property
    def pricing_url(self) -> str:
        return "https://openai.com/pricing"
    
    async def _load_models_from_database(self) -> List[ModelOption]:
        """Load models from database"""
        if not self._model_repo:
            return []
        
        models = await self._model_repo.get_by_provider_key("openai")
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
            "function_calling",
            "json_mode",
            "vision_understanding"
        ]

# Note: Provider registration now happens at startup with dependency injection
