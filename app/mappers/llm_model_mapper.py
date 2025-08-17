# app/mappers/llm_model_mapper.py
"""
Mapper functions for LLM Model domain
"""
from typing import Optional
from app.db.models import LLMModel
from app.dtos.llm_model_dto import LLMModelDTO, LLMModelWithProviderDTO, LLMModelSummaryDTO


def to_llm_model_dto(model: Optional[LLMModel]) -> Optional[LLMModelDTO]:
    """Convert LLMModel model to LLMModelDTO"""
    if not model:
        return None
    return LLMModelDTO.model_validate(model)


def to_llm_model_with_provider_dto(model: LLMModel) -> LLMModelWithProviderDTO:
    """Convert LLMModel with provider to LLMModelWithProviderDTO"""
    return LLMModelWithProviderDTO(
        model_id=model.model_id,
        provider_id=model.provider_id,
        provider_name=model.provider.name,
        provider_key=model.provider.provider_key,
        model_key=model.model_key,
        display_name=model.display_name,
        description=model.description,
        model_family=model.model_family,
        context_length=model.context_length,
        max_output_tokens=model.max_output_tokens,
        input_cost_per_1k=model.input_cost_per_1k,
        output_cost_per_1k=model.output_cost_per_1k,
        capabilities=model.capabilities,
        is_recommended=model.is_recommended,
        is_default=model.is_default,
        response_time_ms=model.response_time_ms,
        release_date=model.release_date,
        deprecation_date=model.deprecation_date,
        is_active=model.is_active
    )


def to_llm_model_summary_dto(model: LLMModel) -> LLMModelSummaryDTO:
    """Convert LLMModel to LLMModelSummaryDTO"""
    return LLMModelSummaryDTO(
        model_id=model.model_id,
        provider_key=model.provider.provider_key,
        model_key=model.model_key,
        display_name=model.display_name,
        description=model.description,
        is_recommended=model.is_recommended,
        is_default=model.is_default,
        context_length=model.context_length,
        input_cost_per_1k=model.input_cost_per_1k,
        output_cost_per_1k=model.output_cost_per_1k,
        capabilities=model.capabilities
    )