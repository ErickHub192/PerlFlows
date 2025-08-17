from typing import List, Optional
from uuid import UUID
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from fastapi import Depends

from app.db.models import Node
from app.exceptions.api_exceptions import RepositoryException
from app.ai.llm_clients.llm_service import get_redis
from app.core.config import settings
from app.db.database import get_db

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class NodeRepository:
    """
    Repositorio para operaciones CRUD de Node con invalidación automática
    de caché Redis para mantener sincronizado el contexto CAG.

    Mejoras aplicadas:
    - Clave de caché configurable desde settings.CAG_CONTEXT_CACHE_KEY
    - Transacciones explícitas para operaciones de escritura
    - Uso de RETURNING en UPDATE/DELETE para reducir round-trips
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self._cache_key = getattr(settings, "CAG_CONTEXT_CACHE_KEY", "cag:context")

    async def _invalidate_context_cache(self) -> None:
        """
        Borra la clave del contexto CAG en Redis.
        Debe llamarse después de cualquier mutación de Nodes.
        """
        try:
            redis = await get_redis()
            await redis.delete(self._cache_key)
            logger.info(f"Caché Redis invalidada: {self._cache_key}")
        except Exception as e:
            logger.warning(f"No se pudo invalidar caché Redis '{self._cache_key}': {e}", exc_info=True)

    # --- Operaciones de lectura ---

    async def list_nodes(self) -> List[Node]:
        """
        Recupera todos los nodos junto con sus acciones.
        """
        try:
            query = select(Node).options(selectinload(Node.actions))
            result = await self.db.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching nodes: {e}", exc_info=True)
            raise RepositoryException(f"Failed to list nodes: {e}")

    async def get_node_by_id(self, node_id: UUID) -> Optional[Node]:
        """
        Recupera un nodo por su ID.
        """
        if node_id is None:
            logger.warning("NodeRepository.get_node_by_id: called with None node_id")
            return None
        try:
            query = select(Node).where(Node.node_id == node_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching node {node_id}: {e}", exc_info=True)
            raise RepositoryException(f"Failed to get node {node_id}: {e}")

    async def get_node_by_name(self, name: str) -> Optional[Node]:
        """
        Recupera un nodo por su nombre.
        """
        if not name:
            logger.warning("NodeRepository.get_node_by_name: called with empty name")
            return None
        try:
            query = select(Node).where(Node.name == name)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching node by name '{name}': {e}", exc_info=True)
            raise RepositoryException(f"Failed to get node by name '{name}': {e}")

    async def list_embeddings(self) -> List[tuple[UUID, list[float]]]:
        """
        Lista pares (node_id, embedding) para nodos que tengan embeddings.
        """
        try:
            query = select(Node.node_id, Node.embedding).where(Node.embedding.isnot(None))
            result = await self.db.execute(query)
            return [(row[0], row[1]) for row in result.all()]
        except Exception as e:
            logger.error(f"Error listing embeddings: {e}", exc_info=True)
            raise RepositoryException(f"Failed to list embeddings: {e}")

    # --- Operaciones de escritura ---

    async def create_node(self, node_data: dict) -> Node:
        """Crea un nuevo nodo con los datos proporcionados, incluido ``usage_mode``."""
        try:
            node = Node(**node_data)
            async with self.db.begin():
                self.db.add(node)
            await self._invalidate_context_cache()
            logger.info(f"Node created: {node.node_id}")
            return node
        except Exception as e:
            logger.error(f"Error creating node: {e}", exc_info=True)
            raise RepositoryException(f"Failed to create node: {e}")

    async def update_node(self, node_id: UUID, node_data: dict) -> Optional[Node]:
        """Actualiza un nodo existente incluyendo ``usage_mode`` si se provee."""
        if node_id is None:
            logger.warning("NodeRepository.update_node: called with None node_id")
            return None
        try:
            async with self.db.begin():
                result = await self.db.execute(
                    update(Node)
                    .where(Node.node_id == node_id)
                    .values(**node_data)
                    .returning(Node)
                )
                updated = result.scalar_one_or_none()
            if updated:
                await self._invalidate_context_cache()
                logger.info(f"Node updated: {node_id}")
            return updated
        except Exception as e:
            logger.error(f"Error updating node {node_id}: {e}", exc_info=True)
            raise RepositoryException(f"Failed to update node {node_id}: {e}")

    async def delete_node(self, node_id: UUID) -> bool:
        """
        Elimina un nodo por su ID.
        """
        if node_id is None:
            logger.warning("NodeRepository.delete_node: called with None node_id")
            return False
        try:
            async with self.db.begin():
                result = await self.db.execute(
                    delete(Node)
                    .where(Node.node_id == node_id)
                    .returning(Node.node_id)
                )
                deleted_ids = result.scalars().all()
            if deleted_ids:
                await self._invalidate_context_cache()
                logger.info(f"Node deleted: {node_id}")
                return True
            logger.warning(f"Attempt to delete non-existent node: {node_id}")
            return False
        except Exception as e:
            logger.error(f"Error deleting node {node_id}: {e}", exc_info=True)
            raise RepositoryException(f"Failed to delete node {node_id}: {e}")


def get_node_repository(db: AsyncSession = Depends(get_db)) -> NodeRepository:
    """Factory para obtener instancia de NodeRepository"""
    return NodeRepository(db)
