# app/dtos/step_result_dto.py

from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Optional, Literal
from uuid import UUID

class StepResultDTO(BaseModel):
    """
    DTO con el resultado de un paso individual en la ejecución de un flujo:
      - node_id: identificador del nodo.
      - action_id: identificador de la acción invocada.
      - status: 'success' o 'error'.
      - output: datos retornados por la acción si tuvo éxito.
      - error: mensaje de error si ocurrió una falla.
      - duration_ms: tiempo de ejecución en milisegundos.
    """
    node_id: UUID = Field(
        ...,
        description="ID del nodo que se ejecutó."
    )
    action_id: UUID = Field(
        ...,
        description="ID de la acción invocada en este paso."
    )
    status: Literal["success", "error"] = Field(
        ...,
        description="Estado del paso: 'success' si todo fue bien, 'error' si falló."
    )
    output: Any = Field(
        ...,
        description="Resultado devuelto por la acción cuando tuvo éxito."
    )
    error: Optional[str] = Field(
        None,
        description="Mensaje de error si el paso terminó en 'error'."
    )
    duration_ms: int = Field(
        ...,
        ge=0,
        description="Duración del paso en milisegundos (>= 0)."
    )

    # Permite inicializar desde un objeto con atributos similares
    model_config = ConfigDict(from_attributes=True)
