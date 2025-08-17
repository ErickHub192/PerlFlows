from pydantic import BaseModel, Field
from typing import Literal
from uuid import UUID

class BranchStepDTO(BaseModel):
    """Paso condicional en un flujo."""

    id: UUID = Field(..., description="Identificador único del paso")
    type: Literal["branch"] = "branch"
    condition: str = Field(..., description="Expresión a evaluar para decidir la rama")
    next_on_true: UUID = Field(..., description="ID del paso siguiente si la condición es verdadera")
    next_on_false: UUID = Field(..., description="ID del paso siguiente si la condición es falsa")
