# app/ai/llm_clients/database_provider.py
"""
Database-driven LLM Provider implementation.
Replaces hardcoded models with database-sourced model information.
"""
import logging
from typing import List, Optional
from app.ai.llm_clients.provider_registry import LLMProvider, ModelOption
from app.repositories.llm_provider_repository import LLMProviderRepository
from app.repositories.llm_model_repository import LLMModelRepository

logger = logging.getLogger(__name__)

class DatabaseProvider(LLMProvider):
    """
    Database-driven provider that dynamically loads models from database
    """
    
    def __init__(
        self, 
        provider_key: str,
        provider_repo: LLMProviderRepository,
        model_repo: LLMModelRepository
    ):
        self._provider_key = provider_key
        self._provider_repo = provider_repo
        self._model_repo = model_repo
        self._provider_info = None
        self._models_cache = None
    
    async def _load_provider_info(self):
        """Load provider information from database"""
        if self._provider_info is None:
            self._provider_info = await self._provider_repo.get_by_provider_key(self._provider_key)
            if not self._provider_info:
                raise ValueError(f"Provider '{self._provider_key}' not found in database")
    
    async def _load_models(self):
        """Load models from database"""
        if self._models_cache is None:
            await self._load_provider_info()
            models = await self._model_repo.get_by_provider_key(self._provider_key)
            
            self._models_cache = [
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
    
    @property
    def provider_id(self) -> str:
        return self._provider_key
    
    @property
    def provider_name(self) -> str:
        if self._provider_info:
            return self._provider_info.name
        return self._provider_key.title()
    
    @property
    def description(self) -> str:
        if self._provider_info:
            return self._provider_info.description or ""
        return f"Provider {self._provider_key}"
    
    @property
    def api_key_format(self) -> str:
        if self._provider_info:
            return self._provider_info.api_key_format or "API-KEY"
        return "API-KEY"
    
    @property
    def website(self) -> str:
        if self._provider_info:
            return self._provider_info.website or "#"
        return "#"
    
    @property
    def pricing_url(self) -> str:
        if self._provider_info:
            return self._provider_info.pricing_url or "#"
        return "#"
    
    def get_available_models(self) -> List[ModelOption]:
        """
        Synchronous method required by interface - use with care
        For async usage, prefer get_available_models_async()
        """
        if self._models_cache is None:
            logger.warning(f"Models not loaded for provider {self._provider_key}. Use get_available_models_async() first.")
            return []
        return self._models_cache
    
    async def get_available_models_async(self) -> List[ModelOption]:
        """Async version that loads from database"""
        await self._load_models()
        return self._models_cache or []
    
    def get_capabilities(self) -> List[str]:
        if self._provider_info and self._provider_info.capabilities:
            return self._provider_info.capabilities
        return []


class DatabaseProviderRegistry:
    """
    Registry that creates database-driven providers dynamically
    """
    
    def __init__(self, provider_repo: LLMProviderRepository, model_repo: LLMModelRepository):
        self._provider_repo = provider_repo
        self._model_repo = model_repo
        self._providers_cache = {}
    
    async def get_provider(self, provider_key: str) -> Optional[DatabaseProvider]:
        """Get or create a database provider"""
        if provider_key not in self._providers_cache:
            try:
                provider = DatabaseProvider(provider_key, self._provider_repo, self._model_repo)
                await provider._load_provider_info()
                self._providers_cache[provider_key] = provider
            except ValueError:
                logger.warning(f"Provider {provider_key} not found in database")
                return None
        
        return self._providers_cache.get(provider_key)
    
    async def get_all_providers(self) -> List[DatabaseProvider]:
        """Get all active providers from database"""
        providers_data = await self._provider_repo.get_all_active()
        providers = []
        
        for provider_data in providers_data:
            provider = await self.get_provider(provider_data.provider_key)
            if provider:
                providers.append(provider)
        
        return providers
    
    async def get_all_models(self) -> List[dict]:
        """Get all models from all providers with provider information"""
        models = await self._model_repo.get_all_active()
        result = []
        
        for model in models:
            provider = await self.get_provider(model.provider_key)
            result.append({
                "model_key": model.model_key,
                "model_name": model.display_name,
                "description": model.description,
                "provider_key": model.provider_key,
                "provider_name": provider.provider_name if provider else model.provider_key,
                "context_length": model.context_length,
                "input_cost_per_1k": float(model.input_cost_per_1k or 0),
                "output_cost_per_1k": float(model.output_cost_per_1k or 0),
                "is_recommended": model.is_recommended,
                "is_default": model.is_default,
                "capabilities": model.capabilities or []
            })
        
        return result