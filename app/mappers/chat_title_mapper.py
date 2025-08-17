# app/mappers/chat_title_mapper.py

from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID

from app.dtos.chat_title_dto import (
    ChatMessageContextDTO,
    TitleGenerationResponseDTO,
    TitleReadinessResponseDTO,
    ChatTitleUpdateDTO,
    ChatTitleStatsDTO
)
from app.db.models import ChatMessage, ChatSession


class ChatTitleMapper:
    """
    Mapper for converting between database models and DTOs for chat title operations.
    Handles data transformation and validation.
    """

    @staticmethod
    def chat_message_to_context_dto(message: ChatMessage) -> ChatMessageContextDTO:
        """
        Convert ChatMessage model to ChatMessageContextDTO.
        
        Args:
            message: ChatMessage database model
            
        Returns:
            ChatMessageContextDTO with message context for title generation
        """
        return ChatMessageContextDTO(
            role=message.role,
            content=message.content,
            timestamp=message.created_at
        )

    @staticmethod
    def chat_messages_to_context_dtos(messages: List[ChatMessage]) -> List[ChatMessageContextDTO]:
        """
        Convert list of ChatMessage models to ChatMessageContextDTO list.
        
        Args:
            messages: List of ChatMessage database models
            
        Returns:
            List of ChatMessageContextDTO objects
        """
        return [
            ChatTitleMapper.chat_message_to_context_dto(message) 
            for message in messages
        ]

    @staticmethod
    def service_response_to_dto(
        service_response: Dict[str, Any],
        generation_time_ms: Optional[int] = None,
        context_messages_count: Optional[int] = None
    ) -> TitleGenerationResponseDTO:
        """
        Convert service response dictionary to TitleGenerationResponseDTO.
        
        Args:
            service_response: Dictionary from ChatTitleService
            generation_time_ms: Time taken for generation
            context_messages_count: Number of messages used for context
            
        Returns:
            TitleGenerationResponseDTO
        """
        return TitleGenerationResponseDTO(
            success=service_response.get("success", False),
            title=service_response.get("title"),
            message=service_response.get("message", ""),
            error=service_response.get("error"),
            generation_time_ms=generation_time_ms,
            context_messages_count=context_messages_count
        )

    @staticmethod
    def readiness_response_to_dto(
        service_response: Dict[str, Any],
        message_count: Optional[int] = None,
        min_required_messages: Optional[int] = None
    ) -> TitleReadinessResponseDTO:
        """
        Convert service readiness response to TitleReadinessResponseDTO.
        
        Args:
            service_response: Dictionary from ChatTitleService
            message_count: Current number of messages
            min_required_messages: Minimum required messages
            
        Returns:
            TitleReadinessResponseDTO
        """
        return TitleReadinessResponseDTO(
            success=service_response.get("success", False),
            ready=service_response.get("ready"),
            current_title=service_response.get("current_title"),
            message=service_response.get("message", ""),
            error=service_response.get("error"),
            message_count=message_count,
            min_required_messages=min_required_messages
        )

    @staticmethod
    def create_title_update_dto(
        session_id: UUID, 
        title: str, 
        user_id: int
    ) -> ChatTitleUpdateDTO:
        """
        Create ChatTitleUpdateDTO for title updates.
        
        Args:
            session_id: Chat session UUID
            title: New title
            user_id: User performing the update
            
        Returns:
            ChatTitleUpdateDTO
        """
        return ChatTitleUpdateDTO(
            session_id=session_id,
            title=title,
            user_id=user_id
        )

    @staticmethod
    def context_dtos_to_dict(context_dtos: List[ChatMessageContextDTO]) -> List[Dict[str, Any]]:
        """
        Convert ChatMessageContextDTO list to dictionary format for service layer.
        
        Args:
            context_dtos: List of ChatMessageContextDTO objects
            
        Returns:
            List of dictionaries with message context
        """
        return [
            {
                "role": dto.role,
                "content": dto.content,
                "timestamp": dto.timestamp.isoformat()
            }
            for dto in context_dtos
        ]

    @staticmethod
    def create_error_response_dto(
        error_code: str,
        message: str,
        generation_time_ms: Optional[int] = None
    ) -> TitleGenerationResponseDTO:
        """
        Create error response DTO for failed title generation.
        
        Args:
            error_code: Error code identifier
            message: Error message
            generation_time_ms: Time taken before failure
            
        Returns:
            TitleGenerationResponseDTO with error information
        """
        return TitleGenerationResponseDTO(
            success=False,
            title=None,
            message=message,
            error=error_code,
            generation_time_ms=generation_time_ms,
            context_messages_count=None
        )

    @staticmethod
    def create_readiness_error_dto(
        error_code: str,
        message: str
    ) -> TitleReadinessResponseDTO:
        """
        Create error response DTO for failed readiness check.
        
        Args:
            error_code: Error code identifier
            message: Error message
            
        Returns:
            TitleReadinessResponseDTO with error information
        """
        return TitleReadinessResponseDTO(
            success=False,
            ready=None,
            current_title=None,
            message=message,
            error=error_code,
            message_count=None,
            min_required_messages=None
        )

    @staticmethod
    def create_stats_dto(
        total_titles: int,
        successful: int,
        failed: int,
        avg_time: float,
        themes: List[str] = None
    ) -> ChatTitleStatsDTO:
        """
        Create statistics DTO for title generation metrics.
        
        Args:
            total_titles: Total titles generated
            successful: Successful generations
            failed: Failed generations  
            avg_time: Average generation time
            themes: Most common themes
            
        Returns:
            ChatTitleStatsDTO
        """
        return ChatTitleStatsDTO(
            total_titles_generated=total_titles,
            successful_generations=successful,
            failed_generations=failed,
            average_generation_time_ms=avg_time,
            most_common_themes=themes or []
        )