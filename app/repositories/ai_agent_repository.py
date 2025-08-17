# app/repositories/ai_agent_repository.py

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.models import AIAgent
from app.dtos.ai_agent_dto import AIAgentDTO
from app.mappers.ai_agent_mapper import to_ai_agent_dto


class AIAgentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_agents(self) -> List[AIAgentDTO]:
        result = await self.db.execute(select(AIAgent))
        agents = result.scalars().all()
        return [to_ai_agent_dto(a) for a in agents]

    async def get_agent(self, agent_id: UUID) -> Optional[AIAgentDTO]:
        result = await self.db.execute(
            select(AIAgent).where(AIAgent.agent_id == agent_id)
        )
        ag = result.scalar_one_or_none()
        return to_ai_agent_dto(ag) if ag else None

    async def create_agent(self, dto: AIAgentDTO) -> AIAgentDTO:
        agent = AIAgent(**dto.model_dump())
        self.db.add(agent)
        # ✅ Repository no maneja transacciones - solo flush para obtener ID
        await self.db.flush()
        await self.db.refresh(agent)
        return to_ai_agent_dto(agent)

    async def update_agent(self, agent_id: UUID, dto: AIAgentDTO) -> Optional[AIAgentDTO]:
        result = await self.db.execute(
            select(AIAgent).where(AIAgent.agent_id == agent_id)
        )
        ag = result.scalar_one_or_none()
        if not ag:
            return None
        for field, value in dto.model_dump().items():
            setattr(ag, field, value)
        # ✅ Repository no maneja transacciones - solo flush
        await self.db.flush()
        await self.db.refresh(ag)
        return to_ai_agent_dto(ag)

    async def delete_agent(self, agent_id: UUID) -> bool:
        result = await self.db.execute(
            select(AIAgent).where(AIAgent.agent_id == agent_id)
        )
        ag = result.scalar_one_or_none()
        if not ag:
            return False
        await self.db.delete(ag)
        # ✅ Repository no maneja transacciones - solo marca para delete
        await self.db.flush()
        return True


# Factory function for dependency injection
def get_ai_agent_repository(session) -> AIAgentRepository:
    """Factory function to create AIAgentRepository instance"""
    return AIAgentRepository(session)

