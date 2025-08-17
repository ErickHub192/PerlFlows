# app/dtos/agent_run_dto.py

from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.db.models import AgentStatus


class AgentRunDTO(BaseModel):
    """DTO for agent run information"""
    run_id: UUID
    agent_id: UUID
    goal: Optional[str] = None
    status: AgentStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AgentRunStatisticsDTO(BaseModel):
    """DTO for agent run statistics"""
    total_runs: int
    successful_runs: int
    failed_runs: int
    running_runs: int
    queued_runs: int
    success_rate: float  # percentage
    average_duration_minutes: float
    last_run_date: Optional[str] = None  # ISO format


class DailyRunStatsDTO(BaseModel):
    """DTO for daily run statistics"""
    date: str  # ISO date format
    total_runs: int
    successful_runs: int
    failed_runs: int
    success_rate: float
    average_duration_minutes: float


class AgentRunsListResponseDTO(BaseModel):
    """DTO for paginated agent runs list"""
    runs: List[AgentRunDTO]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


class AgentRunAnalyticsDTO(BaseModel):
    """DTO for comprehensive agent run analytics"""
    agent_id: UUID
    statistics: AgentRunStatisticsDTO
    recent_runs: List[AgentRunDTO]
    daily_stats: List[DailyRunStatsDTO]
    period_start: str  # ISO datetime
    period_end: str    # ISO datetime


class CreateAgentRunDTO(BaseModel):
    """DTO for creating a new agent run"""
    agent_id: UUID
    goal: Optional[str] = None
    
    
class UpdateAgentRunDTO(BaseModel):
    """DTO for updating agent run status"""
    status: AgentStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None