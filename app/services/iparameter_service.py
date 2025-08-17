# app/services/iparameter_service.py

from abc import ABC, abstractmethod
from typing import List
from uuid import UUID
from app.dtos.parameter_dto import ActionParamDTO

class IParameterService(ABC):
    @abstractmethod
    async def list_parameters(self, action_id: UUID) -> List[ActionParamDTO]:
        """
        Devuelve la lista de parámetros (como DTOs) para la acción indicada.
        """
        ...
