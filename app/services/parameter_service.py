# app/services/parameter_service.py

from typing import List
from uuid import UUID
from app.db.database import get_db
from app.dtos.parameter_dto import ActionParamDTO
from app.services.iparameter_service import IParameterService
from app.repositories.iparameter_repository import IParameterRepository
from app.repositories.parameter_repository import ParameterRepository
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession


def get_parameter_service(
    db: AsyncSession = Depends(get_db),
) -> IParameterService:
    """
    Factory para inyección de dependencias
    """
    return ParameterService(repo=ParameterRepository(db))

class ParameterService(IParameterService):
    def __init__(self, repo: IParameterRepository):
        self.repo = repo

    async def list_parameters(self, action_id: UUID) -> List[ActionParamDTO]:
        """
        Recupera los registros ORM desde el repositorio y los convierte en DTOs.
        """
        orm_params = await self.repo.list_parameters(action_id)
        return [ActionParamDTO.model_validate(p) for p in orm_params]
    
    
