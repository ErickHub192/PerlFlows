import json
import asyncio
import logging
from typing import List, Dict, Any, Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ICag_service import ICAGService
from app.core.config import settings
from app.db.database import get_db
from app.repositories.node_repository import NodeRepository
from app.repositories.action_repository import ActionRepository
from app.repositories.parameter_repository import ParameterRepository
from app.ai.llm_clients.llm_service import get_redis
from app.exceptions.api_exceptions import WorkflowProcessingException


def get_node_repo(db: AsyncSession = Depends(get_db)) -> NodeRepository:
    return NodeRepository(db)


def get_action_repo(db: AsyncSession = Depends(get_db)) -> ActionRepository:
    return ActionRepository(db)


def get_cag_service(
    node_repo: NodeRepository = Depends(get_node_repo),
    action_repo: ActionRepository = Depends(get_action_repo),
    cache_key: str = getattr(settings, "CAG_CONTEXT_CACHE_KEY", "kyra:nodes:all"),
    db: AsyncSession = Depends(get_db),
) -> ICAGService:
    """
    ✅ Factory para RedisNodeCacheService - Redis-first approach
    """
    param_repo = ParameterRepository(db)
    return RedisNodeCacheService(node_repo, action_repo, param_repo, cache_key)


class RedisNodeCacheService(ICAGService):
    """
    🔥 OPCIÓN 2: Redis-First Node Cache Service
    
    - Inicializa cache Redis al startup desde Supabase
    - Function tool accede instantáneamente desde Redis  
    - Solo construye desde BD si cache miss crítico
    - Elimina construcción automática pesada
    """

    def __init__(
        self,
        node_repo: NodeRepository,
        action_repo: ActionRepository,
        param_repo: ParameterRepository,
        cache_key: str = "kyra:nodes:all",
    ):
        self.node_repo = node_repo
        self.action_repo = action_repo
        self.param_repo = param_repo
        self._cache_lock = asyncio.Lock()
        self._cache_key = cache_key
        self.logger = logging.getLogger(__name__)
        self._initialized = False

    async def initialize_cache_from_db(self) -> bool:
        """
        🚀 STARTUP: Inicializa cache Redis con todos los nodos desde Supabase.
        Solo se ejecuta una vez al arrancar la aplicación.
        """
        if self._initialized:
            self.logger.info("✅ Cache Redis ya inicializado, skip")
            return True
            
        async with self._cache_lock:
            if self._initialized:  # Double-check
                return True
                
            try:
                redis = await get_redis()
                if not redis:
                    raise WorkflowProcessingException("Redis no disponible para inicialización")

                self.logger.info("🔄 STARTUP: Inicializando cache Redis desde Supabase...")
                
                # Construir contexto completo desde BD (solo al startup)
                nodes = await self.node_repo.list_nodes()
                self.logger.info(f"📊 STARTUP: Encontrados {len(nodes)} nodos en BD")

                if not nodes:
                    raise WorkflowProcessingException("No hay nodos en BD para inicializar cache")

                context: List[Dict[str, Any]] = []
                for node in nodes:
                    node_type = getattr(node.node_type, "value", str(node.node_type))
                    actions = await self.action_repo.list_actions(node.node_id)
                    
                    action_list = []
                    for action in actions:
                        try:
                            parameters = await self.param_repo.list_parameters(action.action_id)
                            
                            params_metadata = []
                            for param in parameters:
                                param_dict = {
                                    "name": param.name,
                                    "description": param.description or "",
                                    "required": param.required,
                                    "type": getattr(param.param_type, "value", str(param.param_type)),
                                    "param_id": str(param.param_id)
                                }
                                params_metadata.append(param_dict)
                            
                            action_dict = {
                                "action_id": str(action.action_id),
                                "name": action.name,
                                "description": action.description,
                                "parameters": params_metadata
                            }
                            action_list.append(action_dict)
                            
                        except Exception as e:
                            self.logger.warning(f"Error obteniendo parámetros para action {action.action_id}: {e}")
                            action_list.append({
                                "action_id": str(action.action_id),
                                "name": action.name,
                                "description": action.description,
                                "parameters": []
                            })
                    
                    context.append({
                        "node_id": str(node.node_id),
                        "name": node.name,
                        "node_type": node_type,
                        "usage_mode": getattr(node, "usage_mode", None),
                        "default_auth": node.default_auth,
                        "use_case": node.use_case,
                        "actions": action_list,
                    })

                # Guardar en Redis con TTL largo (24 horas)
                ttl_startup = getattr(settings, "STARTUP_CACHE_TTL_SECONDS", 86400)  # 24h
                await redis.set(
                    self._cache_key,
                    json.dumps(context, ensure_ascii=False),
                    ex=ttl_startup
                )
                
                self._initialized = True
                self.logger.info(f"✅ STARTUP: Cache Redis inicializado - {len(context)} nodos, TTL {ttl_startup}s")
                return True

            except Exception as e:
                self.logger.error(f"❌ STARTUP: Error inicializando cache Redis: {e}", exc_info=True)
                raise WorkflowProcessingException(f"Error inicializando cache: {e}")

    async def build_context(self) -> List[Dict[str, Any]]:
        """
        🔧 REDIS-FIRST: Acceso instantáneo desde Redis.
        Solo construye desde BD si cache miss crítico.
        """
        try:
            redis = await get_redis()
            if not redis:
                self.logger.warning("⚠️ Redis no disponible, fallback a construcción BD")
                return await self._build_from_db_fallback()

            # Acceso instantáneo desde Redis
            cached = await redis.get(self._cache_key)
            if cached:
                context = json.loads(cached)
                self.logger.info(f"⚡ Redis HIT: {len(context)} nodos desde cache")
                return context
            else:
                self.logger.warning("⚠️ Redis MISS: Cache no inicializado, fallback a BD")
                return await self._build_from_db_fallback()

        except Exception as e:
            self.logger.error(f"❌ Error accediendo Redis cache: {e}", exc_info=True)
            return await self._build_from_db_fallback()

    async def _build_from_db_fallback(self) -> List[Dict[str, Any]]:
        """
        🆘 FALLBACK: Construcción desde BD solo en emergencias.
        Idealmente nunca debería ejecutarse si startup funciona bien.
        """
        self.logger.warning("🆘 FALLBACK: Construyendo contexto desde BD (no debería pasar en producción)")
        
        # Re-intentar inicializar cache si no estaba inicializado
        if not self._initialized:
            try:
                await self.initialize_cache_from_db()
                return await self.build_context()  # Retry con cache inicializado
            except Exception as e:
                self.logger.error(f"Error en fallback initialization: {e}")
        
        # Construcción directa desde BD (último recurso)
        nodes = await self.node_repo.list_nodes()
        if not nodes:
            raise WorkflowProcessingException("No se encontraron nodos en BD")
            
        # Construcción mínima sin cache
        context = []
        for node in nodes:
            context.append({
                "node_id": str(node.node_id),
                "name": node.name,
                "node_type": getattr(node.node_type, "value", str(node.node_type)),
                "usage_mode": getattr(node, "usage_mode", None),
                "default_auth": node.default_auth,
                "use_case": node.use_case,
                "actions": []  # Minimal context para emergencias
            })
        
        self.logger.info(f"🆘 Contexto mínimo construido: {len(context)} nodos")
        return context

    async def invalidate_cache(self) -> bool:
        """
        🗑️ Invalida cache Redis y marca como no inicializado.
        Útil para actualizaciones de BD o debugging.
        """
        try:
            redis = await get_redis()
            deleted = await redis.delete(self._cache_key)
            self._initialized = False  # Permite re-inicialización
            self.logger.info(f"🗑️ Cache Redis invalidado: {self._cache_key}, resultado={deleted}")
            return deleted > 0
        except Exception as e:
            self.logger.warning(f"Error invalidando cache Redis: {e}", exc_info=True)
            return False

    async def refresh_cache(self) -> bool:
        """
        🔄 Refresca cache Redis con datos actuales de BD.
        Útil cuando se agregan/modifican nodos.
        """
        try:
            await self.invalidate_cache()
            await self.initialize_cache_from_db()
            self.logger.info("🔄 Cache Redis refrescado exitosamente")
            return True
        except Exception as e:
            self.logger.error(f"Error refrescando cache Redis: {e}", exc_info=True)
            return False


# ✅ BACKWARD COMPATIBILITY: Alias para código existente
CAGService = RedisNodeCacheService

