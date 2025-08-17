"""
Response Builder - Construcción centralizada de respuestas estándar
Elimina la duplicación de lógica de construcción de WorkflowCreationResult
"""
from typing import List, Dict, Any, Optional
from ..core.interfaces import (
    WorkflowCreationResult, WorkflowType, 
    OAuthRequirement
)


class ResponseBuilder:
    """
    Maneja la construcción consistente de respuestas WorkflowCreationResult
    """
    
    @staticmethod
    def build_oauth_required_response(
        workflow_type: WorkflowType,
        oauth_requirements: List[OAuthRequirement],
        selected_services: Optional[List[str]] = None,
        execution_plan: Optional[List[Dict[str, Any]]] = None
    ) -> WorkflowCreationResult:
        """
        Construye respuesta estándar para OAuth requerido (sin intent analysis)
        """
        metadata = {}
        if selected_services:
            metadata["selected_services"] = selected_services
            
        return WorkflowCreationResult(
            status="oauth_required",
            workflow_type=workflow_type,
            steps=[],
            execution_plan=execution_plan or [],
            oauth_requirements=oauth_requirements,
            discovered_resources=[],
            confidence=0.6,  # Default reasonable, Kyra will override
            next_actions=[f"Autorizar {ResponseBuilder._extract_provider_from_oauth_item(req)}" for req in oauth_requirements],
            metadata=metadata
        )
    
    @staticmethod
    def build_error_response(
        error: Exception,
        workflow_type: WorkflowType = WorkflowType.CLASSIC,
        selected_services: Optional[List[str]] = None,
        custom_actions: Optional[List[str]] = None,
        execution_plan: Optional[List[Dict[str, Any]]] = None
    ) -> WorkflowCreationResult:
        """
        Construye respuesta estándar para errores
        """
        metadata = {
            "error": str(error),
            "error_type": type(error).__name__
        }
        if selected_services:
            metadata["selected_services"] = selected_services
            
        next_actions = custom_actions or ["Intentar de nuevo", "Contactar soporte"]
        
        return WorkflowCreationResult(
            status="error",
            workflow_type=workflow_type,
            steps=[],
            execution_plan=execution_plan or [],
            oauth_requirements=[],
            discovered_resources=[],
            confidence=0.3,  # Low confidence for errors
            next_actions=next_actions,
            metadata=metadata,
            estimated_execution_time=None,
            cost_estimate=None
        )
    
    @staticmethod
    def build_success_response(
        workflow_type: WorkflowType,
        steps: List[Dict[str, Any]],
        confidence: float,
        discovered_resources: List[Dict[str, Any]] = None,
        estimated_execution_time: Optional[float] = None,
        cost_estimate: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        editable: bool = True,
        finalize: bool = True,
        oauth_requirements: List[OAuthRequirement] = None,
        oauth_already_satisfied: bool = False,
        execution_plan: Optional[List[Dict[str, Any]]] = None
    ) -> WorkflowCreationResult:
        """
        Construye respuesta estándar para éxito
        """
        final_metadata = metadata or {}
        if oauth_already_satisfied:
            final_metadata["oauth_already_satisfied"] = True
            
        return WorkflowCreationResult(
            status="success",
            workflow_type=workflow_type,
            steps=steps,
            execution_plan=execution_plan or steps,  # Default to steps if no execution_plan provided
            oauth_requirements=oauth_requirements or [],
            discovered_resources=discovered_resources or [],
            confidence=confidence,
            next_actions=["Ejecutar workflow"],
            metadata=final_metadata,
            estimated_execution_time=estimated_execution_time,
            cost_estimate=cost_estimate,
            editable=editable,
            finalize=finalize
        )
    
    @staticmethod
    def _extract_provider_from_oauth_item(oauth_item) -> str:
        """
        🔥 Helper to extract provider from ClarifyOAuthItemDTO
        Handles both old AuthRequirementDTO and new ClarifyOAuthItemDTO formats
        """
        # Try old format first (AuthRequirementDTO)
        if hasattr(oauth_item, 'provider'):
            return oauth_item.provider
        
        # Try new format (ClarifyOAuthItemDTO)
        if hasattr(oauth_item, 'oauth_url') and oauth_item.oauth_url:
            oauth_url = oauth_item.oauth_url
            if '/auth/' in oauth_url:
                # Extract provider from "/auth/gmail/authorize" -> "gmail"
                provider = oauth_url.split('/auth/')[1].split('/')[0]
                return provider
        
        # Fallback
        return "servicio"