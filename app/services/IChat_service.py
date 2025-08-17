from abc import ABC, abstractmethod
from typing import List, Dict, Any
from uuid import UUID
from app.models.chat_models import ChatResponseModel

class IChatService(ABC):
    @abstractmethod
    async def process_chat(
        self,
        session_id: UUID,
        user_message: str,
        conversation: List[Dict[str, Any]],
        user_id: int,
        db_session,
        workflow_type: str = None
    ) -> ChatResponseModel:
        """
        Procesa el mensaje de chat junto con el historial de conversación
        y retorna un objeto ChatResponseModel.
        """
        pass
