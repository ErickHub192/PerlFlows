# app/dtos/parameter_dto.py

from typing import Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

class ActionParamDTO(BaseModel):
    param_id: UUID = Field(
        ..., description="UUID del parámetro"
    )
    action_id: UUID = Field(
        ..., description="UUID de la acción asociada"
    )
    name: str = Field(
        ..., description="Nombre del parámetro"
    )
    description: Optional[str] = Field(
        None, description="Descripción del parámetro"
    )
    required: bool = Field(
        ..., description="Indica si el parámetro es obligatorio"
    )
    param_type: str = Field(
        ..., description="Tipo de parámetro (string, integer, enum, etc.)"
    )
    options: Optional[List[Any]] = Field(
        None,
        description="Opciones si `param_type` es ‘enum’ o ‘select’"
    )
    default: Optional[Any] = Field(
        None, description="Valor por defecto del parámetro"
    )

    # Para poder crear desde ORM u otros dicts
    model_config = ConfigDict(from_attributes=True)
