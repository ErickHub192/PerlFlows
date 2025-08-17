"""
Interfaces base para el WorkflowEngine modular
Diseñado para máxima extensibilidad y backward compatibility
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union

from app.dtos.step_meta_dto import StepMetaDTO
from app.dtos.workflow_creation_result_dto import (
    WorkflowType, 
    WorkflowCreationResultDTO
)
from app.dtos.clarify_oauth_dto import ClarifyOAuthItemDTO

# Type aliases para backward compatibility
WorkflowCreationResult = WorkflowCreationResultDTO
OAuthRequirement = ClarifyOAuthItemDTO
# CapabilityInfo ELIMINADO - Kyra procesa contexto crudo del CAG directamente
# IntentAnalysisResult ELIMINADO - LLM maneja intent naturalmente


class IDiscoveryProvider(ABC):
    """
    Interface para diferentes estrategias de discovery
    Permite que CAG, Universal Discovery, y futuros providers coexistan
    """
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nombre único del provider"""
        pass
    
    @property
    @abstractmethod
    def provider_type(self) -> str:
        """Tipo de provider: 'cag', 'universal', 'hybrid'"""
        pass
    
    @abstractmethod
    async def discover_raw_context(
        self, 
        intent: str, 
        user_id: int,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Descubre contexto crudo sin filtros para Kyra
        
        Args:
            intent: Intención del usuario ("automatizar inventario")
            user_id: ID del usuario
            context: Contexto adicional (historial, preferencias, etc.)
            
        Returns:
            Contexto crudo del CAG/provider sin pre-procesamiento
        """
        pass
    
    @abstractmethod
    async def check_oauth_requirements(
        self, 
        raw_context: Dict[str, Any],
        user_id: int
    ) -> List[ClarifyOAuthItemDTO]:
        """
        Verifica qué OAuth flows son necesarios
        
        Args:
            raw_context: Contexto crudo del discovery
            user_id: ID del usuario
            
        Returns:
            Lista de requerimientos OAuth pendientes
        """
        pass
    
    @abstractmethod
    async def validate_raw_context(
        self, 
        raw_context: Dict[str, Any], 
        user_id: int
    ) -> Dict[str, Any]:
        """
        Valida contexto crudo y retorna contexto limpio para Kyra
        
        Args:
            raw_context: Contexto crudo a validar
            user_id: ID del usuario
            
        Returns:
            Contexto validado listo para Kyra
        """
        pass


# IPlanningStrategy ELIMINADO - LLM maneja planning naturalmente


# IIntentAnalyzer ELIMINADO - LLM maneja intent naturalmente


# Exceptions específicas del WorkflowEngine
class WorkflowEngineException(Exception):
    """Base exception para WorkflowEngine"""
    pass


class DiscoveryException(WorkflowEngineException):
    """Error en proceso de discovery"""
    pass


class PlanningException(WorkflowEngineException):
    """Error en proceso de planning"""
    pass


class OAuthRequiredException(WorkflowEngineException):
    """OAuth requerido antes de continuar"""
    
    def __init__(self, oauth_requirements: List[ClarifyOAuthItemDTO]):
        self.oauth_requirements = oauth_requirements
        # Extract service info from ClarifyOAuthItemDTO (has different fields than AuthRequirementDTO)
        oauth_services = []
        for req in oauth_requirements:
            if hasattr(req, 'oauth_url') and '/auth/' in req.oauth_url:
                # Extract provider from oauth_url like "/auth/gmail/authorize" 
                provider = req.oauth_url.split('/auth/')[1].split('/')[0]
                oauth_services.append(provider)
            else:
                oauth_services.append('oauth_service')
        super().__init__(f"OAuth required for: {oauth_services}")


class InsufficientCapabilitiesException(WorkflowEngineException):
    """No hay suficientes capacidades para completar la intención"""
    pass


class IWorkflowEngine(ABC):
    """
    Interface principal del WorkflowEngine
    Coordina discovery, planning y creation de workflows
    """
    
    @abstractmethod
    async def create_workflow_from_intent(
        self,
        user_message: str,
        user_id: int,
        conversation: List[Dict[str, Any]] = None,
        workflow_type: Optional[WorkflowType] = None
    ) -> WorkflowCreationResultDTO:
        """
        Crea un workflow completo a partir de una intención del usuario
        
        Args:
            user_message: Mensaje/intención del usuario
            user_id: ID del usuario
            conversation: Historial de conversación
            workflow_type: Tipo específico de workflow (opcional)
            
        Returns:
            Resultado completo de la creación del workflow
        """
        pass
    
    # analyze_intent ELIMINADO - LLM maneja intent naturalmente
    # discover_capabilities ELIMINADO - Kyra procesa contexto crudo directamente