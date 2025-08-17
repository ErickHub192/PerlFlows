# app/dtos/question_dto.py

from pydantic import BaseModel, ConfigDict
from typing import Literal, List, Optional
from uuid import UUID

class QuestionDTO(BaseModel):
    id: str                            # identificador interno de la pregunta
    question: str                      # texto a mostrar
    type: Literal["text", "select", "time", "number"] = "text"
    options: Optional[List[str]] = None   # para type="select"
    schemaEndpoint: Optional[str] = None  # URL para el JSON Schema (si es formulario complejo)
    node_id: Optional[UUID] = None
    action_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)
