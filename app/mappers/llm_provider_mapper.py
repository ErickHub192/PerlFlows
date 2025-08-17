# app/mappers/llm_provider_mapper.py
"""
Mapper functions for LLM Provider domain
"""
from typing import Optional, List
from app.db.models import LLMProvider
from app.dtos.llm_provider_dto import LLMProviderDTO, LLMProviderSummaryDTO, LLMProviderWithModelsDTO


def to_llm_provider_dto(provider: Optional[LLMProvider]) -> Optional[LLMProviderDTO]:
    """Convert LLMProvider model to LLMProviderDTO"""
    if not provider:
        return None
    return LLMProviderDTO.model_validate(provider)


def to_llm_provider_summary_dto(
    provider: LLMProvider, 
    model_count: int = 0, 
    recommended_model_count: int = 0
) -> LLMProviderSummaryDTO:
    """Convert LLMProvider model to LLMProviderSummaryDTO with counts"""
    return LLMProviderSummaryDTO(
        provider_id=provider.provider_id,
        name=provider.name,
        provider_key=provider.provider_key,
        description=provider.description,
        api_key_format=provider.api_key_format,
        website=provider.website,
        pricing_url=provider.pricing_url,
        capabilities=provider.capabilities,
        rate_limit_rpm=provider.rate_limit_rpm,
        rate_limit_tpm=provider.rate_limit_tpm,
        model_count=model_count,
        recommended_model_count=recommended_model_count,
        is_active=provider.is_active
    )


def to_llm_provider_with_models_dto(
    provider: LLMProvider,
    models: List = None,
    default_model_key: str = None
) -> LLMProviderWithModelsDTO:
    """Convert LLMProvider model to LLMProviderWithModelsDTO"""
    from app.mappers.llm_model_mapper import to_llm_model_dto
    
    models_dto = []
    if models:
        models_dto = [to_llm_model_dto(model) for model in models if model]
    
    return LLMProviderWithModelsDTO(
        provider_id=provider.provider_id,
        name=provider.name,
        provider_key=provider.provider_key,
        description=provider.description,
        api_key_format=provider.api_key_format,
        website=provider.website,
        pricing_url=provider.pricing_url,
        capabilities=provider.capabilities,
        is_active=provider.is_active,
        models=models_dto,
        model_count=len(models_dto),
        default_model_key=default_model_key
    )