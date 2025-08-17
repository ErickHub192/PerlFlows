# app/workflow_engine/tools/cag_tools.py

from typing import List, Dict, Any
from app.connectors.factory import register_tool
from app.handlers.connector_handler import ActionHandler
from app.services.cag_service import get_cag_service
import logging

logger = logging.getLogger(__name__)

@register_tool("get_available_nodes", usage_mode="tool")
class GetAvailableNodesHandler(ActionHandler):
    """
    Function tool que permite al LLM obtener todos los nodos/servicios disponibles
    cuando necesite conocer las capacidades del sistema.
    
    Uso: El LLM llama esta función solo cuando realmente necesita saber qué servicios están disponibles.
    """
    
    def __init__(self, creds: Dict[str, Any] = None):
        # No llamar super().__init__ - ActionHandler puede requerir parámetros específicos
        self.creds = creds or {}
        self.cag_service = None  # Se inicializará bajo demanda
    
    async def execute(self, params: Dict[str, Any], creds: Dict[str, Any]) -> Dict[str, Any]:
        """
        🔥 REDIS-FIRST: Acceso instantáneo a nodos desde cache Redis.
        Solo construye desde BD en caso de cache miss.
        
        Returns:
            Dict con la lista completa de nodos/servicios desde Redis cache
        """
        try:
            logger.info("🔧 LLM solicitó nodos disponibles via get_available_nodes() - Redis access")
            
            # Lazy initialization del service
            if self.cag_service is None:
                from sqlalchemy.ext.asyncio import AsyncSession
                from app.db.database import get_db
                from app.repositories.node_repository import NodeRepository
                from app.repositories.action_repository import ActionRepository
                from app.repositories.parameter_repository import ParameterRepository
                from app.services.cag_service import RedisNodeCacheService
                
                # Para function tools, usamos una instancia temporal
                # En producción esto podría ser inyectado via DI
                async with get_db().__anext__() as db:
                    node_repo = NodeRepository(db)
                    action_repo = ActionRepository(db) 
                    param_repo = ParameterRepository(db)
                    self.cag_service = RedisNodeCacheService(node_repo, action_repo, param_repo)
            
            # Acceso instantáneo desde Redis (o fallback a BD)
            available_nodes = await self.cag_service.build_context()
            
            logger.info(f"⚡ Redis access completado: {len(available_nodes)} nodos disponibles")
            
            # 🔍 DEBUG: Mostrar muestra de nodos obtenidos
            logger.info("🔍 FIRST 3 NODES from get_available_nodes():")
            for i, node in enumerate(available_nodes[:3]):
                logger.info(f"  Node {i+1}: ID={node.get('node_id')}, Name={node.get('name')}, Provider={node.get('provider')}")
                if node.get('actions'):
                    logger.info(f"    Actions: {[a.get('action_name') for a in node.get('actions', [])[:2]]}")
            
            # 🔍 ESTADÍSTICAS
            providers = {}
            for node in available_nodes:
                provider = node.get('provider', 'unknown')
                providers[provider] = providers.get(provider, 0) + 1
            logger.info(f"🔍 NODES BY PROVIDER: {providers}")
            
            return {
                "status": "success",
                "output": {
                    "available_nodes": available_nodes,
                    "total_count": len(available_nodes),
                    "message": f"Nodos obtenidos desde Redis cache: {len(available_nodes)} disponibles"
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo nodos desde Redis: {e}")
            return {
                "status": "error", 
                "output": None,
                "error": f"No se pudo obtener nodos disponibles: {str(e)}"
            }
    
    def get_parameters(self) -> List[Dict[str, Any]]:
        """
        No requiere parámetros - siempre retorna el CAG completo.
        """
        return []
    
    def get_description(self) -> str:
        return """🔧 Obtiene todos los nodos/servicios disponibles desde Redis cache. 
        Acceso instantáneo a 48+ nodos/servicios con sus acciones y parámetros.
        Úsala SOLO cuando necesites conocer qué capacidades están disponibles 
        y no tengas suficiente información del workflow anterior."""