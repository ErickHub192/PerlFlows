# app/handlers/redis_memory_handler.py
"""
Redis Memory Handler - Distributed short-term memory using Redis
Provides persistent short-term memory across server restarts
"""
import json
import time
import logging
from typing import Dict, Any, Optional, List
from uuid import UUID

from .connector_handler import ActionHandler
from app.connectors.factory import register_tool, register_node
from app.exceptions.api_exceptions import InvalidDataException
from app.core.config import settings
from app.ai.memories.memory_factory import register_short_term_memory, MemoryCapability

logger = logging.getLogger(__name__)

@register_node("RedisMemoryHandler")
@register_tool("RedisMemoryHandler")
@register_short_term_memory(
    name="RedisMemoryHandler",
    capabilities=[
        MemoryCapability.READ,
        MemoryCapability.WRITE,
        MemoryCapability.APPEND,
        MemoryCapability.CLEAR,
        MemoryCapability.EXPIRE,
        MemoryCapability.PERSISTENT
    ],
    description="Distributed short-term memory using Redis with TTL support",
    requires_credentials=False,
    persistent=True,
    max_storage=10000,  # High capacity
    cost_per_operation=0.001  # Small cost for Redis operations
)
class RedisMemoryHandler(ActionHandler):
    """
    Redis memory handler - Distributed short-term memory
    
    Uses Redis for persistent short-term memory that survives server restarts.
    Suitable for production environments with multiple instances.
    
    Operations:
    - load: Get all memories for agent
    - append: Add new memory item
    - clear: Clear all memories for agent
    - expire: Set TTL for agent memories
    """
    
    metadata = {
        "type": "tool",
        "category": "memory",
        "description": "Distributed short-term memory using Redis",
        "capabilities": ["load", "append", "clear", "expire"],
        "storage_type": "short_term",
        "persistent": True,
        "requires_credentials": False  # Uses global Redis config
    }
    
    def __init__(self, creds: Dict[str, Any] = None):
        super().__init__(creds or {})
        self._redis_client = None
    
    async def _get_redis_client(self):
        """Get or create Redis client"""
        if self._redis_client is None:
            try:
                import redis.asyncio as redis
                self._redis_client = redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
                # Test connection
                await self._redis_client.ping()
                logger.debug("Redis connection established for RedisMemoryHandler")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise InvalidDataException(f"Redis connection failed: {e}")
        
        return self._redis_client
    
    async def execute(
        self,
        params: Dict[str, Any],
        creds: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute Redis memory operation"""
        start_time = time.perf_counter()
        
        try:
            # Validate parameters
            validation_error = self._validate_params(params)
            if validation_error:
                return self._create_error_response(validation_error)
            
            # Get Redis client
            redis_client = await self._get_redis_client()
            
            # Extract parameters
            action = params.get("action")
            agent_id = UUID(str(params.get("agent_id")))
            
            # Execute action
            if action == "load":
                result = await self._load_memories(redis_client, agent_id)
            elif action == "append":
                item = params.get("item", {})
                window_size = params.get("window", 6)
                ttl = params.get("ttl", 3600)  # 1 hour default
                result = await self._append_memory(redis_client, agent_id, item, window_size, ttl)
            elif action == "clear":
                result = await self._clear_memories(redis_client, agent_id)
            elif action == "expire":
                ttl = params.get("ttl", 3600)
                result = await self._set_expiry(redis_client, agent_id, ttl)
            else:
                return self._create_error_response(f"Unknown action: {action}")
            
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            
            return {
                "status": "success",
                "output": result,
                "duration_ms": duration_ms,
                "handler": "RedisMemoryHandler",
                "agent_id": str(agent_id)
            }
            
        except Exception as e:
            logger.error(f"RedisMemoryHandler execution error: {e}", exc_info=True)
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return {
                "status": "error",
                "output": None,
                "error": str(e),
                "duration_ms": duration_ms,
                "handler": "RedisMemoryHandler"
            }
    
    def _validate_params(self, params: Dict[str, Any]) -> Optional[str]:
        """Validate parameters for Redis memory operations"""
        if not isinstance(params, dict):
            return "Parameters must be a dictionary"
        
        # Validate action
        action = params.get("action")
        if not action:
            return "action is required (load, append, clear, expire)"
        
        if action not in ["load", "append", "clear", "expire"]:
            return f"Invalid action: {action}. Must be load, append, clear, or expire"
        
        # Validate agent_id
        agent_id = params.get("agent_id")
        if not agent_id:
            return "agent_id is required"
        
        try:
            UUID(str(agent_id))
        except (ValueError, TypeError):
            return f"Invalid agent_id format: {agent_id}"
        
        # Validate append-specific parameters
        if action == "append":
            item = params.get("item")
            if not item:
                return "item is required for append action"
            
            if not isinstance(item, dict):
                return "item must be a dictionary"
        
        # Validate TTL
        if action in ["append", "expire"]:
            ttl = params.get("ttl", 3600)
            if not isinstance(ttl, int) or ttl <= 0:
                return "ttl must be a positive integer (seconds)"
        
        return None
    
    def _get_redis_key(self, agent_id: UUID) -> str:
        """Generate Redis key for agent memories"""
        return f"agent_memory:short_term:{str(agent_id)}"
    
    async def _load_memories(self, redis_client, agent_id: UUID) -> Dict[str, Any]:
        """Load all memories for agent from Redis"""
        key = self._get_redis_key(agent_id)
        
        try:
            # Get list of memory items
            memory_strings = await redis_client.lrange(key, 0, -1)
            memories = []
            
            for mem_str in memory_strings:
                try:
                    memory = json.loads(mem_str)
                    memories.append(memory)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse memory item: {e}")
                    continue
            
            # Get TTL info
            ttl = await redis_client.ttl(key)
            
            return {
                "memories": memories,
                "count": len(memories),
                "agent_id": str(agent_id),
                "storage_type": "redis",
                "ttl_seconds": ttl if ttl > 0 else None
            }
            
        except Exception as e:
            logger.error(f"Failed to load memories from Redis: {e}")
            return {
                "memories": [],
                "count": 0,
                "agent_id": str(agent_id),
                "storage_type": "redis",
                "error": str(e)
            }
    
    async def _append_memory(
        self, 
        redis_client, 
        agent_id: UUID, 
        item: Dict[str, Any], 
        window_size: int,
        ttl: int
    ) -> Dict[str, Any]:
        """Append memory item to Redis list with circular window"""
        key = self._get_redis_key(agent_id)
        
        try:
            # Add timestamp if not present
            if "timestamp" not in item:
                item["timestamp"] = time.time()
            
            # Serialize item
            item_str = json.dumps(item, ensure_ascii=False)
            
            # Use Redis pipeline for atomic operations
            pipe = redis_client.pipeline()
            
            # Add item to end of list
            pipe.rpush(key, item_str)
            
            # Trim list to maintain window size
            pipe.ltrim(key, -window_size, -1)
            
            # Set TTL
            pipe.expire(key, ttl)
            
            # Execute pipeline
            results = await pipe.execute()
            
            # Get current list length
            current_size = await redis_client.llen(key)
            
            return {
                "added": item,
                "buffer_size": current_size,
                "window_size": window_size,
                "agent_id": str(agent_id),
                "storage_type": "redis",
                "ttl_seconds": ttl
            }
            
        except Exception as e:
            logger.error(f"Failed to append memory to Redis: {e}")
            raise InvalidDataException(f"Redis append failed: {e}")
    
    async def _clear_memories(self, redis_client, agent_id: UUID) -> Dict[str, Any]:
        """Clear all memories for agent"""
        key = self._get_redis_key(agent_id)
        
        try:
            # Get count before deletion
            cleared_count = await redis_client.llen(key)
            
            # Delete the key
            await redis_client.delete(key)
            
            return {
                "cleared_count": cleared_count,
                "agent_id": str(agent_id),
                "storage_type": "redis"
            }
            
        except Exception as e:
            logger.error(f"Failed to clear memories from Redis: {e}")
            raise InvalidDataException(f"Redis clear failed: {e}")
    
    async def _set_expiry(self, redis_client, agent_id: UUID, ttl: int) -> Dict[str, Any]:
        """Set TTL for agent memories"""
        key = self._get_redis_key(agent_id)
        
        try:
            # Check if key exists
            exists = await redis_client.exists(key)
            if not exists:
                return {
                    "agent_id": str(agent_id),
                    "storage_type": "redis",
                    "ttl_set": False,
                    "reason": "No memories found for agent"
                }
            
            # Set expiry
            await redis_client.expire(key, ttl)
            
            return {
                "agent_id": str(agent_id),
                "storage_type": "redis", 
                "ttl_set": True,
                "ttl_seconds": ttl
            }
            
        except Exception as e:
            logger.error(f"Failed to set TTL in Redis: {e}")
            raise InvalidDataException(f"Redis expire failed: {e}")
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "status": "error",
            "output": None,
            "error": error_message,
            "handler": "RedisMemoryHandler"
        }
    
    # Memory Backend Protocol Compatibility
    # These methods provide compatibility with the old backend interface
    
    async def load_short_term(self, agent_id: UUID) -> List[Dict[str, Any]]:
        """Backend compatibility method"""
        redis_client = await self._get_redis_client()
        result = await self._load_memories(redis_client, agent_id)
        return result["memories"]
    
    async def append_short_term(self, agent_id: UUID, item: Dict[str, Any], window: int = 6) -> None:
        """Backend compatibility method"""
        redis_client = await self._get_redis_client()
        await self._append_memory(redis_client, agent_id, item, window, 3600)
    
    async def clear_short_term(self, agent_id: UUID) -> None:
        """Backend compatibility method"""
        redis_client = await self._get_redis_client()
        await self._clear_memories(redis_client, agent_id)


# Utility functions for Redis memory

async def get_redis_memory_stats() -> Dict[str, Any]:
    """Get statistics about Redis memory usage"""
    try:
        import redis.asyncio as redis
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        
        # Get all agent memory keys
        pattern = "agent_memory:short_term:*"
        keys = await client.keys(pattern)
        
        total_memories = 0
        agents_with_memories = []
        
        for key in keys:
            # Extract agent_id from key
            agent_id = key.split(":")[-1]
            agents_with_memories.append(agent_id)
            
            # Count memories for this agent
            count = await client.llen(key)
            total_memories += count
        
        await client.close()
        
        return {
            "total_agents": len(agents_with_memories),
            "total_memories": total_memories,
            "agents_with_memories": agents_with_memories,
            "redis_keys_count": len(keys)
        }
        
    except Exception as e:
        logger.error(f"Failed to get Redis memory stats: {e}")
        return {"error": str(e)}


async def clear_all_redis_memories() -> Dict[str, Any]:
    """Clear all Redis memories (useful for testing)"""
    try:
        import redis.asyncio as redis
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        
        # Get all agent memory keys
        pattern = "agent_memory:short_term:*"
        keys = await client.keys(pattern)
        
        if keys:
            cleared_count = await client.delete(*keys)
        else:
            cleared_count = 0
        
        await client.close()
        
        return {
            "cleared_agents": len(keys),
            "cleared_keys": cleared_count
        }
        
    except Exception as e:
        logger.error(f"Failed to clear Redis memories: {e}")
        return {"error": str(e)}