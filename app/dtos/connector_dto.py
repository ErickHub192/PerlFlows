from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from uuid import UUID
from app.dtos.action_dto import ActionDTO
from app.db.models import UsageMode


class ConnectorDTO(BaseModel):
    node_id: UUID = Field(..., description="UUID del nodo/conector")
    name: str = Field(..., description="Nombre del conector")
    usage_mode: Optional[UsageMode] = Field(
        None, description="Cómo se usa este conector dentro de los flujos"
    )
    default_auth: Optional[str] = Field(
        None, description="Método de autenticación por defecto"
    )
    actions: List[ActionDTO] = Field(
        ..., description="Lista de acciones disponibles en este conector"
    )
    model_config = ConfigDict(from_attributes=True)
