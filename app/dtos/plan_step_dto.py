# app/dtos/plan_step_dto.py
from pydantic import BaseModel
from uuid import UUID

class PlanStepDTO(BaseModel):
    node_id: UUID
    action_id: UUID

