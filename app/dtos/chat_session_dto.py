# app/dtos/chat_session_dto.py

from uuid import UUID
from datetime import datetime
from typing import List
from pydantic import BaseModel

class ChatSessionDTO(BaseModel):
    session_id: UUID
    title: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


class ChatMessageDTO(BaseModel):
    message_id: UUID
    session_id: UUID
    role: str   # "user" | "assistant"
    content: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


class ChatHistoryDTO(BaseModel):
    session: ChatSessionDTO
    messages: List[ChatMessageDTO]
