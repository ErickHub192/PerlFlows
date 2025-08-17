from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from fastapi import Depends
from uuid import UUID, uuid4
from typing import List
from app.db.models import Trigger
from app.db.database import get_db

class TriggerRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_trigger(
        self,
        flow_id: UUID,
        node_id: UUID,
        action_id: UUID,
        trigger_type: str,
        trigger_args: dict,
        job_id: str,
    ) -> Trigger:
        trigger = Trigger(
            trigger_id=uuid4(),
            flow_id=flow_id,
            node_id=node_id,
            action_id=action_id,
            trigger_type=trigger_type,
            trigger_args=trigger_args,
            job_id=job_id,
            status="active",
        )
        self.db.add(trigger)
        await self.db.flush()
        await self.db.refresh(trigger)
        return trigger

    async def get_active_triggers(
        self,
        flow_id: UUID
    ) -> List[Trigger]:
        q = select(Trigger).where(
            Trigger.flow_id == flow_id,
            Trigger.status == "active"
        )
        res = await self.db.execute(q)
        return res.scalars().all()

    async def delete_trigger(
        self,
        trigger_id: UUID
    ) -> None:
        q = delete(Trigger).where(Trigger.trigger_id == trigger_id)
        await self.db.execute(q)
        await self.db.flush()

    async def list_by_owner(
        self,
        owner_id: int
    ) -> List[Trigger]:
        """Lista todos los triggers de un owner/usuario"""
        # Asumiendo que el owner_id se relaciona con flow_id o user_id
        # Necesitamos revisar el esquema de la tabla Trigger
        q = select(Trigger).where(Trigger.status == "active")
        # TODO: Agregar filtro por owner cuando esté definido en el modelo
        res = await self.db.execute(q)
        return res.scalars().all()


async def get_trigger_repository(
    db: AsyncSession = Depends(get_db),
) -> TriggerRepository:
    return TriggerRepository(db)
