# app/handlers/base_memory_handler.py
"""
Base class for all memory handlers providing common functionality
"""
import time
import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from abc import ABC, abstractmethod

from .connector_handler import ActionHandler
from app.exceptions.api_exceptions import InvalidDataException

logger = logging.getLogger(__name__)

class BaseMemoryHandler(ActionHandler, ABC):
    """
    Base class for all memory handlers providing:
    - Common memory service initialization
    - Standardized error handling
    - Logging and metrics
    - Parameter validation
    """
    
    def __init__(self, creds: Dict[str, Any] = None):
        super().__init__(creds or {})
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Lazy initialization - override in subclasses if needed"""
        if not self._initialized:
            self._initialized = True
            logger.debug(f"Initialized {self.__class__.__name__}")
    
    async def execute(
        self,
        params: Dict[str, Any],
        creds: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Standard execute method that all memory handlers must implement
        Provides common initialization, error handling, and logging
        """
        start_time = time.perf_counter()
        handler_name = self.__class__.__name__
        
        try:
            # Ensure memory service is initialized
            await self._ensure_initialized()
            
            # Validate required parameters
            validation_error = self._validate_params(params)
            if validation_error:
                return {
                    "status": "error",
                    "output": None,
                    "error": validation_error,
                    "duration_ms": int((time.perf_counter() - start_time) * 1000),
                    "handler": handler_name
                }
            
            # Extract common parameters
            agent_id = self._extract_agent_id(params)
            
            # Call the specific handler implementation
            result = await self._handle_memory_operation(params, agent_id)
            
            # Wrap result in standard format
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            
            return {
                "status": "success",
                "output": result,
                "duration_ms": duration_ms,
                "handler": handler_name,
                "agent_id": str(agent_id) if agent_id else None
            }
            
        except InvalidDataException as e:
            logger.warning(f"{handler_name} validation error: {e}")
            return {
                "status": "error",
                "output": None,
                "error": str(e),
                "duration_ms": int((time.perf_counter() - start_time) * 1000),
                "handler": handler_name
            }
            
        except Exception as e:
            logger.error(f"{handler_name} execution error: {e}", exc_info=True)
            return {
                "status": "error",
                "output": None,
                "error": f"Internal error: {str(e)}",
                "duration_ms": int((time.perf_counter() - start_time) * 1000),
                "handler": handler_name
            }
    
    def _validate_params(self, params: Dict[str, Any]) -> Optional[str]:
        """
        Validate common parameters
        Returns error message if validation fails, None if valid
        """
        if not isinstance(params, dict):
            return "Parameters must be a dictionary"
        
        # Validate agent_id if present
        agent_id_param = params.get("agent_id")
        if agent_id_param:
            try:
                UUID(str(agent_id_param))
            except (ValueError, TypeError):
                return f"Invalid agent_id format: {agent_id_param}"
        
        # Call handler-specific validation
        return self._validate_handler_params(params)
    
    def _extract_agent_id(self, params: Dict[str, Any]) -> Optional[UUID]:
        """Extract and validate agent_id from parameters"""
        agent_id_param = params.get("agent_id")
        if agent_id_param:
            try:
                return UUID(str(agent_id_param))
            except (ValueError, TypeError):
                raise InvalidDataException(f"Invalid agent_id format: {agent_id_param}")
        return None
    
    def _validate_handler_params(self, params: Dict[str, Any]) -> Optional[str]:
        """
        Handler-specific parameter validation
        Override in subclasses to add custom validation
        Returns error message if validation fails, None if valid
        """
        return None
    
    @abstractmethod
    async def _handle_memory_operation(
        self, 
        params: Dict[str, Any], 
        agent_id: Optional[UUID]
    ) -> Dict[str, Any]:
        """
        Handler-specific memory operation implementation
        Must be implemented by all memory handlers
        
        Args:
            params: Validated parameters
            agent_id: Extracted and validated agent ID (may be None)
            
        Returns:
            Dictionary with operation result
        """
        pass
    
    def _create_success_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to create standardized success response"""
        return {
            "success": True,
            "data": data,
            "timestamp": time.time()
        }
    
    def _create_error_response(self, error_message: str, error_code: str = "MEMORY_ERROR") -> Dict[str, Any]:
        """Helper to create standardized error response"""
        return {
            "success": False,
            "error": {
                "message": error_message,
                "code": error_code
            },
            "timestamp": time.time()
        }
    
    async def _get_agent_context(self, agent_id: UUID) -> Dict[str, Any]:
        """
        Get agent context information for memory operations
        Useful for personalizing memory operations
        """
        try:
            # For now, just return basic context
            # In the future, this could fetch agent configuration, preferences, etc.
            return {
                "agent_id": str(agent_id),
                "context_type": "basic"
            }
        except Exception as e:
            logger.warning(f"Failed to get agent context: {e}")
            return {"agent_id": str(agent_id), "context_type": "fallback"}
    
    async def _log_memory_operation(
        self, 
        operation: str, 
        agent_id: Optional[UUID], 
        params: Dict[str, Any],
        result: Dict[str, Any]
    ):
        """Log memory operation for debugging and analytics"""
        try:
            log_data = {
                "operation": operation,
                "handler": self.__class__.__name__,
                "agent_id": str(agent_id) if agent_id else "unknown",
                "params_keys": list(params.keys()),
                "success": result.get("success", False),
                "timestamp": time.time()
            }
            
            logger.info(f"Memory operation completed: {log_data}")
            
        except Exception as e:
            logger.warning(f"Failed to log memory operation: {e}")


class AgentRequiredMemoryHandler(BaseMemoryHandler):
    """
    Base class for memory handlers that require an agent_id
    """
    
    def _validate_handler_params(self, params: Dict[str, Any]) -> Optional[str]:
        """Validate that agent_id is present"""
        if not params.get("agent_id"):
            return "agent_id is required for this memory operation"
        return super()._validate_handler_params(params)


class GlobalMemoryHandler(BaseMemoryHandler):
    """
    Base class for memory handlers that operate globally (without agent context)
    """
    
    def _validate_handler_params(self, params: Dict[str, Any]) -> Optional[str]:
        """Global handlers don't require agent_id"""
        return super()._validate_handler_params(params)


# Utility functions for memory handlers

def format_memory_content(content: str, max_length: int = 1000) -> str:
    """Format memory content for storage"""
    if not content:
        return ""
    
    # Truncate if too long
    if len(content) > max_length:
        return content[:max_length - 3] + "..."
    
    return content.strip()


def calculate_memory_importance(
    content: str, 
    context: Dict[str, Any] = None
) -> float:
    """
    Calculate importance score for memory content
    Returns float between 0.0 and 1.0
    """
    if not content:
        return 0.0
    
    importance = 0.5  # Base importance
    
    # Length factor
    if len(content) > 500:
        importance += 0.1
    elif len(content) < 50:
        importance -= 0.1
    
    # Keyword factors
    important_keywords = ["important", "remember", "critical", "urgent", "todo"]
    for keyword in important_keywords:
        if keyword.lower() in content.lower():
            importance += 0.1
            break
    
    # Context factors
    if context:
        if context.get("emotion") == "strong":
            importance += 0.2
        if context.get("user_marked_important"):
            importance += 0.3
    
    # Clamp to valid range
    return max(0.0, min(1.0, importance))


def extract_memory_tags(content: str, metadata: Dict[str, Any] = None) -> List[str]:
    """Extract relevant tags from memory content"""
    tags = []
    
    # Extract from metadata if available
    if metadata and "tags" in metadata:
        tags.extend(metadata["tags"])
    
    # Extract from content
    content_lower = content.lower()
    
    # Emotion tags
    emotions = ["happy", "sad", "angry", "excited", "frustrated", "confused"]
    for emotion in emotions:
        if emotion in content_lower:
            tags.append(f"emotion:{emotion}")
    
    # Topic tags
    topics = ["work", "personal", "learning", "planning", "decision"]
    for topic in topics:
        if topic in content_lower:
            tags.append(f"topic:{topic}")
    
    # Remove duplicates
    return list(set(tags))