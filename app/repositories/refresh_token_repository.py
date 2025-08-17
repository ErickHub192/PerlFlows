from typing import Optional, Dict, Any
from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.db.models import RefreshToken
from app.db.database import get_db


class RefreshTokenRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_token(self, data: Dict[str, Any]) -> Dict[str, Any]:
        stmt = insert(RefreshToken).values(**data).returning(RefreshToken)
        res = await self.db.execute(stmt)
        await self.db.flush()
        return res.scalar_one().__dict__

    async def get_token(self, token_hash: str) -> Optional[Dict[str, Any]]:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        res = await self.db.execute(stmt)
        token = res.scalar_one_or_none()
        return token.__dict__ if token else None

    async def update_token(self, token_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(**data)
            .returning(RefreshToken)
        )
        res = await self.db.execute(stmt)
        await self.db.flush()
        return res.scalar_one().__dict__

    async def delete_token(self, token_hash: str) -> None:
        stmt = delete(RefreshToken).where(RefreshToken.token_hash == token_hash)
        await self.db.execute(stmt)
        await self.db.flush()


def get_refresh_token_repository(
    db: AsyncSession = Depends(get_db),
) -> RefreshTokenRepository:
    return RefreshTokenRepository(db)
