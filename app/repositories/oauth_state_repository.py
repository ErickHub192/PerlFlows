# app/repositories/oauth_state_repository.py
from sqlalchemy import insert, select, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.models import OAuthState
from fastapi import Depends

class OAuthStateRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_oauth_state(self, user_id: int, provider: str, service_id: str, state: str, chat_id: str) -> None:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"💾 Saving OAuth state - user_id: {user_id}, provider: {provider}, service_id: {service_id}, state: {state}, chat_id: {chat_id}")
        
        stmt = pg_insert(OAuthState).values(
            user_id=user_id, provider=provider, service_id=service_id, state=state, chat_id=chat_id
        ).on_conflict_do_update(
            index_elements=["user_id", "provider", "service_id"],
            set_={"state": state, "chat_id": chat_id}
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def get_oauth_state(self, user_id: int, provider: str, service_id: str) -> str | None:
        stmt = select(OAuthState.state).where(
            OAuthState.user_id==user_id,
            OAuthState.provider==provider,
            OAuthState.service_id==service_id
        )
        res = await self.db.execute(stmt)
        row = res.scalar_one_or_none()
        return row
        
    async def get_oauth_state_by_state(self, state: str) -> tuple[int, str, str, str] | None:
        """Get user_id, provider, service_id, and chat_id by state string"""
        import logging
        logger = logging.getLogger(__name__)
        
        stmt = select(OAuthState.user_id, OAuthState.provider, OAuthState.service_id, OAuthState.chat_id).where(
            OAuthState.state == state
        )
        res = await self.db.execute(stmt)
        rows = res.fetchall()
        
        logger.info(f"OAuth state lookup - state: {state}, rows count: {len(rows)}, rows: {rows}")
        
        # Double check: let's also query all states to see what's in the table
        check_stmt = select(OAuthState.state, OAuthState.user_id, OAuthState.provider, OAuthState.service_id)
        check_res = await self.db.execute(check_stmt)
        all_states = check_res.fetchall()
        logger.info(f"🔍 ALL STATES in DB: {all_states}")
        
        if rows:
            row = rows[0]  # Get first row
            logger.info(f"Using row: {row}, type: {type(row)}")
            return row
        else:
            logger.info("No rows found")
            return None

    async def delete_oauth_state(self, user_id: int, provider: str, service_id: str) -> None:
        stmt = delete(OAuthState).where(
            OAuthState.user_id==user_id,
            OAuthState.provider==provider,
            OAuthState.service_id==service_id
        )
        await self.db.execute(stmt)
        await self.db.flush()
        
    async def delete_oauth_state_by_state(self, state: str) -> None:
        """Delete OAuth state by state string"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🗑️ DELETING OAuth state - state: {state}")
        
        stmt = delete(OAuthState).where(OAuthState.state == state)
        result = await self.db.execute(stmt)
        logger.info(f"🗑️ DELETE result - rowcount: {result.rowcount}")
        await self.db.flush()
        
async def get_oauth_state_repository(
    db: AsyncSession = Depends(get_db),
) -> OAuthStateRepository:
    """
    Dependencia para inyectar OAuthStateRepository en los handlers/servicios.
    """
    return OAuthStateRepository(db)        
