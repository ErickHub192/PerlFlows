from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from uuid import UUID
from app.dtos.action_dto import ActionDTO

from app.db.models import UsageMode

class NodeDTO(BaseModel):
    node_id: UUID
    name: str
    node_type: str
    usage_mode: Optional[UsageMode] = None
    default_auth: Optional[str] = None
    use_case:   Optional[str] = None

    actions: List[ActionDTO] = []

    # Pydantic v2: habilita leer atributos de instancias ORM
    model_config = ConfigDict(from_attributes=True)

