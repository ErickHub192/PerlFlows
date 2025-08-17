import logging
from fastapi import Depends
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.node_repository import NodeRepository
from app.repositories.action_repository import ActionRepository
from app.dtos.node_dto import NodeDTO
from app.db.database import get_db
from app.dtos.action_dto import ActionDTO

logger = logging.getLogger(__name__)

def get_connector_service(
    db: AsyncSession = Depends(get_db),
) -> 'ConnectorService':
    """
    Factory para inyección de dependencias
    ✅ Crea repositorios para inyección adecuada
    """
    node_repo = NodeRepository(db)
    action_repo = ActionRepository(db)
    return ConnectorService.get_instance(db, node_repo, action_repo)

class ConnectorService:
    """
    Service for listing connectors (nodes) and their actions.

    Implements a singleton pattern to ensure a single shared instance.
    """
    _instance: Optional['ConnectorService'] = None

    def __init__(
        self, 
        db: AsyncSession, 
        node_repo: NodeRepository, 
        action_repo: ActionRepository
    ):
        """
        Initialize ConnectorService with dependencies injected.
        ✅ Recibe repositorios por DI en lugar de instanciación directa
        :param db: AsyncSession instance connected to the database.
        :param node_repo: NodeRepository instance
        :param action_repo: ActionRepository instance
        """
        self._db: AsyncSession = db
        self.node_repo: NodeRepository = node_repo
        self.action_repo: ActionRepository = action_repo
        # Future: ParameterService could be injected here for loading parameters.

    @classmethod
    def get_instance(
        cls, 
        db: AsyncSession, 
        node_repo: NodeRepository = None, 
        action_repo: ActionRepository = None
    ) -> 'ConnectorService':
        """
        Returns a singleton instance of ConnectorService.
        ✅ Ahora recibe repositorios como parámetros
        :param db: AsyncSession instance; used only on first initialization.
        :param node_repo: NodeRepository instance
        :param action_repo: ActionRepository instance
        """
        # Reinitialize if a different session is provided
        if cls._instance is None or cls._instance._db is not db:
            if node_repo is None:
                node_repo = NodeRepository(db)
            if action_repo is None:
                action_repo = ActionRepository(db)
            cls._instance = cls(db, node_repo, action_repo)
        return cls._instance

    async def list_connectors(self) -> List[NodeDTO]:
        """
        Retrieves all nodes and their associated actions as DTOs.
        :return: List of NodeDTO with nested ActionDTO list.
        :raises: Exception if database queries fail.
        """
        try:
            nodes = await self.node_repo.list_nodes()
            result: List[NodeDTO] = []
            for node in nodes:
                actions = await self.action_repo.list_actions(node.node_id)
                action_dtos: List[ActionDTO] = [
                    ActionDTO(
                        action_id=action.action_id,
                        node_id=action.node_id,
                        name=action.name,
                        description=action.description,
                        is_trigger=getattr(action, "is_trigger", False)
                    )
                    for action in actions
                ]
                result.append(
                    NodeDTO(
                        node_id=node.node_id,
                        name=node.name,
                        node_type=node.node_type.value,
                        usage_mode=getattr(node, "usage_mode", None),
                        default_auth=node.default_auth,
                        use_case=node.use_case,

                        actions=action_dtos
                    )
                )
            return result
        except Exception as e:
            logger.error(f"Error listing connectors: {e}", exc_info=True)
            raise

# Singleton accessor: use ConnectorService.get_instance(db) to retrieve the shared instance
connector_service = ConnectorService.get_instance
