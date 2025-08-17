# app/dtos/workflow_run_request_dto.py

from pydantic import BaseModel, Field
from typing import List, Dict, Any

class WorkflowRunRequestDTO(BaseModel):
    """
    DTO para solicitar la ejecución de un flujo.
    """
    user_id: int = Field(
        ...,
        description="ID del usuario que inicia la ejecución del flujo."
    )
    steps: List[Dict[str, Any]] = Field(
        ...,
        min_items=1,
        description="Lista de pasos generados por el planner; "
                    "cada elemento debe incluir al menos 'node_id' y, si aplica, 'action' y 'params'."
    )
    inputs: Dict[str, Any] = Field(
        default_factory=dict,
        description="Mapeo de valores que el usuario suministra para los parámetros de cada paso."
    )
