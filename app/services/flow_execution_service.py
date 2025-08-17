# app/services/flow_execution_service.py

import logging
from uuid import UUID
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import FlowExecution, FlowExecutionStep
from app.repositories.flow_execution_repository import FlowExecutionRepository
# Interface removed - using concrete class

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

VALID_STATUSES = {"running", "success", "failure", "cancelled", "paused"}

class FlowExecutionService:
    def __init__(self, repo: FlowExecutionRepository):
        self.repo = repo

    async def start_execution(self, flow_id: UUID, inputs: Dict[str, Any]) -> FlowExecution:
        """
        ✅ CORREGIDO: Start execution usando repository apropiadamente
        """
        from uuid import uuid4
        # ✅ CORREGIDO: Crear FlowExecution object y usar save_execution
        flow_exec = FlowExecution(
            execution_id=uuid4(),
            flow_id=None,  # 🔧 NULL for temporary workflows, not in flows table
            flow_spec={},  # 🔧 REQUIRED: flow_spec is NOT NULL in DB
            inputs=inputs,
            status="running",
            started_at=datetime.now(timezone.utc)
        )
        return await self.repo.save_execution(flow_exec)

    async def finish_execution(
        self,
        execution_id: UUID,
        status: str,
        outputs: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        if status not in VALID_STATUSES - {"running", "paused"}:
            raise ValueError(f"Invalid status: {status}")
        await self.repo.update_execution(
            execution_id=execution_id,
            status=status,
            outputs=outputs,
            error=error,
        )

    async def cancel_execution(self, execution_id: UUID) -> None:
        await self.repo.update_execution(
            execution_id=execution_id,
            status="cancelled",
        )

    async def pause_execution(self, execution_id: UUID) -> None:
        await self.repo.update_execution(
            execution_id=execution_id,
            status="paused",
        )

    async def resume_execution(self, execution_id: UUID) -> None:
        await self.repo.update_execution(
            execution_id=execution_id,
            status="running",
        )

    async def get_execution(self, execution_id: UUID) -> Optional[FlowExecution]:
        return await self.repo.get_execution(execution_id)

    async def list_executions(self, flow_id: UUID) -> List[FlowExecution]:
        return await self.repo.list_executions(flow_id)

    async def record_step(
        self,
        execution_id: UUID,
        node_id: UUID,
        action_id: UUID,
        status: str,
        error: Optional[str] = None,
        started_at: Optional[datetime] = None,
        ended_at: Optional[datetime] = None,
    ) -> FlowExecutionStep:
        """
        ✅ CORREGIDO: Add step usando repository apropiadamente
        """
        # ✅ CORREGIDO: Delegar creación del modelo al repositorio
        return await self.repo.create_step(
            execution_id=execution_id,
            node_id=node_id,
            action_id=action_id,
            status=status,
            error=error,
            started_at=started_at,
            ended_at=ended_at
        )

    async def list_steps(self, execution_id: UUID) -> List[FlowExecutionStep]:
        return await self.repo.list_steps(execution_id)

def get_flow_execution_service(
    db: AsyncSession = Depends(get_db),
) -> FlowExecutionService:
    """
    Factory para inyección de dependencias
    """
    repo = FlowExecutionRepository(db)
    return FlowExecutionService(repo)
