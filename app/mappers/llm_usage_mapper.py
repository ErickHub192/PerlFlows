# app/mappers/llm_usage_mapper.py
"""
Mapper functions for LLM Usage domain
"""
from typing import Optional
from app.db.models import LLMUsageLog
from app.dtos.llm_usage_dto import LLMUsageLogDTO, LLMUsageWithDetailsDTO


def to_llm_usage_log_dto(usage_log: Optional[LLMUsageLog]) -> Optional[LLMUsageLogDTO]:
    """Convert LLMUsageLog model to LLMUsageLogDTO"""
    if not usage_log:
        return None
    return LLMUsageLogDTO.model_validate(usage_log)


def to_llm_usage_with_details_dto(usage_log: LLMUsageLog) -> LLMUsageWithDetailsDTO:
    """Convert LLMUsageLog with provider/model details to LLMUsageWithDetailsDTO"""
    provider_name = usage_log.provider.name if usage_log.provider else None
    provider_key = usage_log.provider.provider_key if usage_log.provider else None
    model_name = usage_log.model.display_name if usage_log.model else None
    model_key = usage_log.model.model_key if usage_log.model else None
    
    return LLMUsageWithDetailsDTO(
        usage_id=usage_log.usage_id,
        user_id=usage_log.user_id,
        provider_name=provider_name,
        provider_key=provider_key,
        model_name=model_name,
        model_key=model_key,
        input_tokens=usage_log.input_tokens,
        output_tokens=usage_log.output_tokens,
        total_cost=usage_log.total_cost,
        response_time_ms=usage_log.response_time_ms,
        status=usage_log.status,
        error_message=usage_log.error_message,
        created_at=usage_log.created_at
    )