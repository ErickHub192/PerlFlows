# app/models/agent_config.py

from pydantic import BaseModel
from typing import List, Any, Dict
from uuid import UUID

class AgentConfig(BaseModel):
    agent_id: UUID
    name: str
    default_prompt: str
    tools: List[str]
    memory_schema: Dict[str, Any]
    model: str
    temperature: float
    max_iterations: int
