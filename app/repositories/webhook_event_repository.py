from typing import Any, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends

from app.db.database import get_db
from app.db.models import WebhookEvent


class WebhookEventRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_event(
        self,
        flow_id: UUID,
        path: str,
        method: str,
        payload: Any,
        headers: Any,
    ) -> WebhookEvent:
        event = WebhookEvent(
            flow_id=flow_id,
            path=path,
            method=method,
            payload=payload,
            headers=headers,
        )
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def list_events(self, flow_id: UUID) -> List[WebhookEvent]:
        stmt = select(WebhookEvent).where(WebhookEvent.flow_id == flow_id)
        res = await self.db.execute(stmt)
        return res.scalars().all()


def get_webhook_event_repository(db: AsyncSession = Depends(get_db)) -> WebhookEventRepository:
    return WebhookEventRepository(db)
