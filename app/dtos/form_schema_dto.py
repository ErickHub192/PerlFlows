from pydantic import BaseModel
from typing import Dict, List

class FormSchemaDTO(BaseModel):
    title: str
    type: str
    properties: Dict[str, dict]
    required: List[str]
