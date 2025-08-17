# app/handlers/core_memory_handler.py
"""
Core Memory Handler - Always in context memory
Refactored to work independently without legacy memory services
"""
import time
import logging
from typing import Dict, Any, Optional
from uuid import UUID

from .connector_handler import ActionHandler
from app.connectors.factory import register_tool, register_node
from app.exceptions.api_exceptions import InvalidDataException
from app.ai.memories.memory_factory import register_core_memory, MemoryCapability

logger = logging.getLogger(__name__)

@register_node("CoreMemoryHandler")
@register_tool("CoreMemoryHandler")
@register_core_memory(
    name="CoreMemoryHandler",
    capabilities=[
        MemoryCapability.READ,
        MemoryCapability.WRITE,
        MemoryCapability.APPEND,
        MemoryCapability.CLEAR,
        MemoryCapability.PERSISTENT
    ],
    description="Always-in-context memory for critical agent information",
    requires_credentials=False,
    persistent=False,  # Currently in-memory, can be made persistent
    max_storage=10,  # Limited sections per agent
    cost_per_operation=0.0
)
class CoreMemoryHandler(ActionHandler):
    """
    Core memory handler - Always in context memory
    
    Manages persistent agent memory sections like user profile, agent persona, etc.
    Core memory is always loaded in context for consistent behavior.
    Simple in-memory storage with persistence planned for future.
    """
    
    metadata = {
        "type": "tool",
        "category": "memory",
        "description": "Manage agent's core memory (always in context)",
        "capabilities": ["read", "update", "append", "clear"],
        "storage_type": "core",
        "persistent": False,  # Currently in-memory
        "max_content_length": 2000
    }
    
    def __init__(self, creds: Dict[str, Any] = None):
        super().__init__(creds or {})
        # Global core memory storage - shared across instances
        if not hasattr(CoreMemoryHandler, '_global_core_memory'):
            CoreMemoryHandler._global_core_memory: Dict[UUID, Dict[str, Any]] = {}

    async def execute(
        self,
        params: Dict[str, Any],
        creds: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute core memory operation"""
        start_time = time.perf_counter()
        
        try:
            # Validate parameters
            validation_error = self._validate_params(params)
            if validation_error:
                return self._create_error_response(validation_error)
            
            # Extract parameters
            action = params.get("action")
            agent_id = UUID(str(params.get("agent_id")))
            section = params.get("section")
            
            # Execute action
            if action == "read":
                result = await self._read_core_memory(agent_id, section)
            elif action == "update":
                content = params.get("content")
                result = await self._update_core_memory(agent_id, section, content)
            elif action == "append":
                content = params.get("content")
                result = await self._append_core_memory(agent_id, section, content)
            elif action == "clear":
                if section:
                    result = await self._clear_section(agent_id, section)
                else:
                    result = await self._clear_all_core_memory(agent_id)
            else:
                return self._create_error_response(f"Unknown action: {action}")
            
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            
            return {
                "status": "success",
                "output": result,
                "duration_ms": duration_ms,
                "handler": "CoreMemoryHandler",
                "agent_id": str(agent_id)
            }
            
        except Exception as e:
            logger.error(f"CoreMemoryHandler execution error: {e}", exc_info=True)
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return {
                "status": "error",
                "output": None,
                "error": str(e),
                "duration_ms": duration_ms,
                "handler": "CoreMemoryHandler"
            }
    
    def _validate_params(self, params: Dict[str, Any]) -> Optional[str]:
        """Validate parameters for core memory operations"""
        if not isinstance(params, dict):
            return "Parameters must be a dictionary"
        
        # Validate action
        action = params.get("action")
        if not action:
            return "action is required (read, update, append, clear)"
        
        if action not in ["read", "update", "append", "clear"]:
            return f"Invalid action: {action}. Must be read, update, append, or clear"
        
        # Validate agent_id
        agent_id = params.get("agent_id")
        if not agent_id:
            return "agent_id is required"
        
        try:
            UUID(str(agent_id))
        except (ValueError, TypeError):
            return f"Invalid agent_id format: {agent_id}"
        
        # Validate section (required for read, update, append)
        if action in ["read", "update", "append"]:
            section = params.get("section")
            if not section:
                return "section is required (user_profile, agent_persona, context, etc.)"
        
        # Validate content for update/append operations
        if action in ["update", "append"]:
            content = params.get("content")
            if not content:
                return f"content is required for {action} action"
            
            # Check content length
            if len(str(content)) > self.metadata["max_content_length"]:
                return f"Content too long. Max {self.metadata['max_content_length']} characters"
        
        return None

    async def _read_core_memory(self, agent_id: UUID, section: str) -> Dict[str, Any]:
        """Read core memory section for agent"""
        core_memory = CoreMemoryHandler._global_core_memory.get(agent_id, {})
        content = core_memory.get(section, "")
        
        return {
            "agent_id": str(agent_id),
            "section": section,
            "content": content,
            "exists": bool(content),
            "storage_type": "core"
        }
    
    async def _update_core_memory(self, agent_id: UUID, section: str, content: str) -> Dict[str, Any]:
        """Update core memory section (replace existing content)"""
        if agent_id not in CoreMemoryHandler._global_core_memory:
            CoreMemoryHandler._global_core_memory[agent_id] = {}
        
        old_content = CoreMemoryHandler._global_core_memory[agent_id].get(section, "")
        CoreMemoryHandler._global_core_memory[agent_id][section] = str(content)
        
        return {
            "agent_id": str(agent_id),
            "section": section,
            "action": "updated",
            "new_content": content,
            "old_content": old_content,
            "content_length": len(str(content)),
            "storage_type": "core"
        }
    
    async def _append_core_memory(self, agent_id: UUID, section: str, content: str) -> Dict[str, Any]:
        """Append to core memory section"""
        if agent_id not in CoreMemoryHandler._global_core_memory:
            CoreMemoryHandler._global_core_memory[agent_id] = {}
        
        existing_content = CoreMemoryHandler._global_core_memory[agent_id].get(section, "")
        
        # Append with newline if existing content exists
        if existing_content:
            new_content = existing_content + "\n" + str(content)
        else:
            new_content = str(content)
        
        # Check length limit after append
        if len(new_content) > self.metadata["max_content_length"]:
            return {
                "agent_id": str(agent_id),
                "section": section,
                "action": "append_failed",
                "error": f"Content would exceed max length of {self.metadata['max_content_length']} characters",
                "current_length": len(existing_content),
                "attempted_length": len(new_content)
            }
        
        CoreMemoryHandler._global_core_memory[agent_id][section] = new_content
        
        return {
            "agent_id": str(agent_id),
            "section": section,
            "action": "appended",
            "appended_content": content,
            "final_content": new_content,
            "content_length": len(new_content),
            "storage_type": "core"
        }
    
    async def _clear_section(self, agent_id: UUID, section: str) -> Dict[str, Any]:
        """Clear specific core memory section"""
        if agent_id in CoreMemoryHandler._global_core_memory:
            cleared_content = CoreMemoryHandler._global_core_memory[agent_id].pop(section, "")
            was_cleared = bool(cleared_content)
        else:
            was_cleared = False
            cleared_content = ""
        
        return {
            "agent_id": str(agent_id),
            "section": section,
            "action": "section_cleared",
            "was_cleared": was_cleared,
            "cleared_content": cleared_content,
            "storage_type": "core"
        }
    
    async def _clear_all_core_memory(self, agent_id: UUID) -> Dict[str, Any]:
        """Clear all core memory for agent"""
        cleared_sections = []
        if agent_id in CoreMemoryHandler._global_core_memory:
            cleared_sections = list(CoreMemoryHandler._global_core_memory[agent_id].keys())
            CoreMemoryHandler._global_core_memory.pop(agent_id, None)
        
        return {
            "agent_id": str(agent_id),
            "action": "all_cleared",
            "cleared_sections": cleared_sections,
            "sections_count": len(cleared_sections),
            "storage_type": "core"
        }
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "status": "error",
            "output": None,
            "error": error_message,
            "handler": "CoreMemoryHandler"
        }


# Utility functions for core memory

def get_all_core_memory(agent_id: UUID) -> Dict[str, Any]:
    """Get all core memory sections for agent"""
    if hasattr(CoreMemoryHandler, '_global_core_memory'):
        return CoreMemoryHandler._global_core_memory.get(agent_id, {})
    return {}


def get_core_memory_stats() -> Dict[str, Any]:
    """Get statistics about core memory usage"""
    if not hasattr(CoreMemoryHandler, '_global_core_memory'):
        return {"total_agents": 0, "total_sections": 0}
    
    memory_data = CoreMemoryHandler._global_core_memory
    total_sections = sum(len(sections) for sections in memory_data.values())
    
    return {
        "total_agents": len(memory_data),
        "total_sections": total_sections,
        "agents_with_memory": [str(agent_id) for agent_id in memory_data.keys()]
    }


def clear_all_core_memory() -> Dict[str, Any]:
    """Clear all core memory (useful for testing)"""
    if hasattr(CoreMemoryHandler, '_global_core_memory'):
        cleared_agents = len(CoreMemoryHandler._global_core_memory)
        cleared_sections = sum(len(sections) for sections in CoreMemoryHandler._global_core_memory.values())
        CoreMemoryHandler._global_core_memory.clear()
        
        return {
            "cleared_agents": cleared_agents,
            "cleared_sections": cleared_sections
        }
    
    return {"cleared_agents": 0, "cleared_sections": 0}