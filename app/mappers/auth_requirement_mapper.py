# app/mappers/auth_requirement_mapper.py

from typing import Dict, Any, List
import uuid
from app.db.models import AuthPolicy
from app.dtos.auth_requirement_dto import (
    AuthRequirementDTO, 
    AuthStepDTO, 
    WorkflowAuthAnalysisDTO,
    ServiceAuthConfigDTO
)
from app.dtos.clarify_oauth_dto import ClarifyOAuthItemDTO


def auth_policy_to_service_config_dto(policy: AuthPolicy) -> ServiceAuthConfigDTO:
    """Convierte AuthPolicy model a ServiceAuthConfigDTO"""
    return ServiceAuthConfigDTO(
        service_id=policy.service_id,
        mechanism=policy.mechanism,
        provider=policy.provider,
        service=policy.service,
        display_name=policy.display_name,
        description=policy.description,
        icon_url=policy.icon_url,
        max_scopes=policy.max_scopes or [],
        auth_url=policy.base_auth_url,
        auth_config=policy.auth_config or {},
        is_active=policy.is_active
    )


def dict_to_auth_requirement_dto(data: Dict[str, Any]) -> AuthRequirementDTO:
    """Convierte dict a AuthRequirementDTO"""
    return AuthRequirementDTO(
        service_id=data.get("service_id") or "",
        mechanism=data.get("mechanism") or "oauth2",
        provider=data.get("provider"),
        service=data.get("service"),
        display_name=data.get("display_name") or "",
        required_scopes=data.get("required_scopes") or [],
        auth_url=data.get("auth_url") or "",
        auth_config=data.get("auth_config") or {},
        action_id=data.get("action_id"),
        policy_id=data.get("policy_id"),
        is_satisfied=data.get("is_satisfied", False)
    )


def create_auth_step_dto(
    mechanism: str,
    service_id: str,
    display_name: str,
    **kwargs
) -> AuthStepDTO:
    """Factory para crear AuthStepDTO basado en mechanism"""
    
    step_type_mapping = {
        "oauth2": "oauth",
        "api_key": "api_key", 
        "bot_token": "bot_token",
        "db_credentials": "db_credentials"
    }
    
    return AuthStepDTO(
        type=step_type_mapping.get(mechanism, mechanism),
        service_id=service_id,
        display_name=display_name,
        mechanism=mechanism,
        auth_url=kwargs.get("auth_url"),
        required_scopes=kwargs.get("required_scopes") or [],
        input_required=mechanism in ["api_key", "bot_token", "db_credentials"],
        metadata=kwargs.get("metadata") or {}
    )


def create_workflow_analysis_dto(
    requirements: List[AuthRequirementDTO],
    auth_steps: List[AuthStepDTO]
) -> WorkflowAuthAnalysisDTO:
    """Factory para crear WorkflowAuthAnalysisDTO"""
    
    satisfied = [req for req in requirements if req.is_satisfied]
    missing = [req for req in requirements if not req.is_satisfied]
    
    return WorkflowAuthAnalysisDTO(
        total_requirements=len(requirements),
        satisfied_count=len(satisfied),
        missing_count=len(missing),
        can_execute=len(missing) == 0,
        all_requirements=requirements,
        satisfied_requirements=satisfied,
        missing_requirements=missing,
        auth_steps=auth_steps,
        auto_triggered=len(auth_steps) > 0
    )


def auth_requirements_to_clarify_oauth_items(
    auth_requirements: List[AuthRequirementDTO],
    planned_steps: List[Dict[str, Any]]
) -> List[ClarifyOAuthItemDTO]:
    """
    Convierte AuthRequirementDTO a ClarifyOAuthItemDTO para frontend compatibility
    
    Args:
        auth_requirements: Lista de AuthRequirementDTO del backend
        planned_steps: Workflow steps para extraer node_id
        
    Returns:
        Lista de ClarifyOAuthItemDTO compatible con frontend
    """
    converted_items = []
    
    for auth_req in auth_requirements:
        try:
            # Find node_id from planned_steps that matches this auth requirement
            node_id = None
            for step in planned_steps:
                if step.get('default_auth') and auth_req.service_id in step.get('default_auth', ''):
                    node_id = step.get('node_id')
                    break
            
            if node_id:
                clarify_oauth = ClarifyOAuthItemDTO(
                    type="oauth",
                    node_id=uuid.UUID(node_id),
                    message=f"Conecta tu cuenta de {auth_req.service_id} para continuar",
                    oauth_url=f"/api/oauth/{auth_req.service_id}/authorize",
                    service_id=auth_req.service_id
                )
                converted_items.append(clarify_oauth)
                
        except Exception as e:
            # Log warning but continue with other items
            print(f"Warning: Failed to convert OAuth requirement for {auth_req.service_id}: {e}")
            continue
    
    return converted_items


