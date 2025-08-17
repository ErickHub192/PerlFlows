from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ChatSessionCreateDTO(BaseModel):
    title: str = "Nuevo chat"


class ChatMessageCreateDTO(BaseModel):
    role: str   # "user" | "assistant"
    content: str
