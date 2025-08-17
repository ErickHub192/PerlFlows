# app/handlers/memory_search_handler.py
"""
Memory search handler - Replace hardcoded RAG with intelligent memory search
This handler allows agents to search their memory when needed, instead of automatic injection
"""
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, timedelta

from .base_memory_handler import AgentRequiredMemoryHandler
from app.connectors.factory import register_tool, register_node

@register_node("MemorySearchHandler")
@register_tool("MemorySearchHandler")
class MemorySearchHandler(AgentRequiredMemoryHandler):
    """
    Memory search handler - Intelligent memory retrieval
    Allows agents to search their memory on demand instead of hardcoded RAG injection
    """
    
    metadata = {
        "type": "tool",
        "category": "memory",
        "subcategory": "search",
        "auto_select": True,
        "priority": 1,
        "description": "Search agent memory with various strategies and filters", 
        "capabilities": ["semantic_search", "temporal_search", "filtered_search", "recent_memories"],
        "search_strategies": ["semantic", "temporal", "hybrid", "recent", "importance"],
        "use_cases": ["question_answering", "context_retrieval", "conversation_history"],
        "default_strategy": "semantic",
        "conflicts_with": []
    }
    
    def _validate_handler_params(self, params: Dict[str, Any]) -> Optional[str]:
        """Validate memory search specific parameters"""
        # First validate agent requirement
        base_error = super()._validate_handler_params(params)
        if base_error:
            return base_error
        
        # Validate search strategy
        strategy = params.get("strategy", "semantic")
        valid_strategies = self.metadata["search_strategies"]
        if strategy not in valid_strategies:
            return f"Invalid search strategy: {strategy}. Must be one of {valid_strategies}"
        
        # Validate parameters based on strategy
        if strategy == "semantic":
            query = params.get("query")
            if not query:
                return "query is required for semantic search"
        
        elif strategy == "temporal":
            # Either date range or relative time required
            start_date = params.get("start_date")
            end_date = params.get("end_date")
            days_back = params.get("days_back")
            
            if not any([start_date, end_date, days_back]):
                return "temporal search requires start_date, end_date, or days_back parameter"
        
        elif strategy == "hybrid":
            query = params.get("query")
            if not query:
                return "query is required for hybrid search"
        
        # Validate numeric parameters
        top_k = params.get("top_k", 5)
        if not isinstance(top_k, int) or top_k < 1 or top_k > 100:
            return "top_k must be an integer between 1 and 100"
        
        return None
    
    async def _handle_memory_operation(
        self, 
        params: Dict[str, Any], 
        agent_id: UUID
    ) -> Dict[str, Any]:
        """Handle memory search operations"""
        strategy = params.get("strategy", "semantic")
        
        # Log the operation
        await self._log_memory_operation(f"memory_search_{strategy}", agent_id, params, {})
        
        if strategy == "semantic":
            return await self._semantic_search(params, agent_id)
        
        elif strategy == "temporal":
            return await self._temporal_search(params, agent_id)
        
        elif strategy == "hybrid":
            return await self._hybrid_search(params, agent_id)
        
        elif strategy == "recent":
            return await self._recent_memories(params, agent_id)
        
        elif strategy == "importance":
            return await self._importance_search(params, agent_id)
        
        else:
            return self._create_error_response(f"Unknown strategy: {strategy}", "INVALID_STRATEGY")
    
    async def _semantic_search(self, params: Dict[str, Any], agent_id: UUID) -> Dict[str, Any]:
        """Perform semantic search using embeddings"""
        try:
            query = params["query"]
            top_k = params.get("top_k", 5)
            memory_types = params.get("memory_types", None)  # Filter by memory type
            min_importance = params.get("min_importance", None)
            
            # Perform semantic search
            memories = await self.memory_service.retrieve_similar(
                agent_id=agent_id,
                query=query,
                top_k=top_k * 2  # Get more to apply filters
            )
            
            # Apply filters
            filtered_memories = self._apply_filters(
                memories, 
                memory_types=memory_types,
                min_importance=min_importance
            )
            
            # Limit to requested count
            final_memories = filtered_memories[:top_k]
            
            return self._create_success_response({
                "strategy": "semantic",
                "query": query,
                "memories_found": len(final_memories),
                "total_before_filters": len(memories),
                "memories": self._format_memories_for_response(final_memories),
                "search_metadata": {
                    "semantic_similarity": True,
                    "embedding_based": True,
                    "filtered": bool(memory_types or min_importance is not None)
                }
            })
            
        except Exception as e:
            return self._create_error_response(f"Semantic search failed: {str(e)}", "SEMANTIC_SEARCH_ERROR")
    
    async def _temporal_search(self, params: Dict[str, Any], agent_id: UUID) -> Dict[str, Any]:
        """Search memories by time range"""
        try:
            top_k = params.get("top_k", 5)
            
            # Parse time parameters
            start_date, end_date = self._parse_temporal_params(params)
            
            # Get all memories for the agent (we'll filter by time)
            all_memories = await self.memory_service.list_memories_by_agent(
                agent_id=agent_id,
                limit=1000  # Get a large set to filter from
            )
            
            # Filter by time range
            filtered_memories = []
            for memory in all_memories:
                memory_time = getattr(memory, 'created_at', None)
                if memory_time:
                    if start_date <= memory_time <= end_date:
                        filtered_memories.append({
                            "content": memory.content,
                            "metadata": getattr(memory, 'metadatas', {}),
                            "created_at": memory_time.isoformat() if memory_time else None
                        })
            
            # Sort by recency and limit
            filtered_memories.sort(
                key=lambda m: m.get("created_at", ""), 
                reverse=True
            )
            final_memories = filtered_memories[:top_k]
            
            return self._create_success_response({
                "strategy": "temporal",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "memories_found": len(final_memories),
                "memories": final_memories,
                "search_metadata": {
                    "temporal_range": True,
                    "chronological_order": True
                }
            })
            
        except Exception as e:
            return self._create_error_response(f"Temporal search failed: {str(e)}", "TEMPORAL_SEARCH_ERROR")
    
    async def _hybrid_search(self, params: Dict[str, Any], agent_id: UUID) -> Dict[str, Any]:
        """Combine semantic and temporal search"""
        try:
            query = params["query"]
            top_k = params.get("top_k", 5)
            time_weight = params.get("time_weight", 0.3)  # How much to weight recency
            semantic_weight = 1.0 - time_weight
            
            # Get semantic results
            semantic_memories = await self.memory_service.retrieve_similar(
                agent_id=agent_id,
                query=query,
                top_k=top_k * 3  # Get more for hybrid scoring
            )
            
            # Apply hybrid scoring
            scored_memories = []
            current_time = datetime.utcnow()
            
            for i, memory in enumerate(semantic_memories):
                # Semantic score (based on position in results)
                semantic_score = (len(semantic_memories) - i) / len(semantic_memories)
                
                # Temporal score (recency)
                try:
                    metadata = memory.get("metadata", {})
                    timestamp = metadata.get("timestamp")
                    if timestamp:
                        if isinstance(timestamp, str):
                            memory_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        else:
                            memory_time = timestamp
                        
                        # Calculate recency score (newer = higher score)
                        days_old = (current_time - memory_time).days
                        temporal_score = max(0, 1.0 - (days_old / 365))  # Score decreases over a year
                    else:
                        temporal_score = 0.5  # Default score for unknown timestamps
                except:
                    temporal_score = 0.5
                
                # Combined score
                hybrid_score = (semantic_weight * semantic_score) + (time_weight * temporal_score)
                
                scored_memory = memory.copy()
                scored_memory["hybrid_score"] = hybrid_score
                scored_memory["semantic_score"] = semantic_score
                scored_memory["temporal_score"] = temporal_score
                
                scored_memories.append(scored_memory)
            
            # Sort by hybrid score and limit
            scored_memories.sort(key=lambda m: m["hybrid_score"], reverse=True)
            final_memories = scored_memories[:top_k]
            
            return self._create_success_response({
                "strategy": "hybrid",
                "query": query,
                "memories_found": len(final_memories),
                "memories": self._format_memories_for_response(final_memories),
                "search_metadata": {
                    "hybrid_scoring": True,
                    "semantic_weight": semantic_weight,
                    "time_weight": time_weight,
                    "scoring_details": [
                        {
                            "content_preview": m["content"][:50] + "..." if len(m["content"]) > 50 else m["content"],
                            "hybrid_score": round(m["hybrid_score"], 3),
                            "semantic_score": round(m["semantic_score"], 3),
                            "temporal_score": round(m["temporal_score"], 3)
                        }
                        for m in final_memories
                    ]
                }
            })
            
        except Exception as e:
            return self._create_error_response(f"Hybrid search failed: {str(e)}", "HYBRID_SEARCH_ERROR")
    
    async def _recent_memories(self, params: Dict[str, Any], agent_id: UUID) -> Dict[str, Any]:
        """Get recent memories chronologically"""
        try:
            top_k = params.get("top_k", 5)
            memory_types = params.get("memory_types", None)
            
            # Get recent memories
            recent_memories = await self.memory_service.list_memories_by_agent(
                agent_id=agent_id,
                limit=top_k * 2  # Get more to apply filters
            )
            
            # Convert to dict format and apply filters
            memory_dicts = [
                {
                    "content": memory.content,
                    "metadata": getattr(memory, 'metadatas', {}),
                    "created_at": memory.created_at.isoformat() if memory.created_at else None
                }
                for memory in recent_memories
            ]
            
            filtered_memories = self._apply_filters(memory_dicts, memory_types=memory_types)
            final_memories = filtered_memories[:top_k]
            
            return self._create_success_response({
                "strategy": "recent",
                "memories_found": len(final_memories),
                "memories": final_memories,
                "search_metadata": {
                    "chronological_order": True,
                    "most_recent_first": True
                }
            })
            
        except Exception as e:
            return self._create_error_response(f"Recent memories search failed: {str(e)}", "RECENT_SEARCH_ERROR")
    
    async def _importance_search(self, params: Dict[str, Any], agent_id: UUID) -> Dict[str, Any]:
        """Search memories by importance score"""
        try:
            top_k = params.get("top_k", 5)
            min_importance = params.get("min_importance", 0.7)
            memory_types = params.get("memory_types", None)
            
            # Get all memories to filter by importance
            all_memories = await self.memory_service.list_memories_by_agent(
                agent_id=agent_id,
                limit=1000
            )
            
            # Convert to dict format and filter by importance
            important_memories = []
            for memory in all_memories:
                metadata = getattr(memory, 'metadatas', {})
                importance = metadata.get('importance', 0.5)
                
                if importance >= min_importance:
                    important_memories.append({
                        "content": memory.content,
                        "metadata": metadata,
                        "created_at": memory.created_at.isoformat() if memory.created_at else None,
                        "importance": importance
                    })
            
            # Apply additional filters
            filtered_memories = self._apply_filters(important_memories, memory_types=memory_types)
            
            # Sort by importance and limit
            filtered_memories.sort(key=lambda m: m.get("importance", 0), reverse=True)
            final_memories = filtered_memories[:top_k]
            
            return self._create_success_response({
                "strategy": "importance",
                "min_importance": min_importance,
                "memories_found": len(final_memories),
                "memories": final_memories,
                "search_metadata": {
                    "importance_filtered": True,
                    "sorted_by_importance": True,
                    "average_importance": sum(m.get("importance", 0) for m in final_memories) / len(final_memories) if final_memories else 0
                }
            })
            
        except Exception as e:
            return self._create_error_response(f"Importance search failed: {str(e)}", "IMPORTANCE_SEARCH_ERROR")
    
    def _parse_temporal_params(self, params: Dict[str, Any]) -> tuple[datetime, datetime]:
        """Parse temporal search parameters into start and end dates"""
        start_date = params.get("start_date")
        end_date = params.get("end_date")
        days_back = params.get("days_back")
        
        current_time = datetime.utcnow()
        
        if days_back:
            start_date = current_time - timedelta(days=days_back)
            end_date = current_time
        else:
            if start_date:
                if isinstance(start_date, str):
                    start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            else:
                start_date = current_time - timedelta(days=30)  # Default to 30 days back
            
            if end_date:
                if isinstance(end_date, str):
                    end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            else:
                end_date = current_time
        
        return start_date, end_date
    
    def _apply_filters(
        self, 
        memories: List[Dict[str, Any]], 
        memory_types: Optional[List[str]] = None,
        min_importance: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Apply filters to memory results"""
        filtered = memories
        
        # Filter by memory types
        if memory_types:
            filtered = [
                m for m in filtered 
                if m.get("metadata", {}).get("type") in memory_types
            ]
        
        # Filter by minimum importance
        if min_importance is not None:
            filtered = [
                m for m in filtered 
                if m.get("metadata", {}).get("importance", 0.5) >= min_importance
            ]
        
        return filtered
    
    def _format_memories_for_response(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format memories for consistent response structure"""
        formatted = []
        
        for memory in memories:
            formatted_memory = {
                "content": memory.get("content", ""),
                "metadata": memory.get("metadata", {}),
                "created_at": memory.get("created_at"),
            }
            
            # Add search-specific scores if present
            if "hybrid_score" in memory:
                formatted_memory["scores"] = {
                    "hybrid": memory["hybrid_score"],
                    "semantic": memory.get("semantic_score"),
                    "temporal": memory.get("temporal_score")
                }
            
            if "importance" in memory:
                formatted_memory["importance"] = memory["importance"]
            
            formatted.append(formatted_memory)
        
        return formatted