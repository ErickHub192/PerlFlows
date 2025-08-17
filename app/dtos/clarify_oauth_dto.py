# app/dtos/clarify_oauth_dto.py
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from uuid import UUID

class ClarifyOAuthItemDTO(BaseModel):
    type: Literal["oauth"] = Field(..., description="Indica que esta clarificación es un flujo OAuth")
    node_id: UUID = Field(..., description="ID del nodo que requiere autorización OAuth")
    message: str = Field(..., description="Mensaje de instrucción para mostrar al usuario")
    oauth_url: str = Field(..., description="URL donde el frontend iniciará el flujo OAuth")
    service_id: str = Field(..., description="ID del servicio que requiere autorización (ej: 'gmail', 'google-drive')")

    model_config = ConfigDict(from_attributes=True)
