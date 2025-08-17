# app/models/form_payload.py
from pydantic import BaseModel
from uuid import UUID
from typing import Any, Dict

class FormData(BaseModel):
    node: UUID
    action: UUID
    params: Dict[str, Any]

class FormPayload(BaseModel):
    form: FormData
