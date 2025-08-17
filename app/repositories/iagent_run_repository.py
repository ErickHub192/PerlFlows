# app/db/repositories/iagent_run_repository.py

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from app.db.models import AgentRun, AgentStatus

class IAgentRunRepository(ABC):
    """Interface for AgentRun repository."""

    @abstractmethod
    async def create_run(self, run: AgentRun) -> AgentRun:
        """Persist a new AgentRun."""
        ...

    @abstractmethod
    async def get_run(self, run_id: UUID) -> Optional[AgentRun]:
        """Retrieve an AgentRun by its ID."""
        ...

    @abstractmethod
    async def list_runs_by_agent(
        self, 
        agent_id: UUID, 
        limit: int = 50,
        offset: int = 0,
        status: Optional[AgentStatus] = None
    ) -> List[AgentRun]:
        """List runs for a specific agent with pagination and optional status filter."""
        ...

    @abstractmethod
    async def get_runs_count_by_agent(self, agent_id: UUID) -> int:
        """Get total count of runs for an agent."""
        ...

    @abstractmethod
    async def get_run_statistics(self, agent_id: UUID) -> Dict[str, Any]:
        """Get success rate and other statistics for an agent."""
        ...

    @abstractmethod
    async def get_recent_runs(
        self, 
        agent_id: UUID, 
        days: int = 7,
        limit: int = 10
    ) -> List[AgentRun]:
        """Get recent runs for an agent within specified days."""
        ...

    @abstractmethod
    async def update_run_status(
        self, 
        run_id: UUID, 
        status: AgentStatus, 
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> Optional[AgentRun]:
        """Update run status and optionally result/error."""
        ...

    @abstractmethod
    async def get_daily_run_stats(
        self, 
        agent_id: UUID, 
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get daily run statistics for time range analysis."""
        ...
