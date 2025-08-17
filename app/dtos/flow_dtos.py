from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime
from app.dtos.step_meta_dto import StepMetaDTO

class FlowSummaryDTO(BaseModel):
    model_config = {"from_attributes": True}  # 🔧 FIX: Enable from_orm() in Pydantic v2
    
    flow_id: UUID
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    chat_id: Optional[UUID] = None
    chat_title: Optional[str] = None

class FlowDetailDTO(FlowSummaryDTO):
    spec: Optional[Dict[str, Any]] = None

class CreateFlowRequestDTO(BaseModel):
    """DTO para crear un nuevo flow"""
    name: str = Field(..., description="Nombre del workflow")
    description: Optional[str] = Field(None, description="Descripción opcional del workflow")
    spec: Dict[str, Any] = Field(..., description="Especificación completa del workflow")

class CreateFlowResponseDTO(BaseModel):
    model_config = {"from_attributes": True}  # 🔧 FIX: Enable from_orm() in Pydantic v2
    
    """DTO de respuesta al crear un flow"""
    flow_id: UUID
    name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    success: bool = True
    message: str = "Workflow guardado exitosamente"

# PlannerResponseDTO y ValidateResponseDTO removidos - endpoints eliminados
    
    # DTO para peticiones de dry-run
class DryRunRequestDTO(BaseModel):
    """
    DTO para simular (dry-run) un flujo completo sin ejecutar acciones reales.
    """
    flow_id: UUID = Field(..., description="ID del flujo a simular")
    steps: List[StepMetaDTO] = Field(
        ..., description="Lista de pasos con metadata para dry-run (incluye retries, timeout_ms)"
    )
    user_id: int = Field(..., description="ID de usuario que solicita la simulación")
    test_inputs: Optional[Dict[str, Any]] = Field(
        None, description="Inputs personalizados para la simulación, si aplica"
    )

class InMemoryWorkflowRunRequestDTO(BaseModel):
    """
    DTO para ejecutar workflows temporales sin guardarlos (n8n-style execution).
    """
    steps: List[Dict[str, Any]] = Field(
        ..., description="Lista de pasos en formato workflow engine"
    )
    user_id: int = Field(..., description="ID de usuario que solicita la ejecución")
    inputs: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Inputs del workflow"
    )
    simulate: bool = Field(
        default=False, description="Si es simulación (true) o ejecución real (false)"
    )
    
class ToggleFlowDTO(BaseModel):
    is_active: bool = Field(..., description="True para activar, False para desactivar")
    

    
