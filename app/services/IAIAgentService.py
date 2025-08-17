# app/services/IAIAgentService.py

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID
from app.dtos.ai_agent_dto import AIAgentDTO
from app.dtos.ai_agent_create_request_dto import AIAgentCreateRequestDTO
from app.dtos.ai_agent_update_request_dto import AIAgentUpdateRequestDTO
from app.dtos.ai_agent_response_dto import AIAgentResponseDTO

class IAIAgentService(ABC):
    """Interface for AI Agent Service"""
    
    @abstractmethod
    async def list_agents(self) -> List[AIAgentDTO]:
        """List all agents"""
        pass
    
    @abstractmethod
    async def get_agent(self, agent_id: UUID) -> Optional[AIAgentDTO]:
        """Get agent by ID"""
        pass
    
    @abstractmethod
    async def create_agent(self, dto: AIAgentCreateRequestDTO) -> AIAgentDTO:
        """Create a new agent"""
        pass
    
    @abstractmethod
    async def update_agent(self, agent_id: UUID, dto: AIAgentUpdateRequestDTO) -> Optional[AIAgentDTO]:
        """Update an existing agent"""
        pass
    
    @abstractmethod
    async def delete_agent(self, agent_id: UUID) -> bool:
        """Delete an agent"""
        pass
    
    @abstractmethod
    async def get_agent_model_config(self, agent_id: UUID) -> dict:
        """Get agent model configuration"""
        pass
    
    @abstractmethod
    async def list_available_models_for_agents(self) -> List[dict]:
        """List available models for agents"""
        pass
    
    @abstractmethod
    async def track_agent_usage(
        self, 
        agent_id: UUID, 
        input_tokens: int, 
        output_tokens: int, 
        cost: float = None
    ) -> None:
        """Track agent usage"""
        pass
    
    @abstractmethod
    async def get_agent_cost_analytics(self, agent_id: UUID) -> dict:
        """Get agent cost analytics"""
        pass
    
    @abstractmethod
    async def execute_agent(
        self,
        agent_id: UUID,
        user_prompt: str,
        user_id: Optional[int] = None,
        temperature: Optional[float] = None,
        max_iterations: Optional[int] = None,
        api_key: str = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute an agent"""
        pass
    
    @abstractmethod
    async def execute_agent_for_api(
        self,
        agent_id: UUID,
        user_prompt: str,
        api_key: str,
        temperature: Optional[float] = None,
        model: Optional[str] = None,
        user_id: Optional[int] = None,
        max_iterations: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> AIAgentResponseDTO:
        """Execute agent for API consumption"""
        pass