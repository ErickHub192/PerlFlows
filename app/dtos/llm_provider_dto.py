# app/dtos/llm_provider_dto.py
"""
DTOs for LLM Provider domain
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class LLMProviderDTO(BaseModel):
    """DTO for LLM Provider"""
    provider_id: UUID
    name: str
    provider_key: str
    description: Optional[str] = None
    api_key_format: Optional[str] = None
    base_url: Optional[str] = None
    health_check_endpoint: Optional[str] = None
    auth_header_format: Optional[str] = None
    rate_limit_rpm: Optional[int] = None
    rate_limit_tpm: Optional[int] = None
    website: Optional[str] = None
    pricing_url: Optional[str] = None
    capabilities: Optional[List[str]] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LLMProviderSummaryDTO(BaseModel):
    """Summary DTO for LLM Provider with counts"""
    provider_id: UUID
    name: str
    provider_key: str
    description: Optional[str] = None
    api_key_format: Optional[str] = None
    website: Optional[str] = None
    pricing_url: Optional[str] = None
    capabilities: Optional[List[str]] = None
    rate_limit_rpm: Optional[int] = None
    rate_limit_tpm: Optional[int] = None
    model_count: int
    recommended_model_count: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class LLMProviderWithModelsDTO(BaseModel):
    """DTO for LLM Provider with its models"""
    provider_id: UUID
    name: str
    provider_key: str
    description: Optional[str] = None
    api_key_format: Optional[str] = None
    website: Optional[str] = None
    pricing_url: Optional[str] = None
    capabilities: Optional[List[str]] = None
    is_active: bool
    models: List["LLMModelDTO"] = []
    model_count: int
    default_model_key: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Import here to avoid circular imports
from app.dtos.llm_model_dto import LLMModelDTO
LLMProviderWithModelsDTO.model_rebuild()