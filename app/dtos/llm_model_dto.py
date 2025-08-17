# app/dtos/llm_model_dto.py
"""
DTOs for LLM Model domain
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class LLMModelDTO(BaseModel):
    """DTO for LLM Model"""
    model_id: UUID
    provider_id: UUID
    model_key: str
    display_name: str
    description: Optional[str] = None
    model_family: Optional[str] = None
    release_date: Optional[date] = None
    deprecation_date: Optional[date] = None
    max_output_tokens: Optional[int] = None
    training_cutoff_date: Optional[date] = None
    response_time_ms: Optional[int] = None
    context_length: Optional[int] = None
    input_cost_per_1k: Optional[Decimal] = None
    output_cost_per_1k: Optional[Decimal] = None
    capabilities: Optional[List[str]] = None
    is_recommended: bool
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LLMModelWithProviderDTO(BaseModel):
    """DTO for LLM Model with provider information"""
    model_id: UUID
    provider_id: UUID
    provider_name: str
    provider_key: str
    model_key: str
    display_name: str
    description: Optional[str] = None
    model_family: Optional[str] = None
    context_length: Optional[int] = None
    max_output_tokens: Optional[int] = None
    input_cost_per_1k: Optional[Decimal] = None
    output_cost_per_1k: Optional[Decimal] = None
    capabilities: Optional[List[str]] = None
    is_recommended: bool
    is_default: bool
    response_time_ms: Optional[int] = None
    release_date: Optional[date] = None
    deprecation_date: Optional[date] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class LLMModelSummaryDTO(BaseModel):
    """Summary DTO for LLM Model"""
    model_id: UUID
    provider_key: str
    model_key: str
    display_name: str
    description: Optional[str] = None
    is_recommended: bool
    is_default: bool
    context_length: Optional[int] = None
    input_cost_per_1k: Optional[Decimal] = None
    output_cost_per_1k: Optional[Decimal] = None
    capabilities: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)