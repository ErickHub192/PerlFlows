# app/dtos/flow_execution_dto.py

from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Dict, Optional, Literal,List
from uuid import UUID
from datetime import datetime

class FlowExecutionDTO(BaseModel):
    """
    DTO para exponer la fila de la tabla `flow_executions` en la API:
      - execution_id: UUID de la ejecución.
      - flow_id: UUID del flujo asociado.
      - inputs: parámetros de entrada suministrados.
      - outputs: resultados finales de la ejecución.
      - status: estado actual o final de la ejecución.
      - cost: costo total estimado o real de la ejecución.
      - error: mensaje de error si ocurrió una falla.
      - started_at: timestamp de inicio.
      - ended_at: timestamp de fin (puede ser None si sigue en curso).
    """
    execution_id: UUID = Field(
        ...,
        description="Identificador único de esta ejecución."
    )
    flow_id: UUID = Field(
        ...,
        description="Identificador del flujo ejecutado."
    )
    inputs: Dict[str, Any] = Field(
        default_factory=dict,
        description="Mapa de valores de entrada para los pasos del flujo."
    )
    outputs: Optional[Dict[str, Any]] = Field(
        None,
        description="Mapa de valores de salida producidos por la ejecución."
    )
    status: Literal["running", "success", "failure", "error"] = Field(
        ...,
        description="Estado de la ejecución (running | success | failure | error)."
    )
    cost: Optional[float] = Field(
        None,
        ge=0,
        description="Costo total de la ejecución en la unidad definida, si está disponible."
    )
    error: Optional[str] = Field(
        None,
        description="Mensaje de error en caso de que la ejecución haya fallado."
    )
    started_at: datetime = Field(
        ...,
        description="Fecha y hora en que inició la ejecución."
    )
    ended_at: Optional[datetime] = Field(
        None,
        description="Fecha y hora en que terminó la ejecución (None si aún está en curso)."
    )

class FlowExecutionStepDTO(BaseModel):
    step_id: UUID = Field(..., description="ID del paso de ejecución.")
    execution_id: UUID = Field(..., description="ID de la ejecución padre.")
    node_id: UUID = Field(..., description="ID del nodo ejecutado.")
    action_id: UUID = Field(..., description="ID de la acción ejecutada.")
    status: Literal["running", "ok", "error"] = Field(
        ..., description="Estado del paso: running | ok | error."
    )
    error: Optional[str] = Field(None, description="Mensaje de error si falló el paso.")
    started_at: datetime = Field(..., description="Timestamp de inicio del paso.")
    ended_at: Optional[datetime] = Field(None, description="Timestamp de fin del paso.")

    model_config = ConfigDict(from_attributes=True)


class FlowExecutionDetailDTO(BaseModel):
    execution: FlowExecutionDTO
    steps: List[FlowExecutionStepDTO]

    model_config = ConfigDict(from_attributes=True)


