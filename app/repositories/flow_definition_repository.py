from typing import Dict, Any
from uuid import UUID
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Depends, HTTPException

from app.db.database import get_db
from app.db.models import Flow

class FlowDefinitionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_spec(self, flow_id: UUID) -> Dict[str, Any]:
        q = select(Flow).where(Flow.flow_id == flow_id)
        res = await self.db.execute(q)
        flow = res.scalar_one_or_none()
        if not flow:
            raise HTTPException(status_code=404, detail="Flujo no encontrado")
        return flow.spec

    async def delete_by_flow_id(self, flow_id: UUID) -> None:
        """Elimina definiciones relacionadas con un flow_id"""
        # En este caso, las definiciones están en la misma tabla Flow
        # Este método existe para compatibilidad con el cleanup script
        pass

async def get_flow_definition_repository(
    db: AsyncSession = Depends(get_db),
) -> FlowDefinitionRepository:
    return FlowDefinitionRepository(db)
