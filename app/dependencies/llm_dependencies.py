# app/dependencies/llm_dependencies.py
"""
Dependency injection for LLM-related services and repositories
"""
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.db.database import get_db
from app.repositories.llm_provider_repository import LLMProviderRepository
from app.repositories.llm_model_repository import LLMModelRepository
from app.repositories.llm_usage_repository import LLMUsageRepository
from app.services.llm_provider_service import LLMProviderService
from app.services.intelligent_llm_service import IntelligentLLMService


# Repository Dependencies
def get_llm_provider_repository(db: AsyncSession = Depends(get_db)) -> LLMProviderRepository:
    """Get LLM Provider Repository dependency"""
    return LLMProviderRepository(db)


def get_llm_model_repository(db: AsyncSession = Depends(get_db)) -> LLMModelRepository:
    """Get LLM Model Repository dependency"""
    return LLMModelRepository(db)


def get_llm_usage_repository(db: AsyncSession = Depends(get_db)) -> LLMUsageRepository:
    """Get LLM Usage Repository dependency"""
    return LLMUsageRepository(db)


# Service Dependencies
def get_llm_provider_service(
    provider_repo: LLMProviderRepository = Depends(get_llm_provider_repository),
    model_repo: LLMModelRepository = Depends(get_llm_model_repository),
    usage_repo: LLMUsageRepository = Depends(get_llm_usage_repository)
) -> LLMProviderService:
    """Get LLM Provider Service dependency"""
    return LLMProviderService(
        provider_repo=provider_repo,
        model_repo=model_repo,
        usage_repo=usage_repo
    )


def get_intelligent_llm_service(
    model_repo: LLMModelRepository = Depends(get_llm_model_repository),
    provider_repo: LLMProviderRepository = Depends(get_llm_provider_repository),
    usage_repo: LLMUsageRepository = Depends(get_llm_usage_repository)
) -> IntelligentLLMService:
    """Get Intelligent LLM Service dependency"""
    return IntelligentLLMService(
        model_repo=model_repo,
        provider_repo=provider_repo,
        usage_repo=usage_repo
    )