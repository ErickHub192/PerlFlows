# app/repositories/parameter_repository.py

from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.db.database import get_db  # asumes que expones un get_db en database.py
from app.db.models import Parameter

class ParameterRepository:
    """
    Repositorio para acceder a la tabla `parameters`.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_parameters(self, action_id: UUID) -> List[Parameter]:
        """
        Trae todos los parámetros (ORM) para la acción dada.
        """
        stmt = select(Parameter).where(Parameter.action_id == action_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()


# Factory para inyección en FastAPI
def get_parameter_repository(
    db: AsyncSession = Depends(get_db)
) -> ParameterRepository:
    """
    Dependency provider para ParameterRepository.
    """
    return ParameterRepository(db)
