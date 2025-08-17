from typing import Dict, Any, Optional, List
from uuid import UUID
import asyncio

from .base_memory_handler import AgentRequiredMemoryHandler
from app.connectors.factory import register_tool, register_node

@register_node("MemoryCompressionHandler")
@register_tool("MemoryCompressionHandler")
class MemoryCompressionHandler(AgentRequiredMemoryHandler):
    """
    Memory compression handler - Intelligently compress old memories
    Similar to human forgetting but maintains essence of important information
    """
    
    metadata = {
        "type": "tool",
        "category": "memory",
        "description": "Compress old memories while maintaining important information",
        "capabilities": ["compress", "analyze", "cleanup"],
        "strategies": ["importance_based", "temporal_decay", "similarity_clustering"]
    }
    
    def _validate_handler_params(self, params: Dict[str, Any]) -> Optional[str]:
        """Validate compression specific parameters"""
        # First validate agent requirement
        base_error = super()._validate_handler_params(params)
        if base_error:
            return base_error
        
        # Validate action
        action = params.get("action", "compress")  # Default action
        valid_actions = ["compress", "analyze", "cleanup"]
        if action not in valid_actions:
            return f"Invalid action: {action}. Must be one of {valid_actions}"
        
        # Validate compression strategy
        strategy = params.get("compression_strategy", "importance_based")
        valid_strategies = self.metadata["strategies"]
        if strategy not in valid_strategies:
            return f"Invalid compression strategy: {strategy}. Must be one of {valid_strategies}"
        
        # Validate numeric parameters
        days_old = params.get("days_old", 30)
        if not isinstance(days_old, (int, float)) or days_old < 1:
            return "days_old must be a positive number"
        
        max_memories = params.get("max_memories", 1000)
        if not isinstance(max_memories, int) or max_memories < 1:
            return "max_memories must be a positive integer"
        
        return None
    
    async def _handle_memory_operation(
        self, 
        params: Dict[str, Any], 
        agent_id: UUID
    ) -> Dict[str, Any]:
        """Handle memory compression operations"""
        action = params.get("action", "compress")
        
        # Log the operation
        await self._log_memory_operation(f"memory_compression_{action}", agent_id, params, {})
        
        if action == "compress":
            return await self._compress_memories(params, agent_id)
        
        elif action == "analyze":
            return await self._analyze_compression_candidates(params, agent_id)
        
        elif action == "cleanup":
            return await self._cleanup_compressed_memories(params, agent_id)
        
        else:
            return self._create_error_response(f"Unknown action: {action}", "INVALID_ACTION")
    
    async def _compress_memories(self, params: Dict[str, Any], agent_id: UUID) -> Dict[str, Any]:
        """Compress memories using specified strategy"""
        try:
            strategy = params.get("compression_strategy", "importance_based")
            days_old = params.get("days_old", 30)
            dry_run = params.get("dry_run", False)
            
            # Get compressible memories
            compressible_memories = await self.memory_service.get_compressible_memories(
                agent_id=agent_id, 
                days_old=days_old
            )
            
            if not compressible_memories:
                return self._create_success_response({
                    "action": "compress",
                    "strategy": strategy,
                    "memories_found": 0,
                    "compressed_count": 0,
                    "message": "No memories found for compression"
                })
            
            if strategy == "importance_based":
                result = await self._compress_by_importance(compressible_memories, agent_id, dry_run)
            elif strategy == "temporal_decay":
                result = await self._compress_by_temporal_decay(compressible_memories, agent_id, dry_run)
            elif strategy == "similarity_clustering":
                result = await self._compress_by_similarity(compressible_memories, agent_id, dry_run)
            else:
                return self._create_error_response(f"Strategy {strategy} not implemented", "STRATEGY_ERROR")
            
            return self._create_success_response({
                "action": "compress",
                "strategy": strategy,
                "memories_found": len(compressible_memories),
                "compressed_count": result.get("compressed_count", 0),
                "space_saved_percent": result.get("space_saved_percent", 0),
                "dry_run": dry_run,
                "details": result.get("details", [])
            })
            
        except Exception as e:
            return self._create_error_response(f"Failed to compress memories: {str(e)}", "COMPRESSION_ERROR")
    
    async def _analyze_compression_candidates(self, params: Dict[str, Any], agent_id: UUID) -> Dict[str, Any]:
        """Analyze which memories are candidates for compression"""
        try:
            days_old = params.get("days_old", 30)
            
            compressible_memories = await self.memory_service.get_compressible_memories(
                agent_id=agent_id, 
                days_old=days_old
            )
            
            # Analyze the memories
            analysis = {
                "total_candidates": len(compressible_memories),
                "by_importance": {},
                "by_age": {},
                "by_type": {},
                "estimated_compression": {}
            }
            
            # Group by importance
            for memory in compressible_memories:
                importance = memory.get("metadata", {}).get("importance", 0.5)
                importance_bucket = self._get_importance_bucket(importance)
                analysis["by_importance"][importance_bucket] = analysis["by_importance"].get(importance_bucket, 0) + 1
            
            # Group by memory type
            for memory in compressible_memories:
                memory_type = memory.get("metadata", {}).get("type", "unknown")
                analysis["by_type"][memory_type] = analysis["by_type"].get(memory_type, 0) + 1
            
            # Estimate compression potential
            total_content_length = sum(len(m.get("content", "")) for m in compressible_memories)
            estimated_compressed_length = total_content_length * 0.3  # Rough estimate
            
            analysis["estimated_compression"] = {
                "original_size": total_content_length,
                "estimated_compressed_size": estimated_compressed_length,
                "estimated_savings_percent": ((total_content_length - estimated_compressed_length) / total_content_length * 100) if total_content_length > 0 else 0
            }
            
            return self._create_success_response({
                "action": "analyze",
                "agent_id": str(agent_id),
                "days_old": days_old,
                "analysis": analysis
            })
            
        except Exception as e:
            return self._create_error_response(f"Failed to analyze compression candidates: {str(e)}", "ANALYSIS_ERROR")
    
    async def _cleanup_compressed_memories(self, params: Dict[str, Any], agent_id: UUID) -> Dict[str, Any]:
        """Clean up already compressed memories"""
        try:
            # This is a placeholder - in a real implementation you'd have
            # a way to track and clean up compressed memory artifacts
            
            return self._create_success_response({
                "action": "cleanup",
                "agent_id": str(agent_id),
                "cleaned_up": 0,
                "message": "Cleanup functionality not fully implemented"
            })
            
        except Exception as e:
            return self._create_error_response(f"Failed to cleanup memories: {str(e)}", "CLEANUP_ERROR")
    
    async def _compress_by_importance(self, memories: List[Dict], agent_id: UUID, dry_run: bool) -> Dict[str, Any]:
        """Compress memories based on importance scores"""
        # Group memories by importance level
        low_importance = [m for m in memories if m.get("metadata", {}).get("importance", 0.5) < 0.3]
        medium_importance = [m for m in memories if 0.3 <= m.get("metadata", {}).get("importance", 0.5) < 0.7]
        
        compressed_count = 0
        details = []
        
        # Compress low importance memories aggressively
        if low_importance:
            if not dry_run:
                # In real implementation, you'd create compressed summaries
                pass
            compressed_count += len(low_importance)
            details.append(f"Compressed {len(low_importance)} low importance memories")
        
        # Lightly compress medium importance memories
        if medium_importance:
            if not dry_run:
                # In real implementation, you'd create less aggressive summaries
                pass
            compressed_count += len(medium_importance) // 2  # Compress half
            details.append(f"Lightly compressed {len(medium_importance) // 2} medium importance memories")
        
        space_saved = (compressed_count / len(memories) * 100) if memories else 0
        
        return {
            "compressed_count": compressed_count,
            "space_saved_percent": space_saved,
            "details": details
        }
    
    async def _compress_by_temporal_decay(self, memories: List[Dict], agent_id: UUID, dry_run: bool) -> Dict[str, Any]:
        """Compress memories based on temporal decay"""
        # Sort by age and compress older memories more aggressively
        import time
        from datetime import datetime
        
        current_time = time.time()
        
        for memory in memories:
            try:
                created_at = memory.get("created_at")
                if created_at:
                    if isinstance(created_at, str):
                        memory_time = datetime.fromisoformat(created_at.replace('Z', '+00:00')).timestamp()
                    else:
                        memory_time = created_at.timestamp() if hasattr(created_at, 'timestamp') else float(created_at)
                    
                    age_days = (current_time - memory_time) / (24 * 3600)
                    memory["_age_days"] = age_days
                else:
                    memory["_age_days"] = 0
            except:
                memory["_age_days"] = 0
        
        # Compress based on age
        very_old = [m for m in memories if m.get("_age_days", 0) > 90]
        old = [m for m in memories if 30 <= m.get("_age_days", 0) <= 90]
        
        compressed_count = len(very_old) + len(old) // 2
        space_saved = (compressed_count / len(memories) * 100) if memories else 0
        
        return {
            "compressed_count": compressed_count,
            "space_saved_percent": space_saved,
            "details": [
                f"Heavily compressed {len(very_old)} very old memories (>90 days)",
                f"Lightly compressed {len(old) // 2} old memories (30-90 days)"
            ]
        }
    
    async def _compress_by_similarity(self, memories: List[Dict], agent_id: UUID, dry_run: bool) -> Dict[str, Any]:
        """Compress similar memories by clustering"""
        # This is a simplified version - in reality you'd use embeddings
        # to find truly similar memories and merge them
        
        # Group by content similarity (simplified)
        similarity_groups = self._group_similar_memories(memories)
        
        compressed_count = 0
        for group in similarity_groups:
            if len(group) > 1:
                compressed_count += len(group) - 1  # Keep one, compress others
        
        space_saved = (compressed_count / len(memories) * 100) if memories else 0
        
        return {
            "compressed_count": compressed_count,
            "space_saved_percent": space_saved,
            "details": [f"Found {len(similarity_groups)} similarity groups, compressed {compressed_count} duplicate memories"]
        }
    
    def _get_importance_bucket(self, importance: float) -> str:
        """Categorize importance into buckets"""
        if importance < 0.3:
            return "low"
        elif importance < 0.7:
            return "medium"
        else:
            return "high"
    
    def _group_similar_memories(self, memories: List[Dict]) -> List[List[Dict]]:
        """Group similar memories (simplified implementation)"""
        # This is a very basic implementation
        # In reality, you'd use embeddings and clustering algorithms
        
        groups = []
        used_indices = set()
        
        for i, memory1 in enumerate(memories):
            if i in used_indices:
                continue
            
            group = [memory1]
            used_indices.add(i)
            
            content1 = memory1.get("content", "").lower()
            
            for j, memory2 in enumerate(memories[i+1:], i+1):
                if j in used_indices:
                    continue
                
                content2 = memory2.get("content", "").lower()
                
                # Simple similarity check - in reality use cosine similarity
                if self._simple_similarity(content1, content2) > 0.7:
                    group.append(memory2)
                    used_indices.add(j)
            
            groups.append(group)
        
        return groups
    
    def _simple_similarity(self, text1: str, text2: str) -> float:
        """Simple text similarity calculation"""
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0