# app/ai/memories/manager.py

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from app.exceptions.api_exceptions import InvalidDataException
from app.ai.memories.memory_factory import get_memory_registry, create_memory_handler

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Memory Manager using handlers as the single source of truth.
    
    Manages short-term and long-term memory through registered handlers.
    Supports the new configurable memory architecture where users choose
    their memory backends as nodes.
    """

    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema
        self.memory_registry = get_memory_registry()
        
        # Extract configuration
        self.short_term_config = schema.get("short_term", {
            "handler": "BufferMemoryHandler",
            "config": {"window": 6}
        })
        
        self.long_term_config = schema.get("long_term", None)
        
        # Initialize handlers using memory factory
        self.short_term_handler = self._create_memory_handler(self.short_term_config)
        self.long_term_handler = self._create_memory_handler(self.long_term_config) if self.long_term_config else None
        
        # Common parameters
        self.top_k = schema.get("top_k", 5)
        
        logger.debug(f"MemoryManager initialized with short_term: {self.short_term_config['handler']}, "
                    f"long_term: {self.long_term_config['handler'] if self.long_term_config else 'None'}")
    
    def _create_memory_handler(self, config: Dict[str, Any]):
        """Create memory handler instance using memory factory"""
        if not config:
            return None
            
        handler_name = config.get("handler")
        if not handler_name:
            raise InvalidDataException("Handler name is required in memory configuration")
        
        try:
            # Validate handler exists in memory registry
            handler_info = self.memory_registry.get_handler_info(handler_name)
            if not handler_info:
                raise InvalidDataException(f"Memory handler '{handler_name}' not found in memory registry")
            
            # Create handler instance using factory
            handler_config = config.get("config", {})
            handler = create_memory_handler(handler_name, handler_config)
            
            logger.debug(f"Created memory handler: {handler_name} ({handler_info.category.value})")
            return handler
            
        except Exception as e:
            logger.error(f"Failed to create memory handler '{handler_name}': {e}")
            raise InvalidDataException(f"Memory handler creation failed: {e}")

    # SHORT-TERM MEMORY OPERATIONS
    
    async def load_short_term(self, agent_id: UUID) -> List[Dict[str, Any]]:
        """Load short-term memories for agent"""
        if not self.short_term_handler:
            return []
        
        try:
            # Use handler's compatibility method if available
            if hasattr(self.short_term_handler, 'load_short_term'):
                return await self.short_term_handler.load_short_term(agent_id)
            
            # Fallback to execute method
            result = await self.short_term_handler.execute({
                "action": "load",
                "agent_id": str(agent_id)
            })
            
            if result.get("status") == "success":
                output = result.get("output", {})
                return output.get("memories", [])
            else:
                logger.warning(f"Short-term load failed: {result.get('error')}")
                return []
                
        except Exception as e:
            logger.error(f"Error loading short-term memories: {e}")
            return []
    
    async def append_short_term(self, agent_id: UUID, item: Dict[str, Any]) -> None:
        """Append item to short-term memory"""
        if not self.short_term_handler:
            return
        
        try:
            # Use handler's compatibility method if available
            if hasattr(self.short_term_handler, 'append_short_term'):
                window = self.short_term_config.get("config", {}).get("window", 6)
                await self.short_term_handler.append_short_term(agent_id, item, window)
                return
            
            # Fallback to execute method
            params = {
                "action": "append",
                "agent_id": str(agent_id),
                "item": item
            }
            
            # Add config parameters
            config = self.short_term_config.get("config", {})
            params.update(config)
            
            result = await self.short_term_handler.execute(params)
            
            if result.get("status") != "success":
                logger.warning(f"Short-term append failed: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error appending to short-term memory: {e}")
    
    async def clear_short_term(self, agent_id: UUID) -> None:
        """Clear short-term memories for agent"""
        if not self.short_term_handler:
            return
        
        try:
            # Use handler's compatibility method if available
            if hasattr(self.short_term_handler, 'clear_short_term'):
                await self.short_term_handler.clear_short_term(agent_id)
                return
            
            # Fallback to execute method
            result = await self.short_term_handler.execute({
                "action": "clear",
                "agent_id": str(agent_id)
            })
            
            if result.get("status") != "success":
                logger.warning(f"Short-term clear failed: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error clearing short-term memory: {e}")
    
    # LONG-TERM MEMORY OPERATIONS
    
    async def search_long_term(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        """Search long-term memory (without agent context)"""
        if not self.long_term_handler:
            return []
        
        try:
            result = await self.long_term_handler.execute({
                "action": "search",
                "query": query,
                "top_k": top_k or self.top_k
            })
            
            if result.get("status") == "success":
                output = result.get("output", {})
                return output.get("results", [])
            else:
                logger.warning(f"Long-term search failed: {result.get('error')}")
                return []
                
        except Exception as e:
            logger.error(f"Error searching long-term memory: {e}")
            return []
    
    async def retrieve_similar(self, agent_id: UUID, query: str = "", top_k: int = None) -> List[Dict[str, Any]]:
        """Retrieve similar memories for an agent from long-term storage"""
        if not self.long_term_handler:
            return []
        
        try:
            result = await self.long_term_handler.execute({
                "action": "search",
                "agent_id": str(agent_id),
                "query": query,
                "top_k": top_k or self.top_k
            })
            
            if result.get("status") == "success":
                output = result.get("output", {})
                return output.get("results", [])
            else:
                logger.warning(f"Long-term retrieve failed: {result.get('error')}")
                return []
                
        except Exception as e:
            logger.error(f"Error retrieving similar memories: {e}")
            return []
    
    async def store_long_term(self, agent_id: UUID, item: Dict[str, Any]) -> None:
        """Store item in long-term memory"""
        if not self.long_term_handler:
            return
        
        try:
            result = await self.long_term_handler.execute({
                "action": "store",
                "agent_id": str(agent_id),
                "item": item
            })
            
            if result.get("status") != "success":
                logger.warning(f"Long-term store failed: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error storing to long-term memory: {e}")
    
    # UTILITY METHODS
    
    def get_config(self) -> Dict[str, Any]:
        """Get current memory configuration"""
        return {
            "short_term": self.short_term_config,
            "long_term": self.long_term_config,
            "top_k": self.top_k
        }
    
    def has_long_term_memory(self) -> bool:
        """Check if long-term memory is configured"""
        return self.long_term_handler is not None
    
    def get_handler_names(self) -> Dict[str, Optional[str]]:
        """Get names of configured handlers"""
        return {
            "short_term": self.short_term_config.get("handler"),
            "long_term": self.long_term_config.get("handler") if self.long_term_config else None
        }


# Utility functions for memory management

def create_default_memory_schema() -> Dict[str, Any]:
    """Create default memory schema for agents"""
    return {
        "short_term": {
            "handler": "BufferMemoryHandler",
            "config": {"window": 6}
        },
        "long_term": None,  # No long-term memory by default
        "top_k": 5
    }


def create_rag_memory_schema(long_term_handler: str = "PineconeHandler") -> Dict[str, Any]:
    """Create memory schema for RAG-enabled agents"""
    return {
        "short_term": {
            "handler": "RedisMemoryHandler",
            "config": {"window": 10, "ttl": 3600}
        },
        "long_term": {
            "handler": long_term_handler,
            "config": {"top_k": 5}
        },
        "top_k": 5
    }
