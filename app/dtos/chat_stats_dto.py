# app/dtos/chat_stats_dto.py

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class ChatSessionStatsDTO(BaseModel):
    """DTO for individual chat session statistics."""
    session_id: UUID = Field(..., description="Chat session UUID")
    title: str = Field(..., description="Session title")
    status: str = Field(..., description="Current session status (active/recent/paused)")
    type: str = Field(..., description="Session type (Chat+AI/Workflow/Agent)")
    last_activity: str = Field(..., description="Time since last activity (e.g., '2 min', '1h')")
    execution_count: int = Field(default=0, description="Number of executions in this session")
    message_count: int = Field(default=0, description="Total number of messages")
    description: str = Field(..., description="Dynamic description based on status")
    created_at: datetime = Field(..., description="Session creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        from_attributes = True


class UserChatStatsDTO(BaseModel):
    """DTO for aggregated user chat statistics."""
    user_id: int = Field(..., description="User ID")
    total_sessions: int = Field(default=0, description="Total number of chat sessions")
    active_sessions: int = Field(default=0, description="Number of active sessions")
    total_executions: int = Field(default=0, description="Total executions across all sessions")
    total_messages: int = Field(default=0, description="Total messages across all sessions")
    executions_today: int = Field(default=0, description="Executions in the last 24 hours")
    most_active_session: Optional[UUID] = Field(None, description="Session ID with most activity")
    session_stats: List[ChatSessionStatsDTO] = Field(default=[], description="Individual session statistics")

    class Config:
        from_attributes = True


class SessionExecutionStatsDTO(BaseModel):
    """DTO for session execution statistics."""
    session_id: UUID = Field(..., description="Chat session UUID")
    total_executions: int = Field(default=0, description="Total executions for this session")
    successful_executions: int = Field(default=0, description="Number of successful executions")
    failed_executions: int = Field(default=0, description="Number of failed executions")
    last_execution_time: Optional[datetime] = Field(None, description="Timestamp of last execution")
    average_execution_time: Optional[float] = Field(None, description="Average execution time in seconds")
    executions_today: int = Field(default=0, description="Executions in the last 24 hours")
    executions_this_week: int = Field(default=0, description="Executions in the last 7 days")

    class Config:
        from_attributes = True


class StatsRequestDTO(BaseModel):
    """DTO for stats request parameters."""
    user_id: int = Field(..., description="User ID requesting stats")
    session_ids: Optional[List[UUID]] = Field(None, description="Specific sessions to get stats for")
    include_execution_details: bool = Field(default=False, description="Include detailed execution stats")
    time_range_hours: int = Field(default=24, description="Time range for activity calculations")

    class Config:
        from_attributes = True