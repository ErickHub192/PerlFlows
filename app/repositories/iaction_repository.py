# app/repositories/iaction_repository.py
from typing import List, Optional
from uuid import UUID
from abc import ABC, abstractmethod
from app.db.models import Action

class IActionRepository(ABC):
    """
    Interfaz para el repositorio de Actions.
    Define los métodos que debe implementar cualquier repositorio de Actions,
    incluyendo operaciones CRUD y gestión de caché.
    """

    @abstractmethod
    async def list_actions(self, node_id: UUID) -> List[Action]:
        """
        Devuelve la lista de acciones asociadas a un nodo.

        Args:
            node_id: UUID del nodo.

        Returns:
            Lista de instancias Action.
        """
        ...

    @abstractmethod
    async def get_action(self, action_id: UUID) -> Optional[Action]:
        """
        Recupera una acción por su ID.

        Args:
            action_id: UUID de la acción.

        Returns:
            Instancia Action o None si no existe.
        """
        ...

    @abstractmethod
    async def create_action(self, action_data: dict) -> Action:
        """
        Crea una nueva acción con los datos proporcionados.

        Args:
            action_data: Diccionario con los campos para la nueva acción.

        Returns:
            La instancia Action recién creada.
        """
        ...

    @abstractmethod
    async def update_action(self, action_id: UUID, action_data: dict) -> Optional[Action]:
        """
        Actualiza una acción existente.

        Args:
            action_id: UUID de la acción a actualizar.
            action_data: Diccionario con los campos a modificar.

        Returns:
            Instancia Action actualizada, o None si no existe.
        """
        ...

    @abstractmethod
    async def delete_action(self, action_id: UUID) -> bool:
        """
        Elimina una acción por su ID.

        Args:
            action_id: UUID de la acción a eliminar.

        Returns:
            True si la acción fue eliminada, False si no existía.
        """
        ...

    @abstractmethod
    async def delete_actions_by_node(self, node_id: UUID) -> int:
        """
        Elimina todas las acciones asociadas a un nodo.

        Args:
            node_id: UUID del nodo.

        Returns:
            Número de acciones eliminadas.
        """
        ...
