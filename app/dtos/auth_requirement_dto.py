# app/dtos/auth_requirement_dto.py

from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from uuid import UUID


class AuthRequirementDTO(BaseModel):
    """DTO para representar un requirement de autenticación"""
    service_id: str
    mechanism: str
    provider: Optional[str] = None
    service: Optional[str] = None
    display_name: Optional[str] = None
    required_scopes: List[str] = []
    auth_url: Optional[str] = None
    auth_config: Dict[str, Any] = {}
    action_id: Optional[str] = None
    policy_id: Optional[int] = None
    is_satisfied: bool = False
    
    model_config = ConfigDict(from_attributes=True)


class AuthStepDTO(BaseModel):
    """DTO para un paso de autenticación"""
    type: str  # oauth, api_key, bot_token, db_credentials
    service_id: str
    display_name: str
    mechanism: str
    auth_url: Optional[str] = None
    required_scopes: List[str] = []
    input_required: bool = False
    metadata: Dict[str, Any] = {}
    
    model_config = ConfigDict(from_attributes=True)


class WorkflowAuthAnalysisDTO(BaseModel):
    """DTO para análisis completo de auth de un workflow"""
    total_requirements: int
    satisfied_count: int
    missing_count: int
    can_execute: bool
    all_requirements: List[AuthRequirementDTO] = []
    satisfied_requirements: List[AuthRequirementDTO] = []
    missing_requirements: List[AuthRequirementDTO] = []
    auth_steps: List[AuthStepDTO] = []
    auto_triggered: bool = False
    
    model_config = ConfigDict(from_attributes=True)


class ServiceAuthConfigDTO(BaseModel):
    """DTO para configuración de auth de un servicio"""
    service_id: str
    mechanism: str
    provider: Optional[str] = None
    service: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    icon_url: Optional[str] = None
    max_scopes: List[str] = []
    auth_url: Optional[str] = None
    auth_config: Dict[str, Any] = {}
    is_active: bool = True
    
    model_config = ConfigDict(from_attributes=True)