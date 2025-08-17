from typing import List, Optional
from uuid import UUID
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from fastapi import Depends

from app.db.models import Action
from app.exceptions.api_exceptions import RepositoryException
from app.ai.llm_clients.llm_service import get_redis
from app.core.config import settings
from app.db.database import get_db

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class ActionRepository:
    """
    Repositorio para operaciones CRUD de Action con invalidación automática
    de caché Redis para mantener sincronizado el contexto CAG.

    Mejoras:
    - Clave de caché configurable desde settings.
    - Transacciones explícitas para asegurar consistencia.
    - Operaciones UPDATE/DELETE con RETURNING para reducir round-trips.
    - Eliminación en batch con COUNT desde resultado RETURNING.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        # Clave configurable en settings: CAG_CONTEXT_CACHE_KEY
        self._cache_key = getattr(settings, "CAG_CONTEXT_CACHE_KEY", "cag:context")

    async def _invalidate_context_cache(self) -> None:
        """
        Invalida la caché del contexto CAG en Redis.
        Este método se llama tras cualquier mutación de Actions.
        """
        try:
            redis = await get_redis()
            await redis.delete(self._cache_key)
            logger.info(f"Caché Redis invalidada: {self._cache_key}")
        except Exception as e:
            # Registrar fallo sin interrumpir la operación principal
            logger.warning(f"No se pudo invalidar caché Redis '{self._cache_key}': {e}", exc_info=True)

    # --- Operaciones de lectura ---

    async def list_actions(self, node_id: UUID) -> List[Action]:
        if node_id is None:
            logger.warning("ActionRepository.list_actions: called with None node_id")
            return []
        try:
            result = await self.db.execute(
                select(Action).where(Action.node_id == node_id)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching actions for node {node_id}: {e}", exc_info=True)
            try:
                await self.db.rollback()
                logger.info("Rollback completed successfully")
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
            raise RepositoryException(f"Failed to list actions for node {node_id}: {e}")

    async def get_action(self, action_id: UUID) -> Optional[Action]:
        if action_id is None:
            logger.warning("ActionRepository.get_action: called with None action_id")
            return None
        try:
            result = await self.db.execute(
                select(Action).where(Action.action_id == action_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching action {action_id}: {e}", exc_info=True)
            raise RepositoryException(f"Failed to get action {action_id}: {e}")

    # --- Operaciones de escritura ---

    async def create_action(self, action_data: dict) -> Action:
        try:
            action = Action(**action_data)
            async with self.db.begin():
                self.db.add(action)
            # action.id se refresca automáticamente tras commit
            await self._invalidate_context_cache()
            logger.info(f"Action created: {action.action_id}")
            return action
        except Exception as e:
            logger.error(f"Error creating action: {e}", exc_info=True)
            raise RepositoryException(f"Failed to create action: {e}")

    async def update_action(self, action_id: UUID, action_data: dict) -> Optional[Action]:
        if action_id is None:
            logger.warning("ActionRepository.update_action: called with None action_id")
            return None
        try:
            # UPDATE ... RETURNING * para obtener el objeto actualizado
            async with self.db.begin():
                result = await self.db.execute(
                    update(Action)
                    .where(Action.action_id == action_id)
                    .values(**action_data)
                    .returning(Action)
                )
                updated = result.scalar_one_or_none()
            if updated:
                await self._invalidate_context_cache()
                logger.info(f"Action updated: {action_id}")
            return updated
        except Exception as e:
            logger.error(f"Error updating action {action_id}: {e}", exc_info=True)
            raise RepositoryException(f"Failed to update action {action_id}: {e}")

    async def delete_action(self, action_id: UUID) -> bool:
        if action_id is None:
            logger.warning("ActionRepository.delete_action: called with None action_id")
            return False
        try:
            # DELETE ... RETURNING action_id para saber si existía
            async with self.db.begin():
                result = await self.db.execute(
                    delete(Action)
                    .where(Action.action_id == action_id)
                    .returning(Action.action_id)
                )
                deleted_ids = result.scalars().all()
            if deleted_ids:
                await self._invalidate_context_cache()
                logger.info(f"Action deleted: {action_id}")
                return True
            logger.warning(f"Attempt to delete non-existent action: {action_id}")
            return False
        except Exception as e:
            logger.error(f"Error deleting action {action_id}: {e}", exc_info=True)
            raise RepositoryException(f"Failed to delete action {action_id}: {e}")

    async def delete_actions_by_node(self, node_id: UUID) -> int:
        if node_id is None:
            logger.warning("ActionRepository.delete_actions_by_node: called with None node_id")
            return 0
        try:
            # DELETE en batch con RETURNING para contar eliminaciones
            async with self.db.begin():
                result = await self.db.execute(
                    delete(Action)
                    .where(Action.node_id == node_id)
                    .returning(Action.action_id)
                )
                deleted_ids = result.scalars().all()
            count = len(deleted_ids)
            if count:
                await self._invalidate_context_cache()
                logger.info(f"Deleted {count} actions for node {node_id}")
            return count
        except Exception as e:
            logger.error(f"Error deleting actions for node {node_id}: {e}", exc_info=True)
            raise RepositoryException(f"Failed to delete actions for node {node_id}: {e}")


def get_action_repository(db: AsyncSession = Depends(get_db)) -> ActionRepository:
    """Factory para obtener instancia de ActionRepository"""
    return ActionRepository(db)
