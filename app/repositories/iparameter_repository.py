# app/repositories/iparameter_repository.py

from abc import ABC, abstractmethod
from typing import List
from uuid import UUID

from app.db.models import Parameter

class IParameterRepository(ABC):
    @abstractmethod
    async def list_parameters(self, action_id: UUID) -> List[Parameter]:
        """
        Devuelve todos los objetos Parameter ORM asociados a la acción indicada.
        """
        ...

