# app/services/llm_provider_service.py
"""
Service layer for LLM Provider management
Handles business logic for providers, models, and usage analytics
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import aiohttp
import asyncio
from fastapi import Depends

from app.repositories.llm_provider_repository import LLMProviderRepository
from app.repositories.llm_model_repository import LLMModelRepository
from app.repositories.llm_usage_repository import LLMUsageRepository
from app.repositories.llm_provider_repository import get_llm_provider_repository
from app.repositories.llm_model_repository import get_llm_model_repository
from app.repositories.llm_usage_repository import get_llm_usage_repository
from app.db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.dtos.llm_provider_dto import LLMProviderSummaryDTO, LLMProviderWithModelsDTO
from app.dtos.llm_model_dto import LLMModelWithProviderDTO
from app.dtos.llm_usage_dto import LLMUsageInputDTO


class LLMProviderService:
    """Service for managing LLM providers and models"""

    def __init__(
        self, 
        provider_repo: LLMProviderRepository,
        model_repo: LLMModelRepository,
        usage_repo: LLMUsageRepository
    ):
        self.provider_repo = provider_repo
        self.model_repo = model_repo
        self.usage_repo = usage_repo
        self.logger = logging.getLogger(__name__)

    async def get_all_providers(self) -> List[LLMProviderSummaryDTO]:
        """Get all active providers with summary information"""
        providers = await self.provider_repo.get_all_active()
        
        # Convert to summary DTOs with model counts
        summary_providers = []
        for provider in providers:
            # Get model counts for this provider
            models = await self.model_repo.get_by_provider_key(provider.provider_key)
            model_count = len(models)
            recommended_count = len([m for m in models if m.is_recommended])
            
            from app.mappers.llm_provider_mapper import to_llm_provider_summary_dto
            summary_dto = to_llm_provider_summary_dto(
                provider, 
                model_count=model_count,
                recommended_model_count=recommended_count
            )
            summary_providers.append(summary_dto)
        
        return summary_providers

    async def get_provider_with_models(self, provider_key: str) -> Optional[LLMProviderWithModelsDTO]:
        """Get provider with all its models"""
        provider = await self.provider_repo.get_by_provider_key(provider_key)
        if not provider:
            return None
        
        models = await self.model_repo.get_by_provider_key(provider_key)
        default_model = await self.model_repo.get_default_model(provider_key)
        default_model_key = default_model.model_key if default_model else None
        
        from app.mappers.llm_provider_mapper import to_llm_provider_with_models_dto
        return to_llm_provider_with_models_dto(
            provider, 
            models=models, 
            default_model_key=default_model_key
        )

    async def get_recommended_models(self, provider_key: str = None) -> List[LLMModelWithProviderDTO]:
        """Get recommended models, optionally filtered by provider"""
        models = await self.model_repo.get_recommended_models(provider_key)
        
        from app.mappers.llm_model_mapper import to_llm_model_with_provider_dto
        return [to_llm_model_with_provider_dto(model) for model in models]

    async def search_providers_and_models(self, search_term: str) -> Dict[str, Any]:
        """Search both providers and models"""
        providers = await self.provider_repo.search_providers(search_term)
        models = await self.model_repo.search_models(search_term)
        
        from app.mappers.llm_provider_mapper import to_llm_provider_summary_dto
        from app.mappers.llm_model_mapper import to_llm_model_with_provider_dto
        
        return {
            "providers": [
                to_llm_provider_summary_dto(p, model_count=0, recommended_model_count=0) 
                for p in providers
            ],
            "models": [to_llm_model_with_provider_dto(m) for m in models],
            "total_providers": len(providers),
            "total_models": len(models)
        }

    async def get_models_by_capabilities(self, capabilities: List[str]) -> List[LLMModelWithProviderDTO]:
        """Get models that support specific capabilities"""
        models = await self.model_repo.get_models_with_capabilities(capabilities)
        
        from app.mappers.llm_model_mapper import to_llm_model_with_provider_dto
        return [to_llm_model_with_provider_dto(model) for model in models]

    async def log_llm_usage(self, usage_input: LLMUsageInputDTO) -> None:
        """Log LLM usage for analytics"""
        try:
            await self.usage_repo.log_usage(usage_input)
            self.logger.info(f"Logged LLM usage for user {usage_input.user_id}")
        except Exception as e:
            self.logger.error(f"Error logging LLM usage: {e}")
            raise

    async def get_user_usage_analytics(
        self, 
        user_id: int, 
        start_date: datetime = None, 
        end_date: datetime = None
    ) -> Dict[str, Any]:
        """Get usage analytics for a user"""
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
        # Get summary
        summary = await self.usage_repo.get_user_usage_summary(user_id, start_date, end_date)
        
        # Get daily trend
        daily_trend = await self.usage_repo.get_daily_usage_trend(user_id, days=30)
        
        # Get recent usage
        recent_usage = await self.usage_repo.get_usage_by_user(user_id, start_date, end_date, limit=50)
        
        from app.mappers.llm_usage_mapper import to_llm_usage_with_details_dto
        
        return {
            "summary": summary,
            "daily_trend": daily_trend,
            "recent_usage": [
                to_llm_usage_with_details_dto(usage) for usage in recent_usage
            ],
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        }

    # New methods for router endpoints
    async def get_providers_with_model_counts(self, include_inactive: bool = False) -> List[LLMProviderWithModelsDTO]:
        """Get all providers with model counts"""
        if include_inactive:
            providers = await self.provider_repo.get_all()
        else:
            providers = await self.provider_repo.get_all_active()
        
        result = []
        for provider in providers:
            models = await self.model_repo.get_by_provider_key(provider.provider_key, active_only=not include_inactive)
            default_model = await self.model_repo.get_default_model(provider.provider_key)
            
            from app.mappers.llm_provider_mapper import to_llm_provider_with_models_dto
            provider_dto = to_llm_provider_with_models_dto(
                provider, 
                models=models,
                default_model_key=default_model.model_key if default_model else None
            )
            result.append(provider_dto)
        
        return result

    async def get_provider_by_key(self, provider_key: str, include_models: bool = False) -> Optional[LLMProviderWithModelsDTO]:
        """Get provider by key with optional models"""
        provider = await self.provider_repo.get_by_provider_key(provider_key)
        if not provider:
            return None
        
        if include_models:
            models = await self.model_repo.get_by_provider_key(provider_key)
            default_model = await self.model_repo.get_default_model(provider_key)
            
            from app.mappers.llm_provider_mapper import to_llm_provider_with_models_dto
            return to_llm_provider_with_models_dto(
                provider, 
                models=models,
                default_model_key=default_model.model_key if default_model else None
            )
        else:
            from app.mappers.llm_provider_mapper import to_llm_provider_with_models_dto
            return to_llm_provider_with_models_dto(provider, models=[], default_model_key=None)

    async def get_models_by_provider(self, provider_key: str, include_inactive: bool = False) -> List:
        """Get models for a specific provider"""
        models = await self.model_repo.get_by_provider_key(provider_key, include_inactive=include_inactive)
        
        from app.mappers.llm_model_mapper import to_llm_model_dto
        return [to_llm_model_dto(model) for model in models]

    async def get_models_with_filters(
        self, 
        provider_key: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        min_context_length: Optional[int] = None,
        max_cost_per_1k_input: Optional[float] = None,
        include_inactive: bool = False
    ) -> List[LLMModelWithProviderDTO]:
        """Get models with advanced filtering"""
        models = await self.model_repo.get_models_with_filters(
            provider_key=provider_key,
            capabilities=capabilities,
            min_context_length=min_context_length,
            max_cost_per_1k_input=max_cost_per_1k_input,
            include_inactive=include_inactive
        )
        
        from app.mappers.llm_model_mapper import to_llm_model_with_provider_dto
        return [to_llm_model_with_provider_dto(model) for model in models]


    async def search_models(self, query: str, limit: int = 20) -> List[LLMModelWithProviderDTO]:
        """Search models by query"""
        models = await self.model_repo.search_models(query, limit=limit)
        
        from app.mappers.llm_model_mapper import to_llm_model_with_provider_dto
        return [to_llm_model_with_provider_dto(model) for model in models]

    async def check_providers_health(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all providers"""
        providers = await self.provider_repo.get_all_active()
        health_results = {}
        
        async def check_provider_health(provider):
            """Check health of a single provider"""
            try:
                if provider.health_check_url:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            provider.health_check_url, 
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as response:
                            healthy = response.status == 200
                else:
                    # If no health check URL, assume healthy if provider is active
                    healthy = provider.is_active
                
                return {
                    "healthy": healthy,
                    "status_code": response.status if provider.health_check_url else None,
                    "response_time_ms": None,  # Could measure this
                    "last_checked": datetime.now().isoformat()
                }
            except Exception as e:
                return {
                    "healthy": False,
                    "error": str(e),
                    "last_checked": datetime.now().isoformat()
                }
        
        # Check all providers concurrently
        tasks = [check_provider_health(provider) for provider in providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for provider, result in zip(providers, results):
            if isinstance(result, Exception):
                health_results[provider.provider_key] = {
                    "healthy": False,
                    "error": str(result),
                    "last_checked": datetime.now().isoformat()
                }
            else:
                health_results[provider.provider_key] = result
        
        return health_results

    async def get_user_analytics(
        self, 
        user_id: int, 
        days: int = 30,
        provider_key: Optional[str] = None
    ):
        """Get user analytics with optional provider filter"""
        start_date = datetime.now() - timedelta(days=days)
        end_date = datetime.now()
        
        # Get usage summary
        summary = await self.usage_repo.get_user_usage_summary(
            user_id, start_date, end_date, provider_key=provider_key
        )
        
        # Get trends
        daily_trend = await self.usage_repo.get_daily_usage_trend(
            user_id, days=days, provider_key=provider_key
        )
        
        return {
            "summary": summary,
            "daily_trend": daily_trend,
            "period_days": days,
            "provider_filter": provider_key
        }

    async def get_model_by_id(self, model_id, include_provider: bool = False):
        """Get model by ID with optional provider info"""
        model = await self.model_repo.get_by_id(model_id)
        if not model:
            return None
        
        if include_provider:
            from app.mappers.llm_model_mapper import to_llm_model_with_provider_dto
            return to_llm_model_with_provider_dto(model)
        else:
            from app.mappers.llm_model_mapper import to_llm_model_dto
            return to_llm_model_dto(model)

    async def perform_health_checks(self) -> Dict[str, Any]:
        """Perform health checks on providers"""
        providers = await self.provider_repo.health_check_providers()
        
        results = {}
        for provider in providers:
            if not provider.health_check_endpoint or not provider.base_url:
                continue
            
            try:
                health_url = f"{provider.base_url.rstrip('/')}{provider.health_check_endpoint}"
                
                async with aiohttp.ClientSession() as session:
                    start_time = datetime.now()
                    async with session.get(health_url, timeout=10) as response:
                        end_time = datetime.now()
                        response_time = (end_time - start_time).total_seconds() * 1000
                        
                        results[provider.provider_key] = {
                            "status": "healthy" if response.status == 200 else "unhealthy",
                            "status_code": response.status,
                            "response_time_ms": response_time,
                            "checked_at": end_time.isoformat(),
                            "endpoint": health_url
                        }
                        
            except asyncio.TimeoutError:
                results[provider.provider_key] = {
                    "status": "timeout",
                    "error": "Request timeout",
                    "checked_at": datetime.now().isoformat(),
                    "endpoint": health_url
                }
            except Exception as e:
                results[provider.provider_key] = {
                    "status": "error",
                    "error": str(e),
                    "checked_at": datetime.now().isoformat(),
                    "endpoint": health_url
                }
        
        return {
            "health_checks": results,
            "total_checked": len(results),
            "healthy_count": sum(1 for r in results.values() if r.get("status") == "healthy"),
            "checked_at": datetime.now().isoformat()
        }


# Factory function for dependency injection
async def get_llm_provider_service(
    session: AsyncSession = Depends(get_db)
) -> LLMProviderService:
    """Factory function to create LLMProviderService instance"""
    provider_repo = get_llm_provider_repository(session)
    model_repo = get_llm_model_repository(session)
    usage_repo = get_llm_usage_repository(session)
    return LLMProviderService(provider_repo, model_repo, usage_repo)