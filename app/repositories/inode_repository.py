# app/repositories/inode_repository.py
from typing import List, Optional
from uuid import UUID
from abc import ABC, abstractmethod
from app.db.models import Node

class INodeRepository(ABC):
    """
    Interfaz para el repositorio de Nodes.
    Define operaciones de lectura y escritura, junto con gestión de embeddings y sincronización de caché CAG.
    """

    @abstractmethod
    async def list_nodes(self) -> List[Node]:
        """
        Devuelve la lista de todos los nodos, incluyendo relaciones necesarias (e.g., acciones).
        """
        ...

    @abstractmethod
    async def get_node_by_id(self, node_id: UUID) -> Optional[Node]:
        """
        Recupera un nodo por su ID.

        Args:
            node_id: UUID del nodo.

        Returns:
            Instancia de Node o None si no existe.
        """
        ...

    @abstractmethod
    async def get_node_by_name(self, name: str) -> Optional[Node]:
        """
        Recupera un nodo por su nombre.

        Args:
            name: Nombre único del nodo.

        Returns:
            Instancia de Node o None si no existe.
        """
        ...

    @abstractmethod
    async def list_embeddings(self) -> List[tuple[UUID, list[float]]]:
        """
        Retorna pares (node_id, embedding_vector) para nodos con embedding no nulo.
        """
        ...

    @abstractmethod
    async def create_node(self, node_data: dict) -> Node:
        """
        Crea un nuevo nodo con los datos proporcionados.

        Args:
            node_data: Diccionario con los campos para la nueva entidad Node.

        Returns:
            Instancia Node recién creada.
        """
        ...

    @abstractmethod
    async def update_node(self, node_id: UUID, node_data: dict) -> Optional[Node]:
        """
        Actualiza un nodo existente.

        Args:
            node_id: UUID del nodo a actualizar.
            node_data: Diccionario con los campos a modificar.

        Returns:
            Instancia Node actualizada, o None si no existe.
        """
        ...

    @abstractmethod
    async def delete_node(self, node_id: UUID) -> bool:
        """
        Elimina un nodo por su ID.

        Args:
            node_id: UUID del nodo a eliminar.

        Returns:
            True si se eliminó, False si no existía.
        """
        ...
