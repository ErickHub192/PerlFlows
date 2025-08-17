from typing import Optional
from uuid import UUID

from sqlalchemy import select, insert, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.db.models import TelegramCredential
from app.db.database import get_db

class TelegramCredentialRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert(self, agent_id: UUID, bot_token: str) -> None:
        stmt = select(TelegramCredential).where(TelegramCredential.agent_id == agent_id)
        res = await self.db.execute(stmt)
        cred = res.scalar_one_or_none()
        if cred:
            await self.db.execute(
                update(TelegramCredential).where(TelegramCredential.agent_id == agent_id).values(bot_token=bot_token)
            )
        else:
            await self.db.execute(
                insert(TelegramCredential).values(agent_id=agent_id, bot_token=bot_token)
            )
        await self.db.flush()

    async def get(self, agent_id: UUID) -> Optional[TelegramCredential]:
        res = await self.db.execute(
            select(TelegramCredential).where(TelegramCredential.agent_id == agent_id)
        )
        return res.scalar_one_or_none()

def get_telegram_repo(db: AsyncSession = Depends(get_db)) -> TelegramCredentialRepository:
    return TelegramCredentialRepository(db)
