# app/services/chat_title_service.py

import json
import logging
import time
from typing import Dict, Any, Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

# Interface removed - using concrete class
# Define exceptions locally
class ChatTitleGenerationError(Exception):
    pass

class InsufficientContentError(ChatTitleGenerationError):
    pass

class LLMGenerationError(ChatTitleGenerationError):
    pass
from app.dtos.chat_title_dto import (
    TitleGenerationRequestDTO,
    TitleGenerationResponseDTO,
    TitleReadinessCheckDTO,
    TitleReadinessResponseDTO,
    ChatMessageContextDTO
)
from app.mappers.chat_title_mapper import ChatTitleMapper
from app.db.database import get_db
from app.repositories.chat_session_repository import ChatSessionRepository, get_chat_session_repository
# LLM service imported dynamically when needed to avoid circular imports
from app.exceptions.llm_exceptions import LLMConnectionException, JSONParsingException


class ChatTitleService:
    """
    ✅ CORREGIDO: Service con dependency injection apropiada
    
    Service for automatic chat title generation using Kyra LLM.
    Analyzes initial conversation messages to generate meaningful, 
    concise titles that reflect the chat's main topic or purpose.
    """

    def __init__(
        self,
        chat_session_repository: ChatSessionRepository
    ):
        self.chat_session_repo = chat_session_repository
        self.logger = logging.getLogger(__name__)
        self.max_title_length = 40
        self.min_messages_for_title = 2
        self.max_context_messages = 3

    async def generate_title_for_session(self, session_id: str) -> Optional[str]:
        """
        ✅ CORREGIDO: Generate an intelligent title for a chat session usando repositorios inyectados
        
        Process:
        1. Check if session is ready for title generation
        2. Get conversation context from first messages
        3. Use Kyra LLM to generate contextual title
        4. Update session with generated title
        5. Return generated title
        """
        try:
            self.logger.info(f"Starting title generation for session {session_id}")
            
            # 1. Check if ready for title generation
            if not await self._is_ready_for_title_generation(session_id):
                self.logger.debug(f"Session {session_id} not ready for title generation")
                return None
            
            # 2. Get conversation context
            context_messages = await self._get_conversation_context(session_id)
            if not context_messages:
                self.logger.warning(f"No context messages found for session {session_id}")
                return None
            
            # 3. Generate title using LLM
            generated_title = await self._generate_title_with_llm(context_messages)
            if not generated_title:
                self.logger.warning(f"Failed to generate title for session {session_id}")
                return None
            
            # 4. Update session with generated title  
            success = await self.update_session_title(session_id, generated_title)
            if not success:
                self.logger.error(f"Failed to update title for session {session_id}")
                return None
            
            self.logger.info(f"Successfully generated title for session {session_id}: {generated_title}")
            return generated_title
            
        except Exception as e:
            self.logger.error(f"Error generating title for session {session_id}: {e}", exc_info=True)
            return None

    async def _is_ready_for_title_generation(self, session_id: str) -> bool:
        """
        ✅ CORREGIDO: Check if session has enough content usando repositorio inyectado
        """
        try:
            # Get session info via repository
            session = await self.chat_session_repo.get_session_by_id(session_id)
            if not session:
                return False

            # Handle both dict and object formats
            if isinstance(session, dict):
                session_title = session.get('title', '')
            else:
                session_title = getattr(session, 'title', '')

            # Don't regenerate if already has custom title (not default)
            if session_title and not session_title.startswith("Chat ") and session_title != "Nuevo chat":
                return False

            # Check message count via repository
            message_count = await self.chat_session_repo.count_messages_for_session(session_id)
            return message_count >= self.min_messages_for_title

        except Exception as e:
            self.logger.error(f"Error checking title generation readiness: {e}")
            return False

    async def update_session_title(self, session_id: str, title: str) -> bool:
        """
        ✅ CORREGIDO: Update chat session title usando repositorio inyectado
        """
        try:
            success = await self.chat_session_repo.update_session_title(session_id, title)
            if success:
                self.logger.info(f"Updated title for session {session_id}: {title}")
            return success

        except Exception as e:
            self.logger.error(f"Error updating session title: {e}")
            return False

    async def _get_conversation_context(self, session_id: str) -> List[ChatMessageContextDTO]:
        """
        ✅ CORREGIDO: Get conversation context usando repositorio inyectado
        """
        try:
            # Get first few messages from session
            messages = await self.chat_session_repo.get_messages_for_session(
                session_id, limit=self.max_context_messages
            )
            
            context_messages = []
            for msg in messages:
                # 🔧 FIX: Handle both dict and object types safely
                if isinstance(msg, dict):
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')
                    timestamp = msg.get('created_at', None)
                else:
                    role = getattr(msg, 'role', 'unknown')
                    content = getattr(msg, 'content', '')
                    timestamp = getattr(msg, 'created_at', None)
                
                context_dto = ChatMessageContextDTO(
                    role=role,
                    content=content,
                    timestamp=timestamp
                )
                context_messages.append(context_dto)
            
            return context_messages

        except Exception as e:
            self.logger.error(f"Error getting conversation context: {e}")
            return []

    async def _generate_title_with_llm(self, context_messages: List[ChatMessageContextDTO]) -> Optional[str]:
        """
        ✅ TEMP FIX: Temporarily disable title generation to prevent ROLLBACK issues
        Returns a simple default title to avoid any LLM call errors that cause transaction rollbacks
        """
        try:
            self.logger.info("🔧 TEMP FIX: Using default title to prevent ROLLBACK issues")
            
            # Generate a simple title based on first user message if available
            for msg in context_messages:
                if msg.role == 'user' and msg.content:
                    # Extract first few words for title
                    words = msg.content.strip().split()[:5]
                    title = " ".join(words)
                    if len(title) > self.max_title_length:
                        title = title[:self.max_title_length-3] + "..."
                    return title
            
            # Fallback to generic title
            return "Conversación con Kyra"
            
        except Exception as e:
            self.logger.error(f"Error generating simple title: {e}")
            return "Chat"

    async def check_title_readiness(self, request: TitleReadinessCheckDTO) -> TitleReadinessResponseDTO:
        """
        ✅ CORREGIDO: Check if multiple sessions are ready for title generation
        """
        results = {}
        
        for session_id in request.session_ids:
            is_ready = await self._is_ready_for_title_generation(session_id)
            results[session_id] = is_ready
        
        return TitleReadinessResponseDTO(
            session_readiness=results,
            total_checked=len(request.session_ids),
            ready_count=sum(1 for ready in results.values() if ready)
        )

    async def generate_titles_batch(self, request: TitleGenerationRequestDTO) -> TitleGenerationResponseDTO:
        """
        ✅ CORREGIDO: Generate titles for multiple sessions in batch
        """
        results = {}
        successful_count = 0
        
        for session_id in request.session_ids:
            try:
                title = await self.generate_title_for_session(session_id)
                if title:
                    results[session_id] = {
                        "success": True,
                        "title": title,
                        "error": None
                    }
                    successful_count += 1
                else:
                    results[session_id] = {
                        "success": False,
                        "title": None,
                        "error": "Failed to generate title"
                    }
            except Exception as e:
                results[session_id] = {
                    "success": False,
                    "title": None,
                    "error": str(e)
                }
        
        return TitleGenerationResponseDTO(
            results=results,
            total_processed=len(request.session_ids),
            successful_count=successful_count,
            failed_count=len(request.session_ids) - successful_count
        )


# ✅ CORREGIDO: Factory function con dependency injection apropiada
async def get_chat_title_service(
    chat_session_repo: ChatSessionRepository = Depends(get_chat_session_repository)
) -> ChatTitleService:
    """
    ✅ Factory function con dependency injection apropiada
    """
    return ChatTitleService(chat_session_repo)