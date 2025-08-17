# app/services/IAgentRunService.py

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID
from app.db.models import AgentStatus
from app.dtos.agent_run_dto import (
    AgentRunDTO,
    AgentRunsListResponseDTO,
    AgentRunStatisticsDTO,
    AgentRunAnalyticsDTO,
    CreateAgentRunDTO,
    UpdateAgentRunDTO
)

class IAgentRunService(ABC):
    """Interface for Agent Run Service"""
    
    @abstractmethod
    async def get_run(self, run_id: UUID) -> Optional[AgentRunDTO]:
        """Get specific agent run by ID"""
        pass
    
    @abstractmethod
    async def get_session_execution_stats(self, session_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        """Get execution statistics for a chat session"""
        pass
    
    @abstractmethod
    async def list_agent_runs(
        self,
        agent_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: Optional[AgentStatus] = None
    ) -> AgentRunsListResponseDTO:
        """List runs for an agent with pagination"""
        pass
    
    @abstractmethod
    async def get_agent_statistics(self, agent_id: UUID) -> AgentRunStatisticsDTO:
        """Get statistics for an agent"""
        pass
    
    @abstractmethod
    async def get_agent_analytics(
        self,
        agent_id: UUID,
        days: int = 30,
        recent_runs_limit: int = 10
    ) -> AgentRunAnalyticsDTO:
        """Get comprehensive analytics for an agent"""
        pass
    
    @abstractmethod
    async def create_run(self, create_dto: CreateAgentRunDTO) -> AgentRunDTO:
        """Create a new agent run"""
        pass
    
    @abstractmethod
    async def update_run_status(
        self,
        run_id: UUID,
        update_dto: UpdateAgentRunDTO
    ) -> Optional[AgentRunDTO]:
        """Update agent run status and result"""
        pass
    
    @abstractmethod
    async def get_recent_activity(
        self,
        agent_id: UUID,
        days: int = 7,
        limit: int = 10
    ) -> List[AgentRunDTO]:
        """Get recent activity for an agent"""
        pass
    
    @abstractmethod
    async def get_success_trend(
        self,
        agent_id: UUID,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get success rate trend over time"""
        pass