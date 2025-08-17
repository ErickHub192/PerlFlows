from typing import Optional
from pydantic import BaseModel, ConfigDict
from uuid import UUID

class ActionDTO(BaseModel):
    action_id: UUID
    node_id: UUID
    name: str
    description: Optional[str] = None
    is_trigger: bool = False
    
    model_config = ConfigDict(from_attributes=True)
        
