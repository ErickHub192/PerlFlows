# app/repositories/chat_session_repository.py

from typing import Any, Dict, List
from uuid import UUID
import logging

from sqlalchemy import select, insert, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.db.database import get_db
from app.db.models import ChatSession, ChatMessage

logger = logging.getLogger(__name__)


class ChatSessionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(self, user_id: int, title: str) -> Dict[str, Any]:
        stmt = (
            insert(ChatSession)
            .values(user_id=user_id, title=title)
            .returning(ChatSession)
        )
        res = await self.db.execute(stmt)
        # ✅ Repository no maneja transacciones - solo flush
        await self.db.flush()
        new = res.scalar_one()
        return new.__dict__

    async def list_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        # 🔧 STABLE ORDERING: created_at DESC + session_id para consistencia total
        stmt = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.created_at.desc(), ChatSession.session_id.desc())
        )
        res = await self.db.execute(stmt)
        sessions = res.scalars().all()
        
        # 🔍 DEBUG: Log sidebar requests para detectar patrones
        logger.debug(f"📋 SIDEBAR: Retrieved {len(sessions)} sessions for user {user_id}")
        
        return [s.__dict__ for s in sessions]

    async def get_session(self, session_id: UUID) -> Dict[str, Any]:
        stmt = select(ChatSession).where(ChatSession.session_id == session_id)
        res = await self.db.execute(stmt)
        session = res.scalar_one_or_none()
        return session.__dict__ if session else None

    async def add_message(self, session_id: UUID, role: str, content: str) -> Dict[str, Any]:
        # 🚨 CRITICAL FIX: Add message deduplication to prevent exact duplicates
        from datetime import datetime, timedelta
        
        # Check for duplicate messages in the last 10 seconds
        cutoff_time = datetime.utcnow() - timedelta(seconds=10)
        duplicate_check = (
            select(ChatMessage)
            .where(
                ChatMessage.session_id == session_id,
                ChatMessage.role == role,
                ChatMessage.content == content,
                ChatMessage.created_at >= cutoff_time
            )
            .limit(1)
        )
        
        res = await self.db.execute(duplicate_check)
        existing_msg = res.scalar_one_or_none()
        
        if existing_msg:
            logger.info(f"🚫 BACKEND DEDUP: Prevented duplicate message - role: {role}, content: {content[:50]}...")
            # Return the existing message instead of creating a duplicate
            return existing_msg.__dict__
        
        # No duplicate found, create new message
        stmt = (
            insert(ChatMessage)
            .values(session_id=session_id, role=role, content=content)
            .returning(ChatMessage)
        )
        res = await self.db.execute(stmt)
        await self.db.flush()
        msg = res.scalar_one()
        logger.info(f"✅ BACKEND: New message created - role: {role}, content: {content[:50]}...")
        return msg.__dict__

    async def list_messages(self, session_id: UUID) -> List[Dict[str, Any]]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )
        res = await self.db.execute(stmt)
        msgs = res.scalars().all()
        return [m.__dict__ for m in msgs]

    async def delete_session(self, session_id: UUID) -> bool:
        """Eliminar una sesión de chat y todos sus mensajes (cascada)"""
        stmt = delete(ChatSession).where(ChatSession.session_id == session_id)
        res = await self.db.execute(stmt)
        await self.db.flush()
        return res.rowcount > 0

    async def update_session(self, session_id: UUID, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Actualizar datos de una sesión de chat"""
        stmt = (
            update(ChatSession)
            .where(ChatSession.session_id == session_id)
            .values(**update_data)
            .returning(ChatSession)
        )
        res = await self.db.execute(stmt)
        await self.db.flush()
        updated_session = res.scalar_one_or_none()
        return updated_session.__dict__ if updated_session else None

    # Methods needed for ChatTitleService
    async def get_session_by_id(self, session_id: UUID) -> Dict[str, Any]:
        """Alias for get_session to match ChatTitleService expectations"""
        return await self.get_session(session_id)

    async def count_messages_for_session(self, session_id: UUID) -> int:
        """Count total messages for a session"""
        from sqlalchemy import func
        stmt = (
            select(func.count(ChatMessage.message_id))
            .where(ChatMessage.session_id == session_id)
        )
        res = await self.db.execute(stmt)
        return res.scalar() or 0

    async def update_session_title(self, session_id: UUID, title: str) -> bool:
        """Update only the title of a session"""
        stmt = (
            update(ChatSession)
            .where(ChatSession.session_id == session_id)
            .values(title=title)
        )
        res = await self.db.execute(stmt)
        await self.db.flush()
        return res.rowcount > 0

    async def get_messages_for_session(self, session_id: UUID, limit: int = None) -> List[Dict[str, Any]]:
        """Get messages for a session with optional limit"""
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )
        if limit:
            stmt = stmt.limit(limit)
        
        res = await self.db.execute(stmt)
        msgs = res.scalars().all()
        return [m.__dict__ for m in msgs]


async def get_chat_session_repository(
    db: AsyncSession = Depends(get_db),
) -> ChatSessionRepository:
    return ChatSessionRepository(db)
