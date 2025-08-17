# app/services/IChatTitleService.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from uuid import UUID

from app.dtos.chat_title_dto import (
    TitleGenerationResponseDTO,
    TitleReadinessResponseDTO,
    ChatMessageContextDTO,
    TitleGenerationRequestDTO,
    TitleReadinessCheckDTO
)


class IChatTitleService(ABC):
    """
    Interface for chat title generation service.
    Handles automatic title generation based on conversation content using Kyra LLM.
    """

    @abstractmethod
    async def generate_title_for_session(self, session_id: str) -> Optional[str]:
        """
        Generate an intelligent title for a chat session based on initial messages.
        
        Args:
            session_id: UUID of the chat session
            
        Returns:
            Generated title string (max 40 chars) or None if generation fails
        """
        pass

    @abstractmethod
    async def generate_title_for_user_session(self, request: TitleGenerationRequestDTO) -> TitleGenerationResponseDTO:
        """
        Generate title for a session with user validation and full response.
        
        Args:
            request: TitleGenerationRequestDTO with session_id and user_id
            
        Returns:
            TitleGenerationResponseDTO with success status, title, and metadata
        """
        pass

    @abstractmethod
    async def check_title_readiness(self, request: TitleReadinessCheckDTO) -> TitleReadinessResponseDTO:
        """
        Check if session is ready for title generation with user validation.
        
        Args:
            request: TitleReadinessCheckDTO with session_id and user_id
            
        Returns:
            TitleReadinessResponseDTO with readiness status and metadata
        """
        pass

    @abstractmethod
    async def should_generate_title(self, session_id: str) -> bool:
        """
        Determine if a chat session is ready for title generation.
        
        Args:
            session_id: UUID of the chat session
            
        Returns:
            True if title should be generated, False otherwise
        """
        pass

    @abstractmethod
    async def update_session_title(self, session_id: str, title: str) -> bool:
        """
        Update the title of a chat session in the database.
        
        Args:
            session_id: UUID of the chat session
            title: New title to set
            
        Returns:
            True if update was successful, False otherwise
        """
        pass

    @abstractmethod
    async def get_conversation_context(self, session_id: str, limit: int = 3) -> List[ChatMessageContextDTO]:
        """
        Get the initial messages from a chat session for context analysis.
        
        Args:
            session_id: UUID of the chat session
            limit: Number of initial messages to retrieve (default: 3)
            
        Returns:
            List of ChatMessageContextDTO objects with role, content and timestamp
        """
        pass


class ChatTitleGenerationError(Exception):
    """Custom exception for chat title generation errors."""
    pass


class InsufficientContentError(ChatTitleGenerationError):
    """Raised when there's not enough content to generate a meaningful title."""
    pass


class LLMGenerationError(ChatTitleGenerationError):
    """Raised when the LLM fails to generate a title."""
    pass