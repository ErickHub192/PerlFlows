from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy import select, func, and_, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentRun, AgentStatus

class AgentRunRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_run(self, run: AgentRun) -> AgentRun:
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def get_run(self, run_id: UUID) -> Optional[AgentRun]:
        stmt = select(AgentRun).where(AgentRun.run_id == run_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_runs_by_agent(
        self, 
        agent_id: UUID, 
        limit: int = 50,
        offset: int = 0,
        status: Optional[AgentStatus] = None
    ) -> List[AgentRun]:
        """List runs for a specific agent with pagination and optional status filter."""
        stmt = select(AgentRun).where(AgentRun.agent_id == agent_id)
        
        if status:
            stmt = stmt.where(AgentRun.status == status)
        
        stmt = stmt.order_by(desc(AgentRun.created_at)).limit(limit).offset(offset)
        
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_runs_count_by_agent(self, agent_id: UUID) -> int:
        """Get total count of runs for an agent."""
        stmt = select(func.count(AgentRun.run_id)).where(AgentRun.agent_id == agent_id)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_run_statistics(self, agent_id: UUID) -> Dict[str, Any]:
        """Get success rate and other statistics for an agent."""
        # Total runs
        total_stmt = select(func.count(AgentRun.run_id)).where(AgentRun.agent_id == agent_id)
        total_result = await self.session.execute(total_stmt)
        total_runs = total_result.scalar() or 0
        
        if total_runs == 0:
            return {
                "total_runs": 0,
                "successful_runs": 0,
                "failed_runs": 0,
                "running_runs": 0,
                "queued_runs": 0,
                "success_rate": 0.0,
                "average_duration_minutes": 0.0,
                "last_run_date": None
            }
        
        # Count by status
        status_stmt = select(
            AgentRun.status,
            func.count(AgentRun.run_id).label('count')
        ).where(AgentRun.agent_id == agent_id).group_by(AgentRun.status)
        
        status_result = await self.session.execute(status_stmt)
        status_counts = {row.status: row.count for row in status_result}
        
        successful_runs = status_counts.get(AgentStatus.SUCCEEDED, 0)
        failed_runs = status_counts.get(AgentStatus.FAILED, 0)
        running_runs = status_counts.get(AgentStatus.RUNNING, 0)
        queued_runs = status_counts.get(AgentStatus.QUEUED, 0)
        
        success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0.0
        
        # Average duration (for completed runs)
        duration_stmt = select(
            func.avg(
                func.extract('epoch', AgentRun.updated_at - AgentRun.created_at) / 60
            ).label('avg_duration_minutes')
        ).where(
            and_(
                AgentRun.agent_id == agent_id,
                AgentRun.status.in_([AgentStatus.SUCCEEDED, AgentStatus.FAILED]),
                AgentRun.updated_at.is_not(None)
            )
        )
        
        duration_result = await self.session.execute(duration_stmt)
        avg_duration = duration_result.scalar() or 0.0
        
        # Last run date
        last_run_stmt = select(func.max(AgentRun.created_at)).where(AgentRun.agent_id == agent_id)
        last_run_result = await self.session.execute(last_run_stmt)
        last_run_date = last_run_result.scalar()
        
        return {
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "running_runs": running_runs,
            "queued_runs": queued_runs,
            "success_rate": round(success_rate, 2),
            "average_duration_minutes": round(avg_duration, 2),
            "last_run_date": last_run_date.isoformat() if last_run_date else None
        }

    async def get_recent_runs(
        self, 
        agent_id: UUID, 
        days: int = 7,
        limit: int = 10
    ) -> List[AgentRun]:
        """Get recent runs for an agent within specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        stmt = select(AgentRun).where(
            and_(
                AgentRun.agent_id == agent_id,
                AgentRun.created_at >= cutoff_date
            )
        ).order_by(desc(AgentRun.created_at)).limit(limit)
        
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_run_status(
        self, 
        run_id: UUID, 
        status: AgentStatus, 
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> Optional[AgentRun]:
        """Update run status and optionally result/error."""
        run = await self.get_run(run_id)
        if not run:
            return None
        
        run.status = status
        run.updated_at = datetime.utcnow()
        
        if result is not None:
            run.result = result
        
        if error is not None:
            run.error = error
        
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def get_daily_run_stats(
        self, 
        agent_id: UUID, 
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get daily run statistics for time range analysis."""
        # Using PostgreSQL date_trunc function for daily grouping
        stmt = text("""
            SELECT 
                DATE_TRUNC('day', created_at) as run_date,
                COUNT(*) as total_runs,
                COUNT(CASE WHEN status = 'succeeded' THEN 1 END) as successful_runs,
                COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_runs,
                AVG(CASE 
                    WHEN status IN ('succeeded', 'failed') AND updated_at IS NOT NULL 
                    THEN EXTRACT(EPOCH FROM (updated_at - created_at)) / 60 
                    ELSE NULL 
                END) as avg_duration_minutes
            FROM agent_runs 
            WHERE agent_id = :agent_id 
                AND created_at >= :start_date 
                AND created_at <= :end_date
            GROUP BY DATE_TRUNC('day', created_at)
            ORDER BY run_date
        """)
        
        result = await self.session.execute(
            stmt, 
            {
                "agent_id": str(agent_id), 
                "start_date": start_date, 
                "end_date": end_date
            }
        )
        
        stats = []
        for row in result:
            stats.append({
                "date": row.run_date.date().isoformat(),
                "total_runs": row.total_runs,
                "successful_runs": row.successful_runs,
                "failed_runs": row.failed_runs,
                "success_rate": round((row.successful_runs / row.total_runs * 100), 2) if row.total_runs > 0 else 0.0,
                "average_duration_minutes": round(row.avg_duration_minutes, 2) if row.avg_duration_minutes else 0.0
            })
        
        return stats


# Factory function for dependency injection
def get_agent_run_repository(session: AsyncSession) -> AgentRunRepository:
    """Factory function to create AgentRunRepository instance"""
    return AgentRunRepository(session)
