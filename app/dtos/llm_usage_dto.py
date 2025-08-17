# app/dtos/llm_usage_dto.py
"""
DTOs for LLM Usage domain
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class LLMUsageInputDTO(BaseModel):
    """Input DTO for logging LLM usage"""
    user_id: Optional[int] = None
    provider_id: Optional[UUID] = None
    model_id: Optional[UUID] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_cost: Optional[Decimal] = None
    response_time_ms: Optional[int] = None
    status: Optional[str] = None
    error_message: Optional[str] = None


class LLMUsageLogDTO(BaseModel):
    """DTO for LLM Usage Log"""
    usage_id: UUID
    user_id: Optional[int] = None
    provider_id: Optional[UUID] = None
    model_id: Optional[UUID] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_cost: Optional[Decimal] = None
    response_time_ms: Optional[int] = None
    status: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LLMUsageWithDetailsDTO(BaseModel):
    """DTO for LLM Usage with provider and model details"""
    usage_id: UUID
    user_id: Optional[int] = None
    provider_name: Optional[str] = None
    provider_key: Optional[str] = None
    model_name: Optional[str] = None
    model_key: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_cost: Optional[Decimal] = None
    response_time_ms: Optional[int] = None
    status: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LLMUsageAnalyticsDTO(BaseModel):
    """DTO for LLM Usage Analytics"""
    summary: Dict[str, Any]
    daily_trend: List[Dict[str, Any]]
    recent_usage: List[LLMUsageWithDetailsDTO]
    period: Dict[str, str]
    
    model_config = ConfigDict(from_attributes=True)