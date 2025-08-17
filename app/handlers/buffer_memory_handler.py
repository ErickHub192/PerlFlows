# app/handlers/buffer_memory_handler.py
"""
Buffer Memory Handler - Short-term memory in RAM with circular buffer
Migrated from app/ai/memories/backends/buffer.py
"""
import time
import logging
from typing import Dict, Any, Optional, List
from uuid import UUID

from .connector_handler import ActionHandler
from app.connectors.factory import register_tool, register_node
from app.exceptions.api_exceptions import InvalidDataException
from app.ai.memories.memory_factory import register_short_term_memory, MemoryCapability

logger = logging.getLogger(__name__)

@register_node("BufferMemoryHandler")
@register_tool("BufferMemoryHandler")
@register_short_term_memory(
    name="BufferMemoryHandler",
    capabilities=[
        MemoryCapability.READ,
        MemoryCapability.WRITE,
        MemoryCapability.APPEND,
        MemoryCapability.CLEAR
    ],
    description="Fast in-memory buffer with circular window for chat history",
    requires_credentials=False,
    persistent=False,
    max_storage=1000,  # Max items per agent
    cost_per_operation=0.0
)
class BufferMemoryHandler(ActionHandler):
    """
    Buffer memory handler - Short-term memory stored in RAM
    
    Uses circular buffer with configurable window size.
    Perfect for chat history and recent context.
    
    Operations:
    - load: Get all memories for agent
    - append: Add new memory item
    - clear: Clear all memories for agent
    """
    
    metadata = {
        "type": "tool",
        "category": "memory",
        "description": "Short-term memory buffer in RAM",
        "capabilities": ["load", "append", "clear"],
        "storage_type": "short_term",
        "persistent": False
    }
    
    def __init__(self, creds: Dict[str, Any] = None):
        super().__init__(creds or {})
        # Global buffer storage - shared across all instances
        if not hasattr(BufferMemoryHandler, '_global_buffers'):
            BufferMemoryHandler._global_buffers: Dict[UUID, List[Dict[str, Any]]] = {}
    
    async def execute(
        self,
        params: Dict[str, Any],
        creds: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute buffer memory operation"""
        start_time = time.perf_counter()
        
        try:
            # Validate parameters
            validation_error = self._validate_params(params)
            if validation_error:
                return self._create_error_response(validation_error)
            
            # Extract parameters
            action = params.get("action")
            agent_id = UUID(str(params.get("agent_id")))
            window_size = params.get("window", 6)
            
            # Execute action
            if action == "load":
                result = await self._load_memories(agent_id)
            elif action == "append":
                item = params.get("item", {})
                result = await self._append_memory(agent_id, item, window_size)
            elif action == "clear":
                result = await self._clear_memories(agent_id)
            else:
                return self._create_error_response(f"Unknown action: {action}")
            
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            
            return {
                "status": "success",
                "output": result,
                "duration_ms": duration_ms,
                "handler": "BufferMemoryHandler",
                "agent_id": str(agent_id)
            }
            
        except Exception as e:
            logger.error(f"BufferMemoryHandler execution error: {e}", exc_info=True)
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return {
                "status": "error",
                "output": None,
                "error": str(e),
                "duration_ms": duration_ms,
                "handler": "BufferMemoryHandler"
            }
    
    def _validate_params(self, params: Dict[str, Any]) -> Optional[str]:
        """Validate parameters for buffer memory operations"""
        if not isinstance(params, dict):
            return "Parameters must be a dictionary"
        
        # Validate action
        action = params.get("action")
        if not action:
            return "action is required (load, append, clear)"
        
        if action not in ["load", "append", "clear"]:
            return f"Invalid action: {action}. Must be load, append, or clear"
        
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
        
        # Validate window size
        window = params.get("window", 6)
        if not isinstance(window, int) or window <= 0:
            return "window must be a positive integer"
        
        return None
    
    async def _load_memories(self, agent_id: UUID) -> Dict[str, Any]:
        """Load all memories for agent from buffer"""
        memories = list(BufferMemoryHandler._global_buffers.get(agent_id, []))
        
        return {
            "memories": memories,
            "count": len(memories),
            "agent_id": str(agent_id),
            "storage_type": "buffer"
        }
    
    async def _append_memory(self, agent_id: UUID, item: Dict[str, Any], window_size: int) -> Dict[str, Any]:
        """Append memory item to buffer with circular window"""
        # Get or create buffer for agent
        if agent_id not in BufferMemoryHandler._global_buffers:
            BufferMemoryHandler._global_buffers[agent_id] = []
        
        buf = BufferMemoryHandler._global_buffers[agent_id]
        
        # Add timestamp if not present
        if "timestamp" not in item:
            item["timestamp"] = time.time()
        
        # Append item
        buf.append(item)
        
        # Implement circular buffer - remove oldest if exceeds window
        if len(buf) > window_size:
            removed_item = buf.pop(0)
            logger.debug(f"Removed oldest memory for agent {agent_id}: {removed_item.get('timestamp')}")
        
        return {
            "added": item,
            "buffer_size": len(buf),
            "window_size": window_size,
            "agent_id": str(agent_id),
            "storage_type": "buffer"
        }
    
    async def _clear_memories(self, agent_id: UUID) -> Dict[str, Any]:
        """Clear all memories for agent"""
        cleared_count = len(BufferMemoryHandler._global_buffers.get(agent_id, []))
        BufferMemoryHandler._global_buffers.pop(agent_id, None)
        
        return {
            "cleared_count": cleared_count,
            "agent_id": str(agent_id),
            "storage_type": "buffer"
        }
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "status": "error",
            "output": None,
            "error": error_message,
            "handler": "BufferMemoryHandler"
        }
    
    # Memory Backend Protocol Compatibility
    # These methods provide compatibility with the old backend interface
    
    async def load_short_term(self, agent_id: UUID) -> List[Dict[str, Any]]:
        """Backend compatibility method"""
        result = await self._load_memories(agent_id)
        return result["memories"]
    
    async def append_short_term(self, agent_id: UUID, item: Dict[str, Any], window: int = 6) -> None:
        """Backend compatibility method"""
        await self._append_memory(agent_id, item, window)
    
    async def clear_short_term(self, agent_id: UUID) -> None:
        """Backend compatibility method"""
        await self._clear_memories(agent_id)


# Utility functions for buffer memory

def get_buffer_stats() -> Dict[str, Any]:
    """Get statistics about buffer memory usage"""
    if not hasattr(BufferMemoryHandler, '_global_buffers'):
        return {"total_agents": 0, "total_memories": 0}
    
    buffers = BufferMemoryHandler._global_buffers
    total_memories = sum(len(buf) for buf in buffers.values())
    
    return {
        "total_agents": len(buffers),
        "total_memories": total_memories,
        "agents_with_memories": [str(agent_id) for agent_id in buffers.keys()]
    }


def clear_all_buffers() -> Dict[str, Any]:
    """Clear all buffer memories (useful for testing)"""
    if hasattr(BufferMemoryHandler, '_global_buffers'):
        cleared_agents = len(BufferMemoryHandler._global_buffers)
        cleared_memories = sum(len(buf) for buf in BufferMemoryHandler._global_buffers.values())
        BufferMemoryHandler._global_buffers.clear()
        
        return {
            "cleared_agents": cleared_agents,
            "cleared_memories": cleared_memories
        }
    
    return {"cleared_agents": 0, "cleared_memories": 0}
