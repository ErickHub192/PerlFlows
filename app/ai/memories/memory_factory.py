# app/ai/memories/memory_factory.py
"""
Memory Handler Factory - Registry and management for memory handlers

Provides a centralized system for registering, categorizing, and creating
memory handlers that users can select as nodes for their agents.
"""
import logging
from typing import Dict, List, Type, Any, Optional, Set
from enum import Enum

from app.exceptions.api_exceptions import InvalidDataException

logger = logging.getLogger(__name__)

class MemoryCategory(str, Enum):
    """Categories for memory handlers"""
    SHORT_TERM = "short_term"     # Chat history, session state, recent context
    LONG_TERM = "long_term"       # Documents, knowledge base, RAG/CAG
    CORE = "core"                 # Persistent critical info, always in context
    SPECIALIZED = "specialized"   # Custom memory types (episodic, semantic, etc.)

class MemoryCapability(str, Enum):
    """Capabilities that memory handlers can support"""
    READ = "read"
    WRITE = "write"
    SEARCH = "search"
    APPEND = "append"
    CLEAR = "clear"
    COMPRESS = "compress"
    EXPIRE = "expire"
    VECTORIAL = "vectorial"
    PERSISTENT = "persistent"

class MemoryHandlerInfo:
    """Information about a registered memory handler"""
    
    def __init__(
        self,
        handler_class: Type,
        name: str,
        category: MemoryCategory,
        capabilities: List[MemoryCapability],
        description: str = "",
        requires_credentials: bool = False,
        persistent: bool = True,
        max_storage: Optional[int] = None,
        cost_per_operation: float = 0.0
    ):
        self.handler_class = handler_class
        self.name = name
        self.category = category
        self.capabilities = set(capabilities)
        self.description = description
        self.requires_credentials = requires_credentials
        self.persistent = persistent
        self.max_storage = max_storage
        self.cost_per_operation = cost_per_operation
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "name": self.name,
            "category": self.category.value,
            "capabilities": [cap.value for cap in self.capabilities],
            "description": self.description,
            "requires_credentials": self.requires_credentials,
            "persistent": self.persistent,
            "max_storage": self.max_storage,
            "cost_per_operation": self.cost_per_operation
        }

class MemoryHandlerRegistry:
    """Registry for memory handlers with categorization and filtering"""
    
    def __init__(self):
        self._handlers: Dict[str, MemoryHandlerInfo] = {}
        self._categories: Dict[MemoryCategory, List[str]] = {
            category: [] for category in MemoryCategory
        }
        self._capabilities_index: Dict[MemoryCapability, Set[str]] = {
            capability: set() for capability in MemoryCapability
        }
    
    def register(
        self,
        handler_class: Type,
        name: str,
        category: MemoryCategory,
        capabilities: List[MemoryCapability],
        **kwargs
    ) -> None:
        """Register a memory handler"""
        try:
            # Validate handler class
            if not hasattr(handler_class, 'execute'):
                raise InvalidDataException(f"Handler {name} must implement execute method")
            
            # Create handler info
            handler_info = MemoryHandlerInfo(
                handler_class=handler_class,
                name=name,
                category=category,
                capabilities=capabilities,
                **kwargs
            )
            
            # Check for duplicates
            if name in self._handlers:
                logger.warning(f"Memory handler '{name}' already registered, overwriting")
            
            # Register handler
            self._handlers[name] = handler_info
            
            # Update category index
            if name not in self._categories[category]:
                self._categories[category].append(name)
            
            # Update capabilities index
            for capability in capabilities:
                self._capabilities_index[capability].add(name)
            
            logger.debug(f"Registered memory handler: {name} ({category.value})")
            
        except Exception as e:
            logger.error(f"Failed to register memory handler {name}: {e}")
            raise InvalidDataException(f"Memory handler registration failed: {e}")
    
    def get_handler_class(self, name: str) -> Optional[Type]:
        """Get handler class by name"""
        handler_info = self._handlers.get(name)
        return handler_info.handler_class if handler_info else None
    
    def get_handler_info(self, name: str) -> Optional[MemoryHandlerInfo]:
        """Get handler information by name"""
        return self._handlers.get(name)
    
    def get_by_category(self, category: MemoryCategory) -> List[MemoryHandlerInfo]:
        """Get all handlers in a category"""
        handler_names = self._categories.get(category, [])
        return [self._handlers[name] for name in handler_names]
    
    def get_by_capability(self, capability: MemoryCapability) -> List[MemoryHandlerInfo]:
        """Get all handlers with a specific capability"""
        handler_names = self._capabilities_index.get(capability, set())
        return [self._handlers[name] for name in handler_names]
    
    def search_handlers(
        self,
        category: Optional[MemoryCategory] = None,
        capabilities: Optional[List[MemoryCapability]] = None,
        requires_credentials: Optional[bool] = None,
        persistent: Optional[bool] = None,
        max_cost: Optional[float] = None
    ) -> List[MemoryHandlerInfo]:
        """Search handlers by criteria"""
        results = list(self._handlers.values())
        
        # Filter by category
        if category:
            results = [h for h in results if h.category == category]
        
        # Filter by capabilities (must have ALL specified capabilities)
        if capabilities:
            capability_set = set(capabilities)
            results = [h for h in results if capability_set.issubset(h.capabilities)]
        
        # Filter by credentials requirement
        if requires_credentials is not None:
            results = [h for h in results if h.requires_credentials == requires_credentials]
        
        # Filter by persistence
        if persistent is not None:
            results = [h for h in results if h.persistent == persistent]
        
        # Filter by cost
        if max_cost is not None:
            results = [h for h in results if h.cost_per_operation <= max_cost]
        
        return results
    
    def list_all(self) -> List[MemoryHandlerInfo]:
        """List all registered handlers"""
        return list(self._handlers.values())
    
    def get_categories_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get summary of handlers by category"""
        summary = {}
        for category in MemoryCategory:
            handlers = self.get_by_category(category)
            summary[category.value] = {
                "count": len(handlers),
                "handlers": [h.name for h in handlers],
                "capabilities": list(set().union(*[h.capabilities for h in handlers]))
            }
        return summary
    
    def create_handler(self, name: str, config: Dict[str, Any] = None) -> Any:
        """Create handler instance"""
        handler_info = self.get_handler_info(name)
        if not handler_info:
            raise InvalidDataException(f"Memory handler '{name}' not found")
        
        try:
            # Create handler with config as credentials
            handler = handler_info.handler_class(creds=config or {})
            logger.debug(f"Created memory handler instance: {name}")
            return handler
            
        except Exception as e:
            logger.error(f"Failed to create memory handler {name}: {e}")
            raise InvalidDataException(f"Memory handler creation failed: {e}")

# Global registry instance
_memory_registry = MemoryHandlerRegistry()

# Decorator functions for easy registration

def register_memory_handler(
    name: str,
    category: MemoryCategory,
    capabilities: List[MemoryCapability],
    **kwargs
):
    """Decorator to register a memory handler"""
    def decorator(handler_class: Type):
        _memory_registry.register(
            handler_class=handler_class,
            name=name,
            category=category,
            capabilities=capabilities,
            **kwargs
        )
        return handler_class
    return decorator

def register_short_term_memory(
    name: str,
    capabilities: List[MemoryCapability] = None,
    **kwargs
):
    """Decorator for short-term memory handlers"""
    if capabilities is None:
        capabilities = [MemoryCapability.READ, MemoryCapability.WRITE, MemoryCapability.CLEAR]
    
    return register_memory_handler(
        name=name,
        category=MemoryCategory.SHORT_TERM,
        capabilities=capabilities,
        **kwargs
    )

def register_long_term_memory(
    name: str,
    capabilities: List[MemoryCapability] = None,
    **kwargs
):
    """Decorator for long-term memory handlers"""
    if capabilities is None:
        capabilities = [MemoryCapability.READ, MemoryCapability.WRITE, MemoryCapability.SEARCH]
    
    return register_memory_handler(
        name=name,
        category=MemoryCategory.LONG_TERM,
        capabilities=capabilities,
        **kwargs
    )

def register_core_memory(
    name: str,
    capabilities: List[MemoryCapability] = None,
    **kwargs
):
    """Decorator for core memory handlers"""
    if capabilities is None:
        capabilities = [MemoryCapability.READ, MemoryCapability.WRITE, MemoryCapability.PERSISTENT]
    
    return register_memory_handler(
        name=name,
        category=MemoryCategory.CORE,
        capabilities=capabilities,
        **kwargs
    )

def register_specialized_memory(
    name: str,
    capabilities: List[MemoryCapability],
    **kwargs
):
    """Decorator for specialized memory handlers"""
    return register_memory_handler(
        name=name,
        category=MemoryCategory.SPECIALIZED,
        capabilities=capabilities,
        **kwargs
    )

# Public API functions

def get_memory_registry() -> MemoryHandlerRegistry:
    """Get the global memory handler registry"""
    return _memory_registry

def get_available_memory_handlers() -> List[Dict[str, Any]]:
    """Get list of all available memory handlers for API"""
    return [handler.to_dict() for handler in _memory_registry.list_all()]

def get_memory_handlers_by_category(category: str) -> List[Dict[str, Any]]:
    """Get memory handlers by category for API"""
    try:
        cat = MemoryCategory(category)
        handlers = _memory_registry.get_by_category(cat)
        return [handler.to_dict() for handler in handlers]
    except ValueError:
        return []

def create_memory_handler(name: str, config: Dict[str, Any] = None):
    """Create memory handler instance"""
    return _memory_registry.create_handler(name, config)

def search_memory_handlers(
    category: Optional[str] = None,
    capabilities: Optional[List[str]] = None,
    **filters
) -> List[Dict[str, Any]]:
    """Search memory handlers with filters"""
    # Convert string parameters to enums
    cat = MemoryCategory(category) if category else None
    caps = [MemoryCapability(cap) for cap in capabilities] if capabilities else None
    
    handlers = _memory_registry.search_handlers(
        category=cat,
        capabilities=caps,
        **filters
    )
    
    return [handler.to_dict() for handler in handlers]

# Utility functions

def validate_memory_config(config: Dict[str, Any]) -> List[str]:
    """Validate memory configuration and return list of errors"""
    errors = []
    
    if not isinstance(config, dict):
        errors.append("Memory config must be a dictionary")
        return errors
    
    # Validate short_term config
    short_term = config.get("short_term")
    if short_term:
        if not isinstance(short_term, dict):
            errors.append("short_term config must be a dictionary")
        else:
            handler_name = short_term.get("handler")
            if not handler_name:
                errors.append("short_term handler name is required")
            elif not _memory_registry.get_handler_info(handler_name):
                errors.append(f"short_term handler '{handler_name}' not found")
    
    # Validate long_term config
    long_term = config.get("long_term")
    if long_term:
        if not isinstance(long_term, dict):
            errors.append("long_term config must be a dictionary")
        else:
            handler_name = long_term.get("handler")
            if not handler_name:
                errors.append("long_term handler name is required")
            elif not _memory_registry.get_handler_info(handler_name):
                errors.append(f"long_term handler '{handler_name}' not found")
    
    return errors

def get_memory_categories_summary() -> Dict[str, Any]:
    """Get summary of memory categories for API"""
    return _memory_registry.get_categories_summary()