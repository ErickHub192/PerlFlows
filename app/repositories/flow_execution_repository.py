# app/repositories/flow_execution_repository.py

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.models import FlowExecutionStep
from app.db.models import FlowExecution


class FlowExecutionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_execution(self, execution_id: UUID) -> Optional[FlowExecution]:
        stmt = select(FlowExecution).where(
            FlowExecution.execution_id == execution_id
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def save_execution(self, flow_exec: FlowExecution) -> FlowExecution:
        # aseguramos estado inicial y timestamp
        flow_exec.status     = "running"
        flow_exec.started_at = datetime.now(timezone.utc)
        self.db.add(flow_exec)
        # ✅ Repository no maneja transacciones - solo flush
        await self.db.flush()
        await self.db.refresh(flow_exec)
        return flow_exec

    async def update_execution(
        self,
        execution_id: UUID,
        status: str,
        outputs: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        stmt = (
            update(FlowExecution)
            .where(FlowExecution.execution_id == execution_id)
            .values(
                status=status,
                outputs=outputs,
                error=error,
                ended_at=datetime.now(timezone.utc)
            )
        )
        await self.db.execute(stmt)
        # ✅ Repository no maneja transacciones - solo flush
        await self.db.flush()

    async def list_executions(self, flow_id: UUID) -> List[FlowExecution]:
        stmt = (
            select(FlowExecution)
            .where(FlowExecution.flow_id == flow_id)
            .order_by(FlowExecution.started_at.desc())
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()
    
    async def list_steps(self, execution_id: UUID) -> List[FlowExecutionStep]:
        stmt = (
            select(FlowExecutionStep)
            .where(FlowExecutionStep.execution_id == execution_id)
            .order_by(FlowExecutionStep.started_at)
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def save_step(self, step: FlowExecutionStep) -> FlowExecutionStep:
        self.db.add(step)
        # ✅ Repository no maneja transacciones - solo flush
        await self.db.flush()
        await self.db.refresh(step)
        return step
