from typing import Dict, Any, Optional
from uuid import UUID

from .base_memory_handler import GlobalMemoryHandler
from app.connectors.factory import register_tool, register_node

@register_node("SemanticMemoryHandler")
@register_tool("SemanticMemoryHandler")
class SemanticMemoryHandler(GlobalMemoryHandler):
    """
    Semantic memory handler - General knowledge about user and world
    Manages knowledge graph with entities, relations, and properties
    Note: Uses global memory (not agent-specific) for shared knowledge
    """
    
    metadata = {
        "type": "tool",
        "category": "memory",
        "description": "Manage semantic knowledge graph about user and world",
        "capabilities": ["add_knowledge", "query_connections", "query_inference", "search_entities"],
        "scope": "global"  # Indicates this operates on global knowledge
    }
    
    def _validate_handler_params(self, params: Dict[str, Any]) -> Optional[str]:
        """Validate semantic memory specific parameters"""
        # First validate base requirements (global handler, no agent_id needed)
        base_error = super()._validate_handler_params(params)
        if base_error:
            return base_error
        
        # Validate action
        action = params.get("action")
        if not action:
            return "action is required (add_knowledge, query_connections, query_inference, search_entities)"
        
        valid_actions = ["add_knowledge", "query_connections", "query_inference", "search_entities"]
        if action not in valid_actions:
            return f"Invalid action: {action}. Must be one of {valid_actions}"
        
        # Validate parameters for add_knowledge action
        if action == "add_knowledge":
            entity = params.get("entity")
            if not entity:
                return "entity is required for add_knowledge action"
            
            relation = params.get("relation")
            if not relation:
                return "relation is required for add_knowledge action"
            
            # properties is optional but should be dict if provided
            properties = params.get("properties")
            if properties is not None and not isinstance(properties, dict):
                return "properties must be a dictionary if provided"
        
        # Validate parameters for query actions
        elif action in ["query_connections", "query_inference", "search_entities"]:
            if action in ["query_connections", "query_inference"]:
                entity = params.get("entity")
                if not entity:
                    return f"entity is required for {action} action"
            
            elif action == "search_entities":
                query = params.get("query")
                if not query:
                    return "query is required for search_entities action"
        
        return None
    
    async def _handle_memory_operation(
        self, 
        params: Dict[str, Any], 
        agent_id: Optional[UUID]
    ) -> Dict[str, Any]:
        """Handle semantic memory operations"""
        action = params["action"]
        
        # Log the operation
        await self._log_memory_operation(f"semantic_memory_{action}", agent_id, params, {})
        
        if action == "add_knowledge":
            return await self._add_knowledge(params)
        
        elif action == "query_connections":
            return await self._query_connections(params)
        
        elif action == "query_inference":
            return await self._query_inference(params)
        
        elif action == "search_entities":
            return await self._search_entities(params)
        
        else:
            return self._create_error_response(f"Unknown action: {action}", "INVALID_ACTION")
    
    async def _add_knowledge(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add new knowledge to the semantic graph"""
        try:
            entity = params["entity"]
            relation = params["relation"]
            properties = params.get("properties", {})
            
            # Add metadata for better tracking
            enhanced_properties = {
                **properties,
                "added_via": "semantic_memory_handler",
                "confidence": properties.get("confidence", 0.8),
                "source": properties.get("source", "user_interaction")
            }
            
            result = await self.memory_service.add_to_knowledge_graph(
                entity=entity,
                relation=relation,
                properties=enhanced_properties
            )
            
            return self._create_success_response({
                "action": "add_knowledge",
                "entity": entity,
                "relation": relation,
                "properties": enhanced_properties,
                "status": result.get("status", "success"),
                "knowledge_id": f"{entity}:{relation}"
            })
            
        except Exception as e:
            return self._create_error_response(f"Failed to add knowledge: {str(e)}", "ADD_KNOWLEDGE_ERROR")
    
    async def _query_connections(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query connections for a specific entity"""
        try:
            entity = params["entity"]
            max_connections = params.get("max_connections", 10)
            
            result = await self.memory_service.query_connections(entity)
            
            connections = result.get("connections", [])
            
            # Limit connections if needed
            if len(connections) > max_connections:
                connections = connections[:max_connections]
            
            return self._create_success_response({
                "action": "query_connections",
                "entity": entity,
                "connections_found": len(connections),
                "connections": connections,
                "status": result.get("status", "success")
            })
            
        except Exception as e:
            return self._create_error_response(f"Failed to query connections: {str(e)}", "QUERY_CONNECTIONS_ERROR")
    
    async def _query_inference(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Infer new knowledge based on existing connections"""
        try:
            entity = params["entity"]
            inference_type = params.get("inference_type", "basic")
            
            result = await self.memory_service.infer_knowledge(entity)
            
            return self._create_success_response({
                "action": "query_inference",
                "entity": entity,
                "inference_type": inference_type,
                "inferences": result.get("inferences", []),
                "status": result.get("status", "success"),
                "message": result.get("message", "Inference completed")
            })
            
        except Exception as e:
            return self._create_error_response(f"Failed to infer knowledge: {str(e)}", "INFERENCE_ERROR")
    
    async def _search_entities(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for entities in the knowledge graph"""
        try:
            query = params["query"]
            top_k = params.get("top_k", 10)
            
            # Use the basic retrieve_similar method to search for entities
            # This searches in the global knowledge space (dummy agent_id)
            from uuid import UUID
            dummy_agent_id = UUID("00000000-0000-0000-0000-000000000000")
            
            memories = await self.memory_service.retrieve_similar(
                agent_id=dummy_agent_id,
                query=query,
                top_k=top_k
            )
            
            # Filter for semantic memories only
            semantic_memories = [
                m for m in memories 
                if m.get("metadata", {}).get("type") == "semantic"
            ]
            
            # Extract entities from the results
            entities = []
            for memory in semantic_memories:
                metadata = memory.get("metadata", {})
                if "entity" in metadata:
                    entities.append({
                        "entity": metadata["entity"],
                        "relation": metadata.get("relation"),
                        "properties": metadata.get("properties", {}),
                        "content": memory.get("content", ""),
                        "relevance_score": 1.0  # Could implement scoring later
                    })
            
            return self._create_success_response({
                "action": "search_entities",
                "query": query,
                "entities_found": len(entities),
                "entities": entities
            })
            
        except Exception as e:
            return self._create_error_response(f"Failed to search entities: {str(e)}", "SEARCH_ERROR")