# app/handlers/episodic_memory_handler.py
"""
Episodic Memory Handler - Events and temporal experiences
Refactored to work independently without legacy memory services
"""
import time
import math
import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, timedelta

from .connector_handler import ActionHandler
from app.connectors.factory import register_tool, register_node
from app.exceptions.api_exceptions import InvalidDataException
from app.ai.memories.memory_factory import register_specialized_memory, MemoryCapability

logger = logging.getLogger(__name__)

@register_node("EpisodicMemoryHandler")
@register_tool("EpisodicMemoryHandler")
@register_specialized_memory(
    name="EpisodicMemoryHandler",
    capabilities=[
        MemoryCapability.READ,
        MemoryCapability.WRITE,
        MemoryCapability.SEARCH,
        MemoryCapability.COMPRESS
    ],
    description="Store and retrieve specific events with temporal decay and importance scoring",
    requires_credentials=False,
    persistent=False,  # Currently in-memory
    max_storage=1000,  # Max episodes per agent
    cost_per_operation=0.002  # Slightly higher for processing
)
class EpisodicMemoryHandler(ActionHandler):
    """
    Episodic memory handler - Events and specific experiences
    
    Manages temporal memory with decay, emotion, and importance scoring.
    Inspired by human episodic memory - remembers specific events that
    fade over time unless they are important or frequently accessed.
    """
    
    metadata = {
        "type": "tool",
        "category": "memory",
        "description": "Store and retrieve specific events with temporal decay",
        "capabilities": ["store", "retrieve", "consolidate", "search"],
        "storage_type": "episodic",
        "persistent": False,
        "max_content_length": 5000
    }
    
    def __init__(self, creds: Dict[str, Any] = None):
        super().__init__(creds or {})
        # Global episodic memory storage - shared across instances
        if not hasattr(EpisodicMemoryHandler, '_global_episodes'):
            EpisodicMemoryHandler._global_episodes: Dict[UUID, List[Dict[str, Any]]] = {}

    async def execute(
        self,
        params: Dict[str, Any],
        creds: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute episodic memory operation"""
        start_time = time.perf_counter()
        
        try:
            # Validate parameters
            validation_error = self._validate_params(params)
            if validation_error:
                return self._create_error_response(validation_error)
            
            # Extract parameters
            action = params.get("action")
            agent_id = UUID(str(params.get("agent_id")))
            
            # Execute action
            if action == "store":
                event = params.get("event")
                result = await self._store_episode(agent_id, event)
            elif action == "retrieve":
                query = params.get("query", "")
                time_window = params.get("time_window", 168)  # 1 week default
                top_k = params.get("top_k", 10)
                result = await self._retrieve_episodes(agent_id, query, time_window, top_k)
            elif action == "search":
                query = params.get("query", "")
                importance_threshold = params.get("importance_threshold", 0.3)
                result = await self._search_episodes(agent_id, query, importance_threshold)
            elif action == "consolidate":
                result = await self._consolidate_episodes(agent_id)
            else:
                return self._create_error_response(f"Unknown action: {action}")
            
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            
            return {
                "status": "success",
                "output": result,
                "duration_ms": duration_ms,
                "handler": "EpisodicMemoryHandler",
                "agent_id": str(agent_id)
            }
            
        except Exception as e:
            logger.error(f"EpisodicMemoryHandler execution error: {e}", exc_info=True)
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return {
                "status": "error",
                "output": None,
                "error": str(e),
                "duration_ms": duration_ms,
                "handler": "EpisodicMemoryHandler"
            }
    
    def _validate_params(self, params: Dict[str, Any]) -> Optional[str]:
        """Validate parameters for episodic memory operations"""
        if not isinstance(params, dict):
            return "Parameters must be a dictionary"
        
        # Validate action
        action = params.get("action")
        if not action:
            return "action is required (store, retrieve, search, consolidate)"
        
        if action not in ["store", "retrieve", "search", "consolidate"]:
            return f"Invalid action: {action}. Must be store, retrieve, search, or consolidate"
        
        # Validate agent_id
        agent_id = params.get("agent_id")
        if not agent_id:
            return "agent_id is required"
        
        try:
            UUID(str(agent_id))
        except (ValueError, TypeError):
            return f"Invalid agent_id format: {agent_id}"
        
        # Validate store-specific parameters
        if action == "store":
            event = params.get("event")
            if not event or not isinstance(event, dict):
                return "event data is required for store action"
            
            content = event.get("content")
            if not content:
                return "event content is required"
            
            if len(str(content)) > self.metadata["max_content_length"]:
                return f"Event content too long. Max {self.metadata['max_content_length']} characters"
        
        return None

    async def _store_episode(self, agent_id: UUID, event: Dict[str, Any]) -> Dict[str, Any]:
        """Store episodic memory event"""
        if agent_id not in EpisodicMemoryHandler._global_episodes:
            EpisodicMemoryHandler._global_episodes[agent_id] = []
        
        # Create episode with metadata
        episode = {
            "id": f"ep_{int(time.time() * 1000)}_{len(EpisodicMemoryHandler._global_episodes[agent_id])}",
            "content": str(event.get("content", "")),
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "importance": self._calculate_importance(event),
            "emotion": event.get("emotion", "neutral"),
            "tags": self._extract_tags(event),
            "context": event.get("context", {}),
            "access_count": 0,
            "last_accessed": time.time()
        }
        
        # Add to memory
        episodes = EpisodicMemoryHandler._global_episodes[agent_id]
        episodes.append(episode)
        
        # Limit memory size (keep most recent + most important)
        max_episodes = 1000
        if len(episodes) > max_episodes:
            # Sort by importance and recency
            episodes.sort(key=lambda e: (e["importance"], e["timestamp"]), reverse=True)
            EpisodicMemoryHandler._global_episodes[agent_id] = episodes[:max_episodes]
        
        return {
            "episode_id": episode["id"],
            "stored_content": episode["content"],
            "importance": episode["importance"],
            "tags": episode["tags"],
            "total_episodes": len(EpisodicMemoryHandler._global_episodes[agent_id]),
            "agent_id": str(agent_id),
            "storage_type": "episodic"
        }
    
    async def _retrieve_episodes(
        self, 
        agent_id: UUID, 
        query: str, 
        time_window_hours: int,
        top_k: int
    ) -> Dict[str, Any]:
        """Retrieve episodes within time window, optionally filtered by query"""
        episodes = EpisodicMemoryHandler._global_episodes.get(agent_id, [])
        
        if not episodes:
            return {
                "episodes": [],
                "count": 0,
                "agent_id": str(agent_id),
                "query": query,
                "time_window_hours": time_window_hours
            }
        
        # Filter by time window
        now = time.time()
        time_threshold = now - (time_window_hours * 3600)
        recent_episodes = [ep for ep in episodes if ep["timestamp"] >= time_threshold]
        
        # Apply decay factor to importance
        for episode in recent_episodes:
            episode["current_importance"] = self._apply_decay(episode)
        
        # Filter by query if provided
        if query and query.strip():
            query_lower = query.lower()
            filtered_episodes = []
            for episode in recent_episodes:
                # Simple text matching - could be enhanced with semantic search
                content_lower = episode["content"].lower()
                tags_lower = [tag.lower() for tag in episode["tags"]]
                
                if (query_lower in content_lower or 
                    any(query_lower in tag for tag in tags_lower)):
                    filtered_episodes.append(episode)
            recent_episodes = filtered_episodes
        
        # Sort by current importance (with decay)
        recent_episodes.sort(key=lambda e: e["current_importance"], reverse=True)
        
        # Limit results
        result_episodes = recent_episodes[:top_k]
        
        # Update access count for retrieved episodes
        for episode in result_episodes:
            episode["access_count"] += 1
            episode["last_accessed"] = now
        
        return {
            "episodes": [self._format_episode_for_output(ep) for ep in result_episodes],
            "count": len(result_episodes),
            "total_in_timeframe": len(recent_episodes),
            "agent_id": str(agent_id),
            "query": query,
            "time_window_hours": time_window_hours,
            "storage_type": "episodic"
        }
    
    async def _search_episodes(
        self, 
        agent_id: UUID, 
        query: str,
        importance_threshold: float
    ) -> Dict[str, Any]:
        """Search episodes by content with importance filtering"""
        episodes = EpisodicMemoryHandler._global_episodes.get(agent_id, [])
        
        if not episodes or not query.strip():
            return {
                "episodes": [],
                "count": 0,
                "agent_id": str(agent_id),
                "query": query
            }
        
        query_lower = query.lower()
        matching_episodes = []
        
        for episode in episodes:
            # Apply decay to get current importance
            current_importance = self._apply_decay(episode)
            
            # Filter by importance threshold
            if current_importance < importance_threshold:
                continue
            
            # Search in content and tags
            content_lower = episode["content"].lower()
            tags_lower = [tag.lower() for tag in episode["tags"]]
            
            if (query_lower in content_lower or 
                any(query_lower in tag for tag in tags_lower)):
                episode["current_importance"] = current_importance
                matching_episodes.append(episode)
        
        # Sort by current importance
        matching_episodes.sort(key=lambda e: e["current_importance"], reverse=True)
        
        return {
            "episodes": [self._format_episode_for_output(ep) for ep in matching_episodes],
            "count": len(matching_episodes),
            "agent_id": str(agent_id),
            "query": query,
            "importance_threshold": importance_threshold,
            "storage_type": "episodic"
        }
    
    async def _consolidate_episodes(self, agent_id: UUID) -> Dict[str, Any]:
        """Consolidate old episodes by removing low-importance ones"""
        episodes = EpisodicMemoryHandler._global_episodes.get(agent_id, [])
        
        if not episodes:
            return {
                "consolidated": 0,
                "remaining": 0,
                "agent_id": str(agent_id)
            }
        
        original_count = len(episodes)
        
        # Apply decay and filter out very low importance episodes
        current_time = time.time()
        consolidated_episodes = []
        
        for episode in episodes:
            current_importance = self._apply_decay(episode)
            
            # Keep episode if:
            # 1. High current importance (>0.3)
            # 2. Recently accessed
            # 3. Within last 24 hours regardless of importance
            age_hours = (current_time - episode["timestamp"]) / 3600
            recently_accessed = (current_time - episode["last_accessed"]) < 86400  # 24h
            
            if (current_importance > 0.3 or 
                recently_accessed or 
                age_hours < 24):
                consolidated_episodes.append(episode)
        
        # Update memory
        EpisodicMemoryHandler._global_episodes[agent_id] = consolidated_episodes
        
        return {
            "consolidated": original_count - len(consolidated_episodes),
            "remaining": len(consolidated_episodes),
            "original_count": original_count,
            "agent_id": str(agent_id),
            "storage_type": "episodic"
        }
    
    def _calculate_importance(self, event: Dict[str, Any]) -> float:
        """Calculate importance score for an event"""
        importance = 0.5  # Base importance
        
        content = str(event.get("content", ""))
        emotion = event.get("emotion", "neutral")
        context = event.get("context", {})
        
        # Content-based factors
        if len(content) > 100:
            importance += 0.1
        
        # Emotional intensity
        emotional_weights = {
            "strong_positive": 0.3,
            "strong_negative": 0.3,
            "positive": 0.1,
            "negative": 0.1,
            "excited": 0.2,
            "angry": 0.2,
            "sad": 0.1,
            "neutral": 0.0
        }
        importance += emotional_weights.get(emotion, 0.0)
        
        # Keyword importance
        important_keywords = [
            "important", "critical", "urgent", "remember", "key", "essential",
            "decision", "breakthrough", "achievement", "problem", "issue"
        ]
        
        content_lower = content.lower()
        for keyword in important_keywords:
            if keyword in content_lower:
                importance += 0.15
                break
        
        # Context factors
        if context.get("user_marked_important"):
            importance += 0.3
        
        if context.get("contains_people"):
            importance += 0.1
        
        if context.get("work_related"):
            importance += 0.1
        
        # Clamp to valid range
        return max(0.0, min(1.0, importance))
    
    def _extract_tags(self, event: Dict[str, Any]) -> List[str]:
        """Extract tags from event content and metadata"""
        tags = []
        content = str(event.get("content", ""))
        emotion = event.get("emotion", "neutral")
        context = event.get("context", {})
        
        # Add emotion tag
        if emotion != "neutral":
            tags.append(f"emotion:{emotion}")
        
        # Extract content-based tags
        content_lower = content.lower()
        
        # Topic tags
        topics = {
            "work": ["work", "project", "meeting", "task", "deadline"],
            "personal": ["family", "friend", "personal", "home"],
            "learning": ["learn", "study", "course", "book", "tutorial"],
            "decision": ["decide", "choice", "option", "consider"],
            "problem": ["problem", "issue", "bug", "error", "fix"]
        }
        
        for topic, keywords in topics.items():
            if any(keyword in content_lower for keyword in keywords):
                tags.append(f"topic:{topic}")
        
        # Context tags
        if context.get("work_related"):
            tags.append("context:work")
        
        if context.get("contains_people"):
            tags.append("context:social")
        
        # Remove duplicates
        return list(set(tags))
    
    def _apply_decay(self, episode: Dict[str, Any]) -> float:
        """Apply temporal decay to episode importance"""
        current_time = time.time()
        age_hours = (current_time - episode["timestamp"]) / 3600
        base_importance = episode["importance"]
        access_count = episode.get("access_count", 0)
        
        # Decay function: importance * e^(-age/decay_rate)
        # More accessed episodes decay slower
        decay_rate = 168 + (access_count * 24)  # Base 1 week + 1 day per access
        
        decay_factor = math.exp(-age_hours / decay_rate)
        current_importance = base_importance * decay_factor
        
        # Boost for recently accessed episodes
        time_since_access = current_time - episode.get("last_accessed", episode["timestamp"])
        if time_since_access < 3600:  # Accessed within last hour
            current_importance *= 1.2
        
        return min(1.0, current_importance)
    
    def _format_episode_for_output(self, episode: Dict[str, Any]) -> Dict[str, Any]:
        """Format episode for API output"""
        return {
            "id": episode["id"],
            "content": episode["content"],
            "timestamp": episode["timestamp"],
            "datetime": episode["datetime"],
            "importance": episode["importance"],
            "current_importance": episode.get("current_importance", episode["importance"]),
            "emotion": episode["emotion"],
            "tags": episode["tags"],
            "access_count": episode["access_count"],
            "age_hours": (time.time() - episode["timestamp"]) / 3600
        }
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "status": "error",
            "output": None,
            "error": error_message,
            "handler": "EpisodicMemoryHandler"
        }


# Utility functions for episodic memory

def get_agent_episodes(agent_id: UUID) -> List[Dict[str, Any]]:
    """Get all episodes for an agent"""
    if hasattr(EpisodicMemoryHandler, '_global_episodes'):
        return EpisodicMemoryHandler._global_episodes.get(agent_id, [])
    return []

def get_episodic_memory_stats() -> Dict[str, Any]:
    """Get statistics about episodic memory usage"""
    if not hasattr(EpisodicMemoryHandler, '_global_episodes'):
        return {"total_agents": 0, "total_episodes": 0}
    
    memory_data = EpisodicMemoryHandler._global_episodes
    total_episodes = sum(len(episodes) for episodes in memory_data.values())
    
    return {
        "total_agents": len(memory_data),
        "total_episodes": total_episodes,
        "agents_with_episodes": [str(agent_id) for agent_id in memory_data.keys()],
        "avg_episodes_per_agent": total_episodes / len(memory_data) if memory_data else 0
    }

def clear_all_episodic_memory() -> Dict[str, Any]:
    """Clear all episodic memory (useful for testing)"""
    if hasattr(EpisodicMemoryHandler, '_global_episodes'):
        cleared_agents = len(EpisodicMemoryHandler._global_episodes)
        cleared_episodes = sum(len(episodes) for episodes in EpisodicMemoryHandler._global_episodes.values())
        EpisodicMemoryHandler._global_episodes.clear()
        
        return {
            "cleared_agents": cleared_agents,
            "cleared_episodes": cleared_episodes
        }
    
    return {"cleared_agents": 0, "cleared_episodes": 0}