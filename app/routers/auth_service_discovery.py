"""
Auth Service Discovery API - Endpoints para descubrir servicios de autenticación
Expone la funcionalidad del AutoAuthTrigger para auth requirements
NO confundir con File Discovery (universal_discovery)
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer

from app.services.auto_auth_trigger import AutoAuthTrigger, get_auto_auth_trigger
from app.services.auth_policy_service import AuthPolicyService, get_auth_policy_service
from app.dtos.auth_requirement_dto import (
    WorkflowAuthAnalysisDTO,
    AuthRequirementDTO,
    AuthStepDTO,
    ServiceAuthConfigDTO
)
from app.mappers.auth_requirement_mapper import auth_policy_to_service_config_dto
from app.core.auth import get_current_user_id
from app.exceptions.api_exceptions import WorkflowProcessingException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth-service-discovery", tags=["Auth Service Discovery"])
security = HTTPBearer()

# ✅ NUEVO: Router simple para compatibilidad frontend
auth_services_router = APIRouter(prefix="/api/auth-services", tags=["Auth Services Compatibility"])


@router.post("/workflow/analyze-auth", response_model=WorkflowAuthAnalysisDTO)
async def analyze_workflow_auth_requirements(
    flow_spec: dict,
    chat_id: str,
    user_id: int = Depends(get_current_user_id),
    auto_auth_trigger: AutoAuthTrigger = Depends(get_auto_auth_trigger)
):
    """
    Analiza auth requirements para un workflow completo
    ✅ AGNÓSTICO - funciona con cualquier workflow
    
    Args:
        flow_spec: Especificación del workflow
        chat_id: ID del chat
        current_user: Usuario autenticado
        
    Returns:
        WorkflowAuthAnalysisDTO con análisis completo
    """
    try:
        # user_id is already provided by dependency
        
        analysis = await auto_auth_trigger.analyze_workflow_auth_requirements(
            flow_spec=flow_spec,
            user_id=user_id,
            chat_id=chat_id
        )
        
        logger.info(f"Workflow auth analysis completed for user {user_id}: "
                   f"{analysis.satisfied_count}/{analysis.total_requirements} satisfied")
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error analyzing workflow auth requirements: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze workflow auth requirements: {str(e)}"
        )


@router.get("/action/{action_id}/auth-requirements", response_model=Optional[AuthRequirementDTO])
async def get_action_auth_requirements(
    action_id: str,
    chat_id: str,
    user_id: int = Depends(get_current_user_id),
    auto_auth_trigger: AutoAuthTrigger = Depends(get_auto_auth_trigger)
):
    """
    Obtiene auth requirements para una acción específica
    ✅ AGNÓSTICO - funciona con cualquier acción
    
    Args:
        action_id: UUID de la acción
        chat_id: ID del chat
        current_user: Usuario autenticado
        
    Returns:
        AuthRequirementDTO o null si no requiere auth
    """
    try:
        # user_id is already provided by dependency
        
        requirement = await auto_auth_trigger.analyze_action_auth_requirements(
            action_id=action_id,
            user_id=user_id,
            chat_id=chat_id
        )
        
        if requirement:
            logger.debug(f"Action {action_id} requires auth: {requirement.service_id}")
        else:
            logger.debug(f"Action {action_id} does not require auth")
        
        return requirement
        
    except Exception as e:
        logger.error(f"Error getting action auth requirements: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get action auth requirements: {str(e)}"
        )


@router.post("/service/{service_id}/auth-step", response_model=Optional[AuthStepDTO])
async def get_auth_step_for_service(
    service_id: str,
    chat_id: str = Query(..., description="Chat ID for context"),
    user_id: int = Depends(get_current_user_id),
    auto_auth_trigger: AutoAuthTrigger = Depends(get_auto_auth_trigger)
):
    """
    Genera auth step para un servicio específico
    ✅ AGNÓSTICO - obtiene mechanism dinámicamente de la BD
    
    Args:
        service_id: ID del servicio
        chat_id: ID del chat
        current_user: Usuario autenticado
        
    Returns:
        AuthStepDTO o null si ya está autenticado o no existe
    """
    try:
        # user_id is already provided by dependency
        
        auth_step = await auto_auth_trigger.get_auth_step_for_service(
            service_id=service_id,
            user_id=user_id,
            chat_id=chat_id
        )
        
        if auth_step:
            logger.info(f"Generated auth step for service {service_id}: {auth_step.type}")
        else:
            logger.debug(f"No auth step needed for service {service_id}")
        
        return auth_step
        
    except Exception as e:
        logger.error(f"Error getting auth step for service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get auth step for service: {str(e)}"
        )


@router.post("/workflow/validate-auth")
async def validate_workflow_auth_requirements(
    flow_spec: dict,
    chat_id: str,
    user_id: int = Depends(get_current_user_id),
    auto_auth_trigger: AutoAuthTrigger = Depends(get_auto_auth_trigger)
):
    """
    Valida que todos los auth requirements estén satisfechos
    ✅ AGNÓSTICO - funciona con cualquier workflow
    
    Args:
        flow_spec: Especificación del workflow
        chat_id: ID del chat
        current_user: Usuario autenticado
        
    Returns:
        Dict con can_execute y missing_services
    """
    try:
        # user_id is already provided by dependency
        
        can_execute, missing_services = await auto_auth_trigger.validate_all_requirements_satisfied(
            flow_spec=flow_spec,
            user_id=user_id,
            chat_id=chat_id
        )
        
        logger.info(f"Workflow validation for user {user_id}: "
                   f"can_execute={can_execute}, missing={len(missing_services)}")
        
        return {
            "can_execute": can_execute,
            "missing_services": missing_services,
            "missing_count": len(missing_services)
        }
        
    except Exception as e:
        logger.error(f"Error validating workflow auth requirements: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate workflow auth requirements: {str(e)}"
        )


@router.get("/services/available", response_model=List[ServiceAuthConfigDTO])
async def get_available_services(
    active_only: bool = True,
    user_id: int = Depends(get_current_user_id),
    auth_policy_service: AuthPolicyService = Depends(get_auth_policy_service)
):
    """
    Lista todos los servicios disponibles para autenticación
    ✅ AGNÓSTICO - lista dinámicamente desde BD
    
    Args:
        active_only: Solo servicios activos
        current_user: Usuario autenticado
        
    Returns:
        Lista de ServiceAuthConfigDTO
    """
    try:
        policies = await auth_policy_service.get_all_active_policies()
        
        services = []
        for policy_data in policies:
            if not active_only or policy_data.get("is_active", True):
                # Convert to AuthPolicy model-like object for mapping
                class PolicyModel:
                    def __init__(self, data):
                        self.service_id = data.get("auth_string", "").replace("oauth2_", "").replace("api_key_", "")
                        self.mechanism = data.get("mechanism", "oauth2")
                        self.provider = data.get("provider", "")
                        self.service = data.get("service")
                        self.display_name = data.get("display_name", "")
                        self.description = data.get("description", "")
                        self.icon_url = None  # Not in current schema
                        self.max_scopes = data.get("max_scopes", [])
                        self.base_auth_url = data.get("base_auth_url", "")
                        self.auth_config = {}
                        self.is_active = data.get("is_active", True)
                
                policy_model = PolicyModel(policy_data)
                service_dto = auth_policy_to_service_config_dto(policy_model)
                services.append(service_dto)
        
        logger.info(f"Retrieved {len(services)} available services")
        return services
        
    except Exception as e:
        logger.error(f"Error getting available services: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get available services: {str(e)}"
        )


@router.get("/mechanisms/supported")
async def get_supported_auth_mechanisms(
    user_id: int = Depends(get_current_user_id)
):
    """
    Lista mecanismos de autenticación soportados
    ✅ AGNÓSTICO - obtiene de registry dinámicamente
    
    Args:
        current_user: Usuario autenticado
        
    Returns:
        Lista de mecanismos soportados
    """
    try:
        from app.services.auth_handler_registry import get_auth_handler_registry
        
        registry = get_auth_handler_registry()
        mechanisms = registry.get_supported_mechanisms()
        
        logger.debug(f"Supported auth mechanisms: {mechanisms}")
        
        return {
            "supported_mechanisms": mechanisms,
            "total_count": len(mechanisms)
        }
        
    except Exception as e:
        logger.error(f"Error getting supported mechanisms: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get supported mechanisms: {str(e)}"
        )


@router.post("/auto-discover")
async def auto_discover_services(
    request: dict,
    user_id: int = Depends(get_current_user_id),
    auth_policy_service: AuthPolicyService = Depends(get_auth_policy_service)
):
    """
    Auto-descubrimiento de servicios disponibles para el usuario
    ✅ NUEVO ENDPOINT para compatibilidad con frontend
    Usa la arquitectura actual sin keywords ni scores
    
    Args:
        request: Dict con user_intent y context
        user_id: Usuario autenticado
        
    Returns:
        Lista de servicios disponibles
    """
    try:
        user_intent = request.get("user_intent", "")
        context = request.get("context", "dashboard_discovery")
        
        logger.info(f"Auto-discovery request for user {user_id}, intent: '{user_intent}', context: '{context}'")
        
        # Obtener todos los servicios activos disponibles
        policies = await auth_policy_service.get_all_active_policies()
        
        # Convertir a formato esperado por el frontend
        suggestions = []
        for policy_data in policies:
            if not policy_data.get("is_active", True):
                continue
                
            service_config = {
                "service_id": policy_data.get("service_id", ""),
                "name": policy_data.get("display_name", policy_data.get("service_id", "")),
                "description": policy_data.get("description", "Servicio disponible para integración"),
                "confidence": 1.0,  # Todos los servicios activos son igualmente válidos
                "suggested_actions": [],  # Frontend puede definir acciones por servicio
                "provider": policy_data.get("provider", ""),
                "mechanism": policy_data.get("mechanism", ""),
                "service_category": policy_data.get("service", "")
            }
            
            suggestions.append(service_config)
        
        logger.info(f"Auto-discovery found {len(suggestions)} available services for user {user_id}")
        
        return {
            "suggestions": suggestions,
            "total_found": len(suggestions),
            "user_intent": user_intent,
            "context": context,
            "message": f"Encontrados {len(suggestions)} servicios disponibles"
        }
        
    except Exception as e:
        logger.error(f"Error in auto-discover: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to auto-discover services: {str(e)}"
        )


@router.post("/missing-auth/trigger", response_model=List[AuthStepDTO])
async def trigger_missing_auth_flows(
    missing_requirements: List[AuthRequirementDTO],
    chat_id: str,
    user_id: int = Depends(get_current_user_id),
    auto_auth_trigger: AutoAuthTrigger = Depends(get_auto_auth_trigger)
):
    """
    Dispara flows de autenticación para requirements faltantes
    ✅ AGNÓSTICO - usa registry pattern
    
    Args:
        missing_requirements: Lista de requirements no satisfechos
        chat_id: ID del chat
        current_user: Usuario autenticado
        
    Returns:
        Lista de AuthStepDTO para ejecutar
    """
    try:
        # user_id is already provided by dependency
        
        auth_steps = await auto_auth_trigger.trigger_missing_auth_flows_agnostic(
            missing_requirements=missing_requirements,
            user_id=user_id,
            chat_id=chat_id
        )
        
        logger.info(f"Triggered {len(auth_steps)} auth flows for user {user_id}")
        
        return auth_steps
        
    except Exception as e:
        logger.error(f"Error triggering missing auth flows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger missing auth flows: {str(e)}"
        )


# ✅ ENDPOINT DE COMPATIBILIDAD FRONTEND
@auth_services_router.get("")
async def get_auth_services_for_frontend(
    user_id: int = Depends(get_current_user_id),
    auth_policy_service: AuthPolicyService = Depends(get_auth_policy_service)
):
    """
    Endpoint de compatibilidad para el frontend.
    El frontend espera /api/services pero devolvemos formato compatible.
    """
    try:
        policies = await auth_policy_service.get_all_active_policies()
        
        services = []
        for policy_data in policies:
            if policy_data.get("is_active", True):
                services.append({
                    "service_id": policy_data.get("service_id"),
                    "mechanism": policy_data.get("mechanism"),
                    "provider": policy_data.get("provider"),
                    "display_name": policy_data.get("display_name"),
                    "description": policy_data.get("description"),
                    "ui_metadata": {
                        "name": policy_data.get("display_name"),
                        "category": get_category_by_mechanism(policy_data.get("mechanism")),
                        "icon": get_icon_by_service_id(policy_data.get("service_id"))
                    }
                })
        
        return {"services": services}
        
    except Exception as e:
        logger.error(f"Error getting services for frontend: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get services: {str(e)}"
        )


def get_category_by_mechanism(mechanism: str) -> str:
    """Helper para categorizar servicios por mechanism"""
    mapping = {
        "oauth2": "OAuth Services",
        "api_key": "API Key Services", 
        "bot_token": "Bot Token Services",
        "db_credentials": "Database Services"
    }
    return mapping.get(mechanism, "Otros")


