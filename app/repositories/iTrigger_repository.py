from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID, uuid4
from app.db.models import Trigger


class ITriggerRepository(ABC):
    @abstractmethod
    async def create_trigger(
        self,
        flow_id: UUID,
        node_id: UUID,
        action_id: UUID,
        trigger_type: str,
        trigger_args: dict,
        job_id: str,
    ) -> Trigger:
        """Crea un registro de trigger y lo devuelve."""
        pass

    @abstractmethod
    async def get_active_triggers(
        self,
        flow_id: UUID
    ) -> List[Trigger]:
        """Devuelve todos los triggers activos para un flujo dado."""
        pass

    @abstractmethod
    async def delete_trigger(
        self,
        trigger_id: UUID
    ) -> None:
        """Elimina un trigger por su ID."""
        pass

    @abstractmethod
    async def list_by_owner(
        self,
        owner_id: int
    ) -> List[Trigger]:
        """Lista todos los triggers de un owner/usuario."""
        pass
