import time
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
import asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.config import settings
from app.exceptions.api_exceptions import WorkflowProcessingException
from app.dtos.parameter_dto import ActionParamDTO
from app.dtos.connector_dto import ConnectorDTO
from app.db.database import async_session
from app.db.models import Node

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# --- Funciones simples para el MVP ---

async def fetch_action_parameters_simple(action_id: UUID) -> List[ActionParamDTO]:
    """
    Versión simple para el MVP: sin cache TTL.
    (Se mantiene vía HTTP para parámetros, si lo necesitas)
    """
    try:
        from httpx import HTTPError
        from app.core.http_client import http_client

        url = f"{settings.API_BASE_URL.rstrip('/')}/parameters/{action_id}/"
        resp = await http_client.get(url)
        resp.raise_for_status()
        data = resp.json() or []
        return [ActionParamDTO(**item) for item in data]
    except HTTPError as e:
        raise WorkflowProcessingException(
            f"Error fetching parameters for action {action_id}: {e}"
        )


class ConnectorClient:
    """
    Cliente con TTL cache de conectores.
    
    - Lista de conectores cargada desde la DB en un solo round-trip (selectinload).
    - Parámetros de acciones vía HTTP (TTL cache).
    """
    # Caché para conectores
    _cache: List[ConnectorDTO] = []
    _cache_dict: Dict[UUID, ConnectorDTO] = {}
    _cache_ts: float = 0.0
    _cache_ttl: int = getattr(settings, "CONNECTORS_CACHE_TTL", 300)
    _semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_REQUESTS)
    
    # Caché para parámetros de acciones
    _action_params_cache: Dict[UUID, List[ActionParamDTO]] = {}
    _action_params_ts: Dict[UUID, float] = {}  # Corregido: debe ser un diccionario

    async def fetch_connectors(self) -> List[ConnectorDTO]:
        """
        Obtiene la lista de conectores con caché TTL,
        cargando de la DB todos los nodos + sus actions en lote.
        """
        now = time.perf_counter()
        if not ConnectorClient._cache or (now - ConnectorClient._cache_ts > ConnectorClient._cache_ttl):
            logger.debug("Cache miss: loading connectors from DB")

            # 1) Eager‐load de Node + Actions en un solo paso
            async with async_session() as session:
                result = await session.execute(
                    select(Node)
                    .options(selectinload(Node.actions))
                )
                nodes: List[Node] = result.scalars().all()

            # 2) Mapear cada Node ORM a tu DTO de conector
            ConnectorClient._cache = []
            for node in nodes:
                # Asume que ConnectorDTO acepta estos campos; ajusta si tu DTO difiere
                dto = ConnectorDTO(
                    node_id=node.node_id,
                    name=node.name,
                    default_auth=node.default_auth,
                    usage_mode=getattr(node, "usage_mode", None),

                    actions=[
                        {
                            "action_id": action.action_id,
                            "node_id": action.node_id,
                            "name": action.name,
                            "description": action.description,
                            "is_trigger": action.is_trigger,
                        }
                        for action in node.actions
                    ]
                )
                ConnectorClient._cache.append(dto)

            # 3) Reconstruir el diccionario para acceso O(1)
            ConnectorClient._cache_dict = {
                c.node_id: c for c in ConnectorClient._cache
            }
            ConnectorClient._cache_ts = now
        else:
            logger.debug("Cache hit: using cached connectors")
        
        return ConnectorClient._cache
    
        delay = 0.5
        for intento in range(3):
            try:
                return await self._load_connectors_from_db()
            except Exception as e:
                logging.warning(f"ConnectorClient.fetch_connectors intento {intento+1} falló: {e}")
                if intento < 2:
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
                    logging.error("ConnectorClient: no pudo cargar conectores, devuelvo vacío")
                    return []    

    async def get_connector(self, node_id: UUID) -> Optional[ConnectorDTO]:
        """
        Obtiene un conector específico por su ID de manera eficiente (caché O(1)).
        """
        await self.fetch_connectors()
        return ConnectorClient._cache_dict.get(node_id)

    async def fetch_action_parameters(self, action_id: UUID) -> List[ActionParamDTO]:
        """
        Obtiene los parámetros de una acción con caché TTL.
        """
        now = time.perf_counter()
        last_ts = ConnectorClient._action_params_ts.get(action_id, 0.0)

        # Cache hit por acción individual
        if (
            action_id in ConnectorClient._action_params_cache
            and (now - last_ts) <= ConnectorClient._cache_ttl
        ):
            logger.debug(f"Cache hit: parameters for action {action_id}")
            return ConnectorClient._action_params_cache[action_id]

        # Cache miss: fetch y refresco de timestamp
        logger.debug(f"Cache miss: fetching parameters for action {action_id}")
        params = await fetch_action_parameters_simple(action_id)
        ConnectorClient._action_params_cache[action_id] = params
        ConnectorClient._action_params_ts[action_id] = now
        return params
        
        async with ConnectorClient._semaphore:
            return await fetch_action_parameters_simple(action_id)

    async def execute_action(
        self,
        node_id: UUID,
        action_id: UUID,
        params: Dict[str, Any],
        creds: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta una acción en un nodo específico.
        Sin caché, porque las ejecuciones deben ser frescas.
        """
        from app.connectors.connector_client import execute_action_simple
        return await execute_action_simple(node_id, action_id, params, creds)

    async def invalidate_cache(self):
        """
        Invalida manualmente el caché de conectores y parámetros.
        """
        ConnectorClient._cache = []
        ConnectorClient._cache_dict = {}
        ConnectorClient._action_params_cache = {}
        ConnectorClient._cache_ts = 0.0
        ConnectorClient._action_params_ts = {}  # Corregido: inicializar como diccionario vacío
        logger.debug("ConnectorClient cache invalidated")


def get_connector_client() -> ConnectorClient:
    """
    Factory para inyección en FastAPI o para tests.
    """
    return ConnectorClient()


