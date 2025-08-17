# app/services/agent_run_service.py

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.iagent_run_repository import IAgentRunRepository
from app.services.IAgentRunService import IAgentRunService
from app.db.models import AgentRun, AgentStatus
from app.dtos.agent_run_dto import (
    AgentRunDTO,
    AgentRunsListResponseDTO,
    AgentRunStatisticsDTO,
    AgentRunAnalyticsDTO,
    CreateAgentRunDTO,
    UpdateAgentRunDTO
)
from app.mappers.agent_run_mapper import (
    to_agent_run_dto,
    to_agent_runs_list,
    to_agent_run_statistics_dto,
    to_agent_run_analytics_dto
)
from app.exceptions.api_exceptions import InvalidDataException


class AgentRunService(IAgentRunService):
    """
    Service layer for Agent Run operations
    Handles business logic for agent execution history and analytics
    """

    def __init__(self, agent_run_repo: IAgentRunRepository):
        self.agent_run_repo = agent_run_repo
        self.logger = logging.getLogger(__name__)

    async def get_run(self, run_id: UUID) -> Optional[AgentRunDTO]:
        """Get specific agent run by ID"""
        run = await self.agent_run_repo.get_run(run_id)
        return to_agent_run_dto(run) if run else None

    async def get_session_execution_stats(self, session_id: str, user_id: int) -> Dict[str, Any]:
        """
        ✅ CORREGIDO: Get execution statistics usando repositorio inyectado
        Returns None if session has no agents (classic workflow mode).
        """
        try:
            # ✅ CORREGIDO: Delegar completamente al repositorio
            stats = await self.agent_run_repo.get_session_execution_stats(session_id, user_id)
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting session execution stats: {e}")
            return None

    async def list_agent_runs(
        self,
        agent_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: Optional[AgentStatus] = None
    ) -> AgentRunsListResponseDTO:
        """List runs for an agent with pagination"""
        if page < 1:
            raise InvalidDataException("Page must be >= 1")
        if page_size < 1 or page_size > 100:
            raise InvalidDataException("Page size must be between 1 and 100")

        offset = (page - 1) * page_size
        
        # Get runs and total count concurrently
        runs = await self.agent_run_repo.list_runs_by_agent(
            agent_id=agent_id,
            limit=page_size,
            offset=offset,
            status=status
        )
        
        total_count = await self.agent_run_repo.get_runs_count_by_agent(agent_id)
        
        return to_agent_runs_list(runs, total_count, page, page_size)

    async def get_agent_statistics(self, agent_id: UUID) -> AgentRunStatisticsDTO:
        """Get statistics for an agent"""
        stats = await self.agent_run_repo.get_run_statistics(agent_id)
        return to_agent_run_statistics_dto(stats)

    async def get_agent_analytics(
        self,
        agent_id: UUID,
        days: int = 30,
        recent_runs_limit: int = 10
    ) -> AgentRunAnalyticsDTO:
        """Get comprehensive analytics for an agent"""
        if days < 1 or days > 365:
            raise InvalidDataException("Days must be between 1 and 365")

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Get all analytics data concurrently
        statistics = await self.agent_run_repo.get_run_statistics(agent_id)
        recent_runs = await self.agent_run_repo.get_recent_runs(
            agent_id=agent_id,
            days=days,
            limit=recent_runs_limit
        )
        daily_stats = await self.agent_run_repo.get_daily_run_stats(
            agent_id=agent_id,
            start_date=start_date,
            end_date=end_date
        )

        return to_agent_run_analytics_dto(
            agent_id=agent_id,
            statistics=statistics,
            recent_runs=recent_runs,
            daily_stats=daily_stats,
            period_start=start_date.isoformat(),
            period_end=end_date.isoformat()
        )

    async def create_run(self, create_dto: CreateAgentRunDTO) -> AgentRunDTO:
        """
        ✅ CORREGIDO: Create a new agent run usando repository apropiadamente
        """
        # ✅ CORREGIDO: Delegar completamente al repositorio - no instanciar modelos aquí
        created_run = await self.agent_run_repo.create_run_from_dto(create_dto)
        return to_agent_run_dto(created_run)

    async def update_run_status(
        self,
        run_id: UUID,
        update_dto: UpdateAgentRunDTO
    ) -> Optional[AgentRunDTO]:
        """Update agent run status and result"""
        updated_run = await self.agent_run_repo.update_run_status(
            run_id=run_id,
            status=update_dto.status,
            result=update_dto.result,
            error=update_dto.error
        )
        
        return to_agent_run_dto(updated_run) if updated_run else None

    async def get_recent_activity(
        self,
        agent_id: UUID,
        days: int = 7,
        limit: int = 10
    ) -> List[AgentRunDTO]:
        """Get recent activity for an agent"""
        runs = await self.agent_run_repo.get_recent_runs(
            agent_id=agent_id,
            days=days,
            limit=limit
        )
        
        return [to_agent_run_dto(run) for run in runs]

    async def get_success_trend(
        self,
        agent_id: UUID,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get success rate trend over time"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        daily_stats = await self.agent_run_repo.get_daily_run_stats(
            agent_id=agent_id,
            start_date=start_date,
            end_date=end_date
        )

        return daily_stats


def get_agent_run_service(
    db: AsyncSession = Depends(get_db)
) -> AgentRunService:
    """
    Factory para inyección de dependencias
    """
    agent_run_repo = AgentRunRepository(db)
    return AgentRunService(agent_run_repo)