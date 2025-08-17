from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum

# from app.dtos.step_meta_dto import StepMetaDTO  # 🔧 REMOVED: Using Dict[str, Any] for steps consistency
from app.dtos.clarify_oauth_dto import ClarifyOAuthItemDTO


class WorkflowType(Enum):
    """Tipos de workflows que puede crear Kyra"""
    CLASSIC = "classic"      # Workflows determinísticos tradicionales
    AGENT = "agent"          # Agentes personalizados con IA


# DiscoveryConfidence ELIMINADO - Kyra decide confianza naturalmente


# CapabilityInfoDTO ELIMINADO - Kyra procesa contexto crudo del CAG directamente


# IntentAnalysisResultDTO ELIMINADO - LLM maneja intent naturalmente


class WorkflowCreationResultDTO(BaseModel):
    """Resultado de creación de workflow - REUTILIZA DTOs EXISTENTES"""
    status: str = Field(..., description="Status (ready, oauth_required, needs_clarification)")
    workflow_type: WorkflowType = Field(..., description="Workflow type")
    steps: List[Dict[str, Any]] = Field(default_factory=list, description="Workflow steps")
    execution_plan: List[Dict[str, Any]] = Field(default_factory=list, description="Raw execution plan from LLM planner - source of truth for workflow extraction")
    oauth_requirements: List[ClarifyOAuthItemDTO] = Field(default_factory=list, description="OAuth requirements - REUTILIZA DTO EXISTENTE")
    discovered_resources: List[Dict[str, Any]] = Field(default_factory=list, description="Discovered resources")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence (0.0-1.0) decided by LLM")
    next_actions: List[str] = Field(default_factory=list, description="Next user actions")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    estimated_execution_time: Optional[int] = Field(None, description="Estimated execution time in seconds")
    cost_estimate: Optional[float] = Field(None, description="Estimated cost in USD")
    editable: bool = Field(default=False, description="Whether this workflow can be edited by user feedback")
    finalize: bool = Field(default=False, description="Whether workflow is ready for finalization")
    reply: Optional[str] = Field(None, description="User-facing message about the workflow result")
