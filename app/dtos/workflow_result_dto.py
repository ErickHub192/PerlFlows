# app/dtos/workflow_result_dto.py

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Literal
from app.dtos.step_result_dto import StepResultDTO

class WorkflowResultDTO(BaseModel):
    """
    DTO con el resultado de la ejecución de un flujo:
      - steps: lista de resultados de cada paso.
      - overall_status: estado global de la ejecución.
    """
    steps: List[StepResultDTO] = Field(
        ...,
        description="Resultados detallados de cada paso: node_id, action_id, status, output, error, duration_ms."
    )
    overall_status: Literal["success", "partial_failure", "failure"] = Field(
        ...,
        description="Estado global de la ejecución (success | partial_failure | failure)."
    )

    # Permite crear el DTO a partir de un objeto con atributos análogos
    model_config = ConfigDict(from_attributes=True)
