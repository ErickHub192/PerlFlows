# app/services/provider_registry_service.py
"""
Service to manage LLM provider registry with database as single source of truth
"""
import logging
from typing import Dict, List, Optional
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.repositories.llm_provider_repository import LLMProviderRepository
from app.repositories.llm_model_repository import LLMModelRepository
from app.dependencies.llm_dependencies import get_llm_provider_repository, get_llm_model_repository
from app.ai.llm_clients.provider_registry import provider_registry, ProviderInfo, ModelOption
from app.ai.llm_clients.openai_client import OpenAIProvider
from app.ai.llm_clients.anthropic_client import AnthropicProvider
from app.ai.llm_clients.database_provider import DatabaseProviderRegistry

logger = logging.getLogger(__name__)

class ProviderRegistryService:
    """
    Service to manage the LLM provider registry using database as source of truth
    """
    
    def __init__(
        self,
        provider_repo: LLMProviderRepository,
        model_repo: LLMModelRepository
    ):
        self.provider_repo = provider_repo
        self.model_repo = model_repo
        self.db_registry = DatabaseProviderRegistry(provider_repo, model_repo)
        self._initialized = False
    
    async def initialize_providers(self) -> None:
        """
        Initialize provider registry with data from database
        """
        if self._initialized:
            return
        
        try:
            # Clear existing hardcoded providers
            provider_registry._providers.clear()
            
            # Initialize LLMClientFactory with database repositories
            from app.ai.llm_factory import LLMClientFactory
            LLMClientFactory.set_repositories(self.model_repo, self.provider_repo)
            
            # Load providers from database
            providers_data = await self.provider_repo.get_all_active()
            
            for provider_data in providers_data:
                await self._register_provider(provider_data.provider_key)
            
            self._initialized = True
            logger.info(f"Initialized {len(providers_data)} LLM providers from database")
            logger.info("LLMClientFactory configured with database repositories")
            
        except Exception as e:
            logger.error(f"Failed to initialize provider registry: {e}")
            raise
    
    async def _register_provider(self, provider_key: str) -> None:
        """
        Register a specific provider with database-driven models
        """
        try:
            if provider_key == "openai":
                provider = OpenAIProvider(self.model_repo)
                provider._models_cache = await provider._load_models_from_database()
                provider_registry.register(provider)
                
            elif provider_key == "anthropic":
                provider = AnthropicProvider(self.model_repo)
                provider._models_cache = await provider._load_models_from_database()
                provider_registry.register(provider)
                
            else:
                # For other providers, use generic database provider
                db_provider = await self.db_registry.get_provider(provider_key)
                if db_provider:
                    # Load models for the database provider
                    await db_provider._load_models()
                    provider_registry.register(db_provider)
            
            logger.info(f"Registered provider: {provider_key}")
            
        except Exception as e:
            logger.error(f"Failed to register provider {provider_key}: {e}")
    
    async def refresh_provider_models(self, provider_key: str) -> None:
        """
        Refresh models for a specific provider from database
        """
        provider = provider_registry.get_provider(provider_key)
        if not provider:
            logger.warning(f"Provider {provider_key} not found in registry")
            return
        
        if hasattr(provider, '_load_models_from_database'):
            provider._models_cache = await provider._load_models_from_database()
            logger.info(f"Refreshed models for provider: {provider_key}")
        elif hasattr(provider, '_load_models'):
            await provider._load_models()
            logger.info(f"Refreshed models for provider: {provider_key}")
    
    async def get_all_models_with_providers(self) -> List[dict]:
        """
        Get all models from all providers with enhanced information
        """
        await self.initialize_providers()
        return await self.db_registry.get_all_models()
    
    async def get_provider_models(self, provider_key: str) -> List[dict]:
        """
        Get models for a specific provider
        """
        await self.initialize_providers()
        
        models = await self.model_repo.get_by_provider_key(provider_key)
        provider = await self.provider_repo.get_by_provider_key(provider_key)
        
        return [
            {
                "model_key": model.model_key,
                "model_name": model.display_name,
                "description": model.description,
                "provider_key": provider_key,
                "provider_name": provider.name if provider else provider_key,
                "context_length": model.context_length,
                "input_cost_per_1k": float(model.input_cost_per_1k or 0),
                "output_cost_per_1k": float(model.output_cost_per_1k or 0),
                "is_recommended": model.is_recommended,
                "is_default": model.is_default,
                "capabilities": model.capabilities or []
            }
            for model in models
            if model.is_active
        ]
    
    async def validate_model_availability(self, model_key: str) -> bool:
        """
        Validate that a model is available and active
        """
        await self.initialize_providers()
        
        model = await self.model_repo.get_by_model_key(model_key)
        if not model or not model.is_active:
            return False
        
        provider = await self.provider_repo.get_by_id(model.provider_id)
        return provider is not None and provider.is_active


def get_provider_registry_service(
    db: AsyncSession = Depends(get_db),
    provider_repo: LLMProviderRepository = Depends(get_llm_provider_repository),
    model_repo: LLMModelRepository = Depends(get_llm_model_repository)
) -> ProviderRegistryService:
    """Dependency injection for ProviderRegistryService"""
    return ProviderRegistryService(provider_repo, model_repo)