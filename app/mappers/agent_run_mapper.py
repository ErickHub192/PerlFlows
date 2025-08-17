# app/mappers/agent_run_mapper.py

from typing import List, Dict, Any
from app.db.models import AgentRun
from app.dtos.agent_run_dto import (
    AgentRunDTO, 
    AgentRunStatisticsDTO, 
    DailyRunStatsDTO,
    AgentRunsListResponseDTO,
    AgentRunAnalyticsDTO
)


def to_agent_run_dto(agent_run: AgentRun) -> AgentRunDTO:
    """Convert AgentRun model to DTO"""
    return AgentRunDTO(
        run_id=agent_run.run_id,
        agent_id=agent_run.agent_id,
        goal=agent_run.goal,
        status=agent_run.status,
        result=agent_run.result,
        error=agent_run.error,
        created_at=agent_run.created_at,
        updated_at=agent_run.updated_at
    )


def to_agent_runs_list(
    runs: List[AgentRun], 
    total_count: int, 
    page: int, 
    page_size: int
) -> AgentRunsListResponseDTO:
    """Convert list of AgentRun models to paginated response DTO"""
    return AgentRunsListResponseDTO(
        runs=[to_agent_run_dto(run) for run in runs],
        total_count=total_count,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total_count,
        has_prev=page > 1
    )


def to_agent_run_statistics_dto(stats_dict: Dict[str, Any]) -> AgentRunStatisticsDTO:
    """Convert statistics dictionary to DTO"""
    return AgentRunStatisticsDTO(**stats_dict)


def to_daily_run_stats_dto_list(daily_stats: List[Dict[str, Any]]) -> List[DailyRunStatsDTO]:
    """Convert list of daily statistics dictionaries to DTOs"""
    return [DailyRunStatsDTO(**stat) for stat in daily_stats]


def to_agent_run_analytics_dto(
    agent_id,
    statistics: Dict[str, Any],
    recent_runs: List[AgentRun],
    daily_stats: List[Dict[str, Any]],
    period_start: str,
    period_end: str
) -> AgentRunAnalyticsDTO:
    """Convert analytics data to comprehensive DTO"""
    return AgentRunAnalyticsDTO(
        agent_id=agent_id,
        statistics=to_agent_run_statistics_dto(statistics),
        recent_runs=[to_agent_run_dto(run) for run in recent_runs],
        daily_stats=to_daily_run_stats_dto_list(daily_stats),
        period_start=period_start,
        period_end=period_end
    )