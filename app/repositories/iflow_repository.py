from abc import ABC, abstractmethod
from typing import List
from uuid import UUID

from app.db.models import Flow

class IFlowRepository(ABC):
    """
    Interfaz para acceso a datos de flujos (flows).
    Define operaciones para listar y activar/desactivar definiciones de flujo.
    """

    @abstractmethod
    async def list_by_owner(self, owner_id: int) -> List[Flow]:
        """
        Devuelve todas las definiciones de flujo pertenecientes a un propietario.

        Args:
            owner_id: Identificador del usuario propietario del flujo.

        Returns:
            Lista de instancias Flow.
        """
        pass

    @abstractmethod
    async def set_active(self, flow_id: UUID, is_active: bool) -> Flow:
        """
        Activa o desactiva un flujo y devuelve la entidad actualizada.

        Args:
            flow_id: Identificador del flujo a modificar.
            is_active: Nuevo valor del flag de activación.

        Returns:
            Instancia Flow con el estado actualizado.
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, flow_id: UUID, owner_id: UUID | None = None) -> Flow:
        """Devuelve un flujo por su ID y opcionalmente valida el owner."""
        pass

    @abstractmethod
    async def update_trigger_id(self, flow_id: UUID, trigger_id: str | None) -> None:
        """Asigna o limpia el trigger_id de un flujo."""
        pass

    @abstractmethod
    async def create_flow(self, name: str, owner_id: int, spec: dict, description: str = None) -> Flow:
        """Crea un flujo a partir de una spec."""
        pass
