"""
ConversationMemoryRepository - Repository para operaciones de DB de memoria persistente
Maneja solo operaciones de base de datos, sin lógica de negocio
"""
import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.db.models import ChatMessage, ChatSession

logger = logging.getLogger(__name__)


class ConversationMemoryRepository:
    """
    Repository para operaciones de base de datos de memoria persistente
    """
    
    async def get_chat_session(self, db_session: AsyncSession, chat_id: UUID) -> Optional[ChatSession]:
        """
        Obtiene una sesión de chat por ID
        """
        try:
            stmt = select(ChatSession).filter(ChatSession.session_id == chat_id)
            result = await db_session.execute(stmt)
            return result.scalars().first()
        except Exception as e:
            logger.error(f"🗄️ REPO ERROR: No se pudo obtener sesión {chat_id}: {e}")
            return None
    
    async def create_chat_session(self, db_session: AsyncSession, chat_id: UUID, user_id: int, title: str = "Kyra Workflow Chat") -> ChatSession:
        """
        Crea una nueva sesión de chat
        """
        try:
            session = ChatSession(
                session_id=chat_id,
                user_id=user_id,
                title=title
            )
            db_session.add(session)
            await db_session.flush()  # Repository hace flush, Service hace commit
            logger.debug(f"🗄️ REPO: Creada nueva sesión de chat: {chat_id}")
            return session
        except Exception as e:
            logger.error(f"🗄️ REPO ERROR: No se pudo crear sesión {chat_id}: {e}")
            raise
    
    async def get_messages_by_session(self, db_session: AsyncSession, chat_id: UUID) -> List[ChatMessage]:
        """
        Obtiene todos los mensajes de una sesión ordenados por fecha
        """
        try:
            stmt = select(ChatMessage).filter(
                ChatMessage.session_id == chat_id
            ).order_by(ChatMessage.created_at.asc())
            result = await db_session.execute(stmt)
            messages = result.scalars().all()
            logger.debug(f"🗄️ REPO: Recuperados {len(messages)} mensajes de la sesión {chat_id}")
            return messages
        except Exception as e:
            logger.error(f"🗄️ REPO ERROR: No se pudo obtener mensajes de {chat_id}: {e}")
            return []
    
    async def create_message(self, db_session: AsyncSession, chat_id: UUID, role: str, content: str) -> ChatMessage:
        """
        Crea un nuevo mensaje en la sesión
        """
        try:
            message = ChatMessage(
                session_id=chat_id,
                role=role,
                content=content
            )
            db_session.add(message)
            await db_session.flush()  # Repository hace flush, Service hace commit
            logger.debug(f"🗄️ REPO: Creado mensaje {role}: {content[:50]}...")
            return message
        except Exception as e:
            logger.error(f"🗄️ REPO ERROR: No se pudo crear mensaje: {e}")
            raise
    
    async def update_message_content(self, db_session: AsyncSession, message_id: UUID, new_content: str):
        """
        🔧 NEW: Updates the content of an existing message
        """
        try:
            from sqlalchemy import update
            
            stmt = update(ChatMessage).where(
                ChatMessage.message_id == message_id
            ).values(content=new_content)
            
            await db_session.execute(stmt)
            await db_session.flush()  # 🔧 CRITICAL FIX: Flush after UPDATE operation
            logger.debug(f"🗄️ REPO: Updated and flushed message {message_id} content")
            
        except Exception as e:
            logger.error(f"🗄️ REPO ERROR: Could not update message {message_id}: {e}")
            raise


# Singleton instance
_conversation_memory_repository = None

def get_conversation_memory_repository() -> ConversationMemoryRepository:
    """
    Obtiene la instancia singleton del ConversationMemoryRepository
    """
    global _conversation_memory_repository
    if _conversation_memory_repository is None:
        _conversation_memory_repository = ConversationMemoryRepository()
    return _conversation_memory_repository