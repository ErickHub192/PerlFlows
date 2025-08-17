"""
Cache Manager
=============

Módulo de cache unificado que proporciona una interfaz común para operaciones de cache.
Utiliza Redis como backend de almacenamiento.
"""

import json
import logging
import redis.asyncio as redis
from typing import Any, List, Optional, Union
from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Gestor de cache unificado usando Redis como backend.
    
    Proporciona operaciones básicas de cache: set, get, delete, y búsqueda por patrones.
    """
    
    def __init__(self):
        self.redis_client = None
        self.logger = logger
        self._connection_pool = None
        
    async def _get_redis_client(self) -> redis.Redis:
        """
        Obtiene el cliente Redis, creándolo si no existe.
        
        Returns:
            Cliente Redis configurado
        """
        if self.redis_client is None:
            try:
                # Crear pool de conexiones
                self._connection_pool = redis.ConnectionPool.from_url(
                    settings.REDIS_URL,
                    max_connections=20,
                    decode_responses=True
                )
                
                # Crear cliente Redis
                self.redis_client = redis.Redis(
                    connection_pool=self._connection_pool
                )
                
                # Verificar conexión
                await self.redis_client.ping()
                self.logger.info("✅ Redis cache manager initialized successfully")
                
            except Exception as e:
                self.logger.error(f"❌ Error initializing Redis cache manager: {e}")
                raise
                
        return self.redis_client
    
    async def set(self, key: str, value: Union[str, dict, list], ttl: Optional[int] = None) -> bool:
        """
        Almacena un valor en el cache.
        
        Args:
            key: Clave del cache
            value: Valor a almacenar (se serializará a JSON si no es string)
            ttl: Tiempo de vida en segundos (opcional)
            
        Returns:
            True si se almacenó correctamente, False en caso contrario
        """
        try:
            redis_client = await self._get_redis_client()
            
            # Convertir el valor a string si es necesario
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value, ensure_ascii=False)
            else:
                value_str = str(value)
            
            # Almacenar en Redis
            if ttl:
                await redis_client.setex(key, ttl, value_str)
            else:
                await redis_client.set(key, value_str)
            
            self.logger.debug(f"✅ Cache set: {key} (TTL: {ttl})")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error setting cache key {key}: {e}")
            return False
    
    async def get(self, key: str) -> Optional[str]:
        """
        Obtiene un valor del cache.
        
        Args:
            key: Clave del cache
            
        Returns:
            Valor almacenado o None si no existe
        """
        try:
            redis_client = await self._get_redis_client()
            value = await redis_client.get(key)
            
            if value is not None:
                self.logger.debug(f"✅ Cache hit: {key}")
                return value
            else:
                self.logger.debug(f"❌ Cache miss: {key}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Error getting cache key {key}: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """
        Elimina un valor del cache.
        
        Args:
            key: Clave del cache
            
        Returns:
            True si se eliminó correctamente, False en caso contrario
        """
        try:
            redis_client = await self._get_redis_client()
            deleted_count = await redis_client.delete(key)
            
            if deleted_count > 0:
                self.logger.debug(f"✅ Cache deleted: {key}")
                return True
            else:
                self.logger.debug(f"❌ Cache key not found for deletion: {key}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error deleting cache key {key}: {e}")
            return False
    
    async def get_keys_by_pattern(self, pattern: str) -> List[str]:
        """
        Obtiene todas las claves que coinciden con un patrón.
        
        Args:
            pattern: Patrón de búsqueda (ej: "workflow_oauth_state:*")
            
        Returns:
            Lista de claves que coinciden con el patrón
        """
        try:
            redis_client = await self._get_redis_client()
            keys = await redis_client.keys(pattern)
            
            self.logger.debug(f"✅ Found {len(keys)} keys matching pattern: {pattern}")
            return keys
            
        except Exception as e:
            self.logger.error(f"❌ Error getting keys by pattern {pattern}: {e}")
            return []
    
    async def exists(self, key: str) -> bool:
        """
        Verifica si una clave existe en el cache.
        
        Args:
            key: Clave del cache
            
        Returns:
            True si la clave existe, False en caso contrario
        """
        try:
            redis_client = await self._get_redis_client()
            exists = await redis_client.exists(key)
            
            self.logger.debug(f"✅ Cache key exists check: {key} = {bool(exists)}")
            return bool(exists)
            
        except Exception as e:
            self.logger.error(f"❌ Error checking if cache key exists {key}: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """
        Establece un tiempo de vida para una clave existente.
        
        Args:
            key: Clave del cache
            ttl: Tiempo de vida en segundos
            
        Returns:
            True si se estableció correctamente, False en caso contrario
        """
        try:
            redis_client = await self._get_redis_client()
            success = await redis_client.expire(key, ttl)
            
            if success:
                self.logger.debug(f"✅ Cache key TTL set: {key} = {ttl}s")
                return True
            else:
                self.logger.debug(f"❌ Cache key not found for TTL: {key}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error setting TTL for cache key {key}: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Incrementa un valor numérico en el cache.
        
        Args:
            key: Clave del cache
            amount: Cantidad a incrementar (por defecto 1)
            
        Returns:
            Nuevo valor después del incremento, o None si hay error
        """
        try:
            redis_client = await self._get_redis_client()
            new_value = await redis_client.incrby(key, amount)
            
            self.logger.debug(f"✅ Cache incremented: {key} = {new_value}")
            return new_value
            
        except Exception as e:
            self.logger.error(f"❌ Error incrementing cache key {key}: {e}")
            return None
    
    async def close(self):
        """
        Cierra las conexiones del cache manager.
        """
        try:
            if self.redis_client:
                await self.redis_client.close()
                self.logger.info("✅ Redis cache manager closed")
                
            if self._connection_pool:
                await self._connection_pool.disconnect()
                self.logger.info("✅ Redis connection pool closed")
                
        except Exception as e:
            self.logger.error(f"❌ Error closing cache manager: {e}")


# Instancia global del cache manager
_cache_manager = None


async def get_cache_manager() -> CacheManager:
    """
    Factory function para obtener instancia del cache manager.
    
    Returns:
        Instancia de CacheManager
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


async def close_cache_manager():
    """
    Cierra el cache manager global.
    """
    global _cache_manager
    if _cache_manager:
        await _cache_manager.close()
        _cache_manager = None