# app/services/chat_session_service.py

from uuid import UUID
from typing import Any, Dict, List
from fastapi import Depends

from app.repositories.chat_session_repository import ChatSessionRepository, get_chat_session_repository

class ChatSessionService:
    def __init__(self, repo: ChatSessionRepository):
        self.repo = repo

    async def create_session(self, user_id: int, title: str) -> Dict[str, Any]:
        return await self.repo.create_session(user_id, title)

    async def list_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        return await self.repo.list_sessions(user_id)

    async def get_session(self, session_id: UUID) -> Dict[str, Any]:
        result = await self.repo.get_session(session_id)
        if result is None:
            raise ValueError(f"ChatSession {session_id} not found")
        return result

    async def add_message(self, session_id: UUID, role: str, content: str) -> Dict[str, Any]:
        return await self.repo.add_message(session_id, role, content)

    async def list_messages(self, session_id: UUID) -> List[Dict[str, Any]]:
        return await self.repo.list_messages(session_id)

    async def delete_session(self, session_id: UUID) -> bool:
        """Eliminar una sesión de chat y todos sus mensajes"""
        return await self.repo.delete_session(session_id)

    async def update_session(self, session_id: UUID, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Actualizar datos de una sesión de chat"""
        result = await self.repo.update_session(session_id, update_data)
        if result is None:
            raise ValueError(f"ChatSession {session_id} not found or could not be updated")
        return result

    # Methods needed for ChatTitleService
    async def get_session_by_id(self, session_id: UUID) -> Dict[str, Any]:
        """Get session by ID (alias for get_session)"""
        return await self.get_session(session_id)

    async def count_messages_for_session(self, session_id: UUID) -> int:
        """Count messages for a session"""
        return await self.repo.count_messages_for_session(session_id)

    async def update_session_title(self, session_id: UUID, title: str) -> bool:
        """Update only the title of a session"""
        return await self.repo.update_session_title(session_id, title)

    async def get_messages_for_session(self, session_id: UUID, limit: int = None) -> List[Dict[str, Any]]:
        """Get messages for a session with limit"""
        return await self.repo.get_messages_for_session(session_id, limit)

def get_chat_session_service(
    repo: ChatSessionRepository = Depends(get_chat_session_repository),
) -> ChatSessionService:
    """
    ✅ LIMPIADO: Factory sin interface innecesaria
    """
    return ChatSessionService(repo)
