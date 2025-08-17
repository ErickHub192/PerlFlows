from typing import List
from pydantic import BaseModel, ConfigDict
from uuid import UUID

from app.dtos.question_dto import QuestionDTO

class NodeSelectionDTO(BaseModel):
    node_id: UUID
    action_id: UUID
    model_config = ConfigDict(from_attributes=True)

class LLMResponseDTO(BaseModel):
    nodes: List[NodeSelectionDTO]
    questions: List[QuestionDTO] = []
    model_config = ConfigDict(from_attributes=True)
