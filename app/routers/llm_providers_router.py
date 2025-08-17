# app/routers/llm_providers_router.py

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.database import get_db
from app.core.auth import get_current_user_id
from app.dtos.llm_provider_dto import LLMProviderDTO, LLMProviderWithModelsDTO
from app.dtos.llm_model_dto import LLMModelDTO, LLMModelWithProviderDTO
from app.dtos.llm_usage_dto import LLMUsageAnalyticsDTO
from app.services.llm_provider_service import LLMProviderService
from app.dependencies.llm_dependencies import get_llm_provider_service

router = APIRouter(prefix="/api/llm", tags=["llm-providers"])

@router.get(
    "/providers",
    response_model=List[LLMProviderWithModelsDTO],
    summary="Get all LLM providers with model counts"
)
async def get_providers(
    include_inactive: bool = Query(False, description="Include inactive providers"),
    db: Session = Depends(get_db),
    service: LLMProviderService = Depends(get_llm_provider_service)
):
    """
    Get all LLM providers with their model counts and basic information.
    """
    try:
        providers = await service.get_providers_with_model_counts(
            include_inactive=include_inactive
        )
        return providers
    except Exception as e:
        logging.exception("Error getting LLM providers")
        raise HTTPException(status_code=500, detail="Failed to get providers")

@router.get(
    "/providers/{provider_key}",
    response_model=LLMProviderWithModelsDTO,
    summary="Get specific provider with models"
)
async def get_provider_detail(
    provider_key: str,
    db: Session = Depends(get_db),
    service: LLMProviderService = Depends(get_llm_provider_service)
):
    """
    Get detailed information about a specific provider including all its models.
    """
    try:
        provider = await service.get_provider_by_key(provider_key, include_models=True)
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        return provider
    except HTTPException:
        raise
    except Exception as e:
        logging.exception(f"Error getting provider {provider_key}")
        raise HTTPException(status_code=500, detail="Failed to get provider")

@router.get(
    "/providers/{provider_key}/models",
    response_model=List[LLMModelDTO],
    summary="Get models for a specific provider"
)
async def get_provider_models(
    provider_key: str,
    include_inactive: bool = Query(False, description="Include inactive models"),
    db: Session = Depends(get_db),
    service: LLMProviderService = Depends(get_llm_provider_service)
):
    """
    Get all models for a specific provider.
    """
    try:
        models = await service.get_models_by_provider(
            provider_key=provider_key,
            include_inactive=include_inactive
        )
        return models
    except Exception as e:
        logging.exception(f"Error getting models for provider {provider_key}")
        raise HTTPException(status_code=500, detail="Failed to get provider models")

@router.get(
    "/models",
    response_model=List[LLMModelWithProviderDTO],
    summary="Get all available models with provider info"
)
async def get_all_models(
    provider_key: Optional[str] = Query(None, description="Filter by provider"),
    capabilities: Optional[List[str]] = Query(None, description="Filter by capabilities"),
    min_context_length: Optional[int] = Query(None, description="Minimum context length"),
    max_cost_per_1k_input: Optional[float] = Query(None, description="Maximum cost per 1K input tokens"),
    include_inactive: bool = Query(False, description="Include inactive models"),
    db: Session = Depends(get_db),
    service: LLMProviderService = Depends(get_llm_provider_service)
):
    """
    Get all available models with advanced filtering options.
    """
    try:
        models = await service.get_models_with_filters(
            provider_key=provider_key,
            capabilities=capabilities,
            min_context_length=min_context_length,
            max_cost_per_1k_input=max_cost_per_1k_input,
            include_inactive=include_inactive
        )
        return models
    except Exception as e:
        logging.exception("Error getting filtered models")
        raise HTTPException(status_code=500, detail="Failed to get models")


@router.get(
    "/models/search",
    response_model=List[LLMModelWithProviderDTO],
    summary="Search models by name or description"
)
async def search_models(
    q: str = Query(..., description="Search query"),
    limit: int = Query(20, le=100, description="Maximum number of results"),
    db: Session = Depends(get_db),
    service: LLMProviderService = Depends(get_llm_provider_service)
):
    """
    Search models by name, description, or capabilities.
    """
    try:
        models = await service.search_models(query=q, limit=limit)
        return models
    except Exception as e:
        logging.exception(f"Error searching models with query: {q}")
        raise HTTPException(status_code=500, detail="Failed to search models")

@router.get(
    "/health",
    summary="Check provider health status"
)
async def check_providers_health(
    db: Session = Depends(get_db),
    service: LLMProviderService = Depends(get_llm_provider_service)
):
    """
    Check the health status of all providers by testing their endpoints.
    """
    try:
        health_status = await service.check_providers_health()
        return {
            "status": "success",
            "providers": health_status,
            "healthy_count": sum(1 for status in health_status.values() if status["healthy"]),
            "total_count": len(health_status)
        }
    except Exception as e:
        logging.exception("Error checking provider health")
        raise HTTPException(status_code=500, detail="Failed to check provider health")


@router.get(
    "/models/{model_id}",
    response_model=LLMModelWithProviderDTO,
    summary="Get specific model details"
)
async def get_model_detail(
    model_id: UUID,
    db: Session = Depends(get_db),
    service: LLMProviderService = Depends(get_llm_provider_service)
):
    """
    Get detailed information about a specific model.
    """
    try:
        model = await service.get_model_by_id(model_id, include_provider=True)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        return model
    except HTTPException:
        raise
    except Exception as e:
        logging.exception(f"Error getting model {model_id}")
        raise HTTPException(status_code=500, detail="Failed to get model")

