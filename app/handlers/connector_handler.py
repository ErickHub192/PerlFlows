# app/ai/connector_handler.py

from abc import ABC, abstractmethod
from typing import Any, Dict
from uuid import UUID

class ActionHandler(ABC):
    @abstractmethod
    async def execute(
        self,
        params: Dict[str, Any],
        
    ) -> Dict[str, Any]:
        """
        Ejecuta esta acción específica y devuelve el dict:
        {status, output, error?, duration_ms}
        """
        ...
