import pkgutil
import importlib
import logging
from typing import Type, Optional
from app.ai.llm_clients.protocol import LLMClientProtocol

logger = logging.getLogger(__name__)

class LLMClientFactory:
    # Registro interno de clientes LLM
    _registry: list[Type[LLMClientProtocol]] = []
    _model_repo = None
    _provider_repo = None

    @classmethod
    def register(cls, client_cls: Type[LLMClientProtocol]) -> Type[LLMClientProtocol]:
        """
        Decorador para registrar un cliente LLM en la fábrica.
        """
        cls._registry.append(client_cls)
        return client_cls

    @classmethod
    def set_repositories(cls, model_repo, provider_repo):
        """
        Set database repositories for enhanced validation
        """
        cls._model_repo = model_repo
        cls._provider_repo = provider_repo

    @classmethod
    async def validate_model(cls, model: str) -> bool:
        """
        Validate model exists and is active in database
        """
        if not cls._model_repo:
            logger.warning("Model repository not set, skipping database validation")
            return True
        
        try:
            model_info = await cls._model_repo.get_by_model_key(model)
            if not model_info or not model_info.is_active:
                return False
            
            # Validate provider is also active
            if cls._provider_repo:
                provider_info = await cls._provider_repo.get_by_provider_key(model_info.provider_key)
                return provider_info is not None and provider_info.is_active
            
            return True
        except Exception as e:
            logger.error(f"Error validating model {model}: {e}")
            return False

    @classmethod
    async def get_model_info(cls, model: str) -> Optional[dict]:
        """
        Get model information from database
        """
        if not cls._model_repo:
            return None
        
        try:
            model_info = await cls._model_repo.get_by_model_key(model)
            if not model_info:
                return None
            
            provider_info = None
            if cls._provider_repo:
                provider_info = await cls._provider_repo.get_by_provider_key(model_info.provider_key)
            
            return {
                'model_key': model_info.model_key,
                'display_name': model_info.display_name,
                'provider_key': model_info.provider_key,
                'provider_name': provider_info.name if provider_info else model_info.provider_key,
                'context_length': model_info.context_length,
                'input_cost_per_1k': float(model_info.input_cost_per_1k or 0),
                'output_cost_per_1k': float(model_info.output_cost_per_1k or 0),
                'capabilities': model_info.capabilities,
                'is_recommended': model_info.is_recommended
            }
        except Exception as e:
            logger.error(f"Error getting model info for {model}: {e}")
            return None

    @classmethod
    def create(cls, api_key: str, model: str) -> LLMClientProtocol:
        """
        Devuelve la instancia del cliente registrado que maneje 'model'.
        Now with enhanced database integration.
        """
        for client_cls in cls._registry:
            if hasattr(client_cls, 'can_handle_model') and client_cls.can_handle_model(model):
                return client_cls(api_key=api_key, model=model)
        raise ValueError(f"No LLM client registered for model '{model}'")

# Auto-descubrimiento de módulos en app/ai/llm_clients
package = importlib.import_module(__name__.rsplit('.', 1)[0] + '.llm_clients')
for _, modname, _ in pkgutil.iter_modules(package.__path__):
    importlib.import_module(f"{package.__name__}.{modname}")


create = LLMClientFactory.create
