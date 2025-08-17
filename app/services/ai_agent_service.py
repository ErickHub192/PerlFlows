# app/services/ai_agent_service.py

from typing import List, Optional, Dict, Any
from uuid import UUID
import time
import logging
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.repositories.ai_agent_repository import AIAgentRepository
from app.repositories.llm_model_repository import LLMModelRepository
from app.repositories.llm_provider_repository import LLMProviderRepository
from app.dependencies.llm_dependencies import get_llm_model_repository, get_llm_provider_repository
# Interface removed - using concrete class
from app.dtos.ai_agent_dto import AIAgentDTO
from app.dtos.ai_agent_create_request_dto import AIAgentCreateRequestDTO
from app.dtos.ai_agent_update_request_dto import AIAgentUpdateRequestDTO
from app.exceptions.api_exceptions import InvalidDataException, WorkflowProcessingException

# Fusión: Imports para ejecución de agentes
from app.ai.llm_clients.llm_service import LLMService
from app.ai.memories.manager import MemoryManager
from app.ai.tool_executor import ToolExecutor
from app.ai.llm_clients.tool_router import ToolRouter
from app.dtos.ai_agent_response_dto import AIAgentResponseDTO


class AIAgentService:
    """
    Unified AI Agent Service that replaces redundant services.
    
    Responsibilities:
    - Agent lifecycle management (CRUD)
    - LLM model integration and validation
    - Parameter resolution for agent execution
    - Integration with LLM Provider system
    """

    def __init__(
        self,
        agent_repo: AIAgentRepository,
        model_repo: LLMModelRepository,
        provider_repo: LLMProviderRepository,
        db: AsyncSession
    ):
        self.agent_repo = agent_repo
        self.model_repo = model_repo
        self.provider_repo = provider_repo
        self.db = db
        
        # Fusión: Servicios para ejecución de agentes
        self.tool_router = ToolRouter()
        self.logger = logging.getLogger(__name__)

    async def list_agents(self) -> List[AIAgentDTO]:
        """Get all agents"""
        return await self.agent_repo.list_agents()

    async def get_agent(self, agent_id: UUID) -> Optional[AIAgentDTO]:
        """Get agent by ID"""
        return await self.agent_repo.get_agent(agent_id)

    async def create_agent(self, dto: AIAgentCreateRequestDTO) -> AIAgentDTO:
        """
        Create new agent with LLM model validation and provider/model resolution
        ✅ Service maneja transacciones (movido desde repository)
        """
        try:
            # ✅ Service maneja la transacción
            async with self.db.begin():
                llm_provider_id = None
                llm_model_id = None
                
                # Resolve model to provider and model IDs if provided
                if hasattr(dto, 'model') and dto.model:
                    model_info = await self._resolve_model_references(dto.model)
                    llm_provider_id = model_info.get('provider_id')
                    llm_model_id = model_info.get('model_id')
                
                # Convert create request to agent DTO with enhanced LLM references
                agent_dto = AIAgentDTO(
                    name=dto.name,
                    default_prompt=dto.default_prompt,
                    tools=dto.tools or [],
                    model=getattr(dto, 'model', None),  # Keep for backward compatibility
                    llm_provider_id=llm_provider_id,
                    llm_model_id=llm_model_id,
                    temperature=getattr(dto, 'temperature', 0.7),
                    max_iterations=getattr(dto, 'max_iterations', 5),
                    memory_schema=getattr(dto, 'memory_schema', {}),
                    status=getattr(dto, 'status', 'queued'),
                    total_input_tokens=0,
                    total_output_tokens=0,
                    total_cost=0
                )
                
                return await self.agent_repo.create_agent(agent_dto)
                
        except Exception as e:
            raise InvalidDataException(f"Error creando agente: {str(e)}")

    async def update_agent(self, agent_id: UUID, dto: AIAgentUpdateRequestDTO) -> Optional[AIAgentDTO]:
        """
        Update agent with LLM model validation
        ✅ Service maneja transacciones (movido desde repository)
        """
        try:
            # ✅ Service maneja la transacción
            async with self.db.begin():
                # Validate model if being updated
                if hasattr(dto, 'model') and dto.model:
                    await self._validate_model(dto.model)
                
                # Convert update request to agent DTO
                agent_dto = AIAgentDTO(
                    agent_id=agent_id,
                    name=getattr(dto, 'name', None),
                    default_prompt=getattr(dto, 'default_prompt', None),
                    tools=getattr(dto, 'tools', None),
                    model=getattr(dto, 'model', None),
                    temperature=getattr(dto, 'temperature', None),
                    max_iterations=getattr(dto, 'max_iterations', None),
                    memory_schema=getattr(dto, 'memory_schema', None),
                    status=getattr(dto, 'status', None)
                )
                
                return await self.agent_repo.update_agent(agent_id, agent_dto)
                
        except Exception as e:
            raise InvalidDataException(f"Error actualizando agente: {str(e)}")

    async def delete_agent(self, agent_id: UUID) -> bool:
        """
        Delete agent
        ✅ Service maneja transacciones (movido desde repository)
        """
        try:
            # ✅ Service maneja la transacción
            async with self.db.begin():
                return await self.agent_repo.delete_agent(agent_id)
                
        except Exception as e:
            raise InvalidDataException(f"Error eliminando agente: {str(e)}")

    async def _resolve_model_references(self, model_key: str) -> dict:
        """
        Resolve model key to provider and model IDs with validation
        """
        if not model_key:
            return {}
        
        model = await self.model_repo.get_by_model_key(model_key)
        if not model:
            raise InvalidDataException(f"Model '{model_key}' not found")
        
        if not model.is_active:
            raise InvalidDataException(f"Model '{model_key}' is not active")
        
        # Validate provider is also active
        provider = await self.provider_repo.get_by_id(model.provider_id)
        if not provider or not provider.is_active:
            raise InvalidDataException(f"Provider for model '{model_key}' is not active")
        
        return {
            'provider_id': provider.provider_id,
            'model_id': model.model_id,
            'provider_key': provider.provider_key,
            'model_key': model.model_key,
            'provider_name': provider.name,
            'model_name': model.display_name
        }

    async def _validate_model(self, model_key: str) -> None:
        """
        Validate that the specified model exists and is active
        """
        await self._resolve_model_references(model_key)

    async def get_agent_model_config(self, agent_id: UUID) -> dict:
        """
        Get resolved model configuration for an agent
        """
        agent = await self.get_agent(agent_id)
        if not agent:
            raise InvalidDataException(f"Agent {agent_id} not found")
        
        if not agent.model:
            return {
                "model_key": None,
                "provider_key": None,
                "model_name": None,
                "provider_name": None,
                "context_length": None,
                "cost_per_1k_input": None,
                "cost_per_1k_output": None
            }
        
        model = await self.model_repo.get_by_model_key(agent.model)
        if not model:
            raise InvalidDataException(f"Model '{agent.model}' configured for agent not found")
        
        provider = await self.provider_repo.get_by_provider_key(model.provider_key)
        
        return {
            "model_key": model.model_key,
            "provider_key": model.provider_key,
            "model_name": model.name,
            "provider_name": provider.name if provider else None,
            "context_length": model.context_length,
            "cost_per_1k_input": model.cost_per_1k_input_tokens,
            "cost_per_1k_output": model.cost_per_1k_output_tokens,
            "capabilities": model.capabilities,
            "is_recommended": model.is_recommended
        }

    async def list_available_models_for_agents(self) -> List[dict]:
        """
        Get list of models suitable for agents
        """
        models = await self.model_repo.get_all_active()
        
        result = []
        for model in models:
            provider = await self.provider_repo.get_by_provider_key(model.provider_key)
            result.append({
                "model_key": model.model_key,
                "model_name": model.name,
                "provider_key": model.provider_key,
                "provider_name": provider.name if provider else None,
                "context_length": model.context_length,
                "cost_per_1k_input": model.cost_per_1k_input_tokens,
                "is_recommended": model.is_recommended,
                "capabilities": model.capabilities
            })
        
        return result
    
    async def track_agent_usage(
        self, 
        agent_id: UUID, 
        input_tokens: int, 
        output_tokens: int, 
        cost: float = None
    ) -> None:
        """
        Track token usage and costs for an agent
        """
        agent = await self.agent_repo.get_agent(agent_id)
        if not agent:
            raise InvalidDataException(f"Agent {agent_id} not found")
        
        # Calculate cost if not provided
        calculated_cost = cost
        if calculated_cost is None and agent.llm_model_id:
            model = await self.model_repo.get_by_id(agent.llm_model_id)
            if model and model.input_cost_per_1k and model.output_cost_per_1k:
                input_cost = (input_tokens / 1000) * float(model.input_cost_per_1k)
                output_cost = (output_tokens / 1000) * float(model.output_cost_per_1k)
                calculated_cost = input_cost + output_cost
        
        # Update agent usage statistics
        new_total_input = (agent.total_input_tokens or 0) + input_tokens
        new_total_output = (agent.total_output_tokens or 0) + output_tokens
        new_total_cost = float(agent.total_cost or 0) + (calculated_cost or 0)
        
        # Create update DTO
        from app.dtos.ai_agent_update_request_dto import AIAgentUpdateRequestDTO
        update_dto = AIAgentUpdateRequestDTO(
            total_input_tokens=new_total_input,
            total_output_tokens=new_total_output,
            total_cost=new_total_cost
        )
        
        await self.agent_repo.update_agent(agent_id, update_dto)
    
    async def get_agent_cost_analytics(self, agent_id: UUID) -> dict:
        """
        Get cost analytics for an agent
        """
        agent = await self.get_agent(agent_id)
        if not agent:
            raise InvalidDataException(f"Agent {agent_id} not found")
        
        # Get current model pricing if available
        current_model_info = {}
        if agent.llm_model_id:
            model = await self.model_repo.get_by_id(agent.llm_model_id)
            if model:
                current_model_info = {
                    'model_name': model.display_name,
                    'provider_name': model.provider.name if hasattr(model, 'provider') else 'Unknown',
                    'input_cost_per_1k': float(model.input_cost_per_1k or 0),
                    'output_cost_per_1k': float(model.output_cost_per_1k or 0)
                }
        
        return {
            'agent_id': str(agent_id),
            'total_tokens': (agent.total_input_tokens or 0) + (agent.total_output_tokens or 0),
            'total_input_tokens': agent.total_input_tokens or 0,
            'total_output_tokens': agent.total_output_tokens or 0,
            'total_cost': float(agent.total_cost or 0),
            'average_cost_per_token': (
                float(agent.total_cost or 0) / ((agent.total_input_tokens or 0) + (agent.total_output_tokens or 0))
                if (agent.total_input_tokens or 0) + (agent.total_output_tokens or 0) > 0 
                else 0
            ),
            'current_model': current_model_info
        }

    # ===============================
    # FUSIÓN: FUNCIONALIDAD DE EJECUCIÓN (de agent_execution_service)
    # ===============================
    
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
        """
        Execute agent with model validation and usage tracking
        """
        start_time = time.time()
        
        try:
            # 1. Load and validate agent configuration
            agent = await self.get_agent(agent_id)
            if not agent:
                raise InvalidDataException(f"Agent {agent_id} not found")
            
            # 2. Resolve and validate model using built-in validation
            model_key = await self._resolve_agent_model_for_execution(agent)
            model_info = await self._resolve_model_references(model_key)  # Uses existing validation
            effective_model = model_info['model_key']
            
            # 3. Create session for tracking
            if not session_id:
                session_id = f"agent_{agent_id}_{int(start_time)}"
            
            # 4. Initialize LLM service with validated model info
            llm_service = LLMService(
                api_key=api_key,
                model=effective_model,
                model_info=model_info
            )
            
            # 5. Initialize memory manager
            mem_mgr = MemoryManager(schema=agent.memory_schema or {})
            await mem_mgr.clear_short_term(agent_id)
            
            # Use original user prompt without automatic memory injection
            enhanced_prompt = user_prompt
            
            # 6. Execute agent iterations with comprehensive tracking
            effective_temperature = temperature if temperature is not None else agent.temperature
            effective_max_iterations = max_iterations if max_iterations is not None else agent.max_iterations
            
            final_result = None
            iteration_results = []
            
            for iteration in range(effective_max_iterations):
                iteration_start = time.time()
                self.logger.info(f"Agent {agent_id} iteration {iteration + 1}/{effective_max_iterations}")
                
                # Run LLM with tracking
                llm_response = await llm_service.run_with_tracking(
                    system_prompt=agent.default_prompt,
                    short_term=[],  # Initialize empty, memory handled by tools
                    long_term=[],
                    user_prompt=enhanced_prompt,
                    temperature=effective_temperature
                )
                
                # Extract usage info and track it
                token_usage = llm_response.get('_token_usage', {})
                iteration_duration = time.time() - iteration_start
                
                # Track token usage directly using built-in method
                if token_usage.get('input_tokens') or token_usage.get('output_tokens'):
                    await self.track_agent_usage(
                        agent_id=agent_id,
                        input_tokens=token_usage.get('input_tokens', 0),
                        output_tokens=token_usage.get('output_tokens', 0)
                    )
                
                iteration_results.append({
                    'iteration': iteration + 1,
                    'response': llm_response,
                    'token_usage': token_usage,
                    'duration_seconds': iteration_duration
                })
                
                # Check if we have steps to execute
                steps = llm_response.get("steps", [])
                if not steps:
                    final_result = llm_response
                    break
                
                # Execute tools
                executor = ToolExecutor(self.tool_router, mem_mgr, llm_service.client)
                llm_response = await executor.execute(agent_id, llm_response, creds={})
                
                # Check if execution is complete
                if llm_response.get("final_output"):
                    final_result = llm_response
                    break
            
            # 7. Store in long-term memory
            if final_result:
                await mem_mgr.store_long_term(agent_id, {
                    "prompt": user_prompt,
                    "response": final_result.get("final_output", "")
                })
            
            # 8. Get final usage summary
            usage_summary = await self.get_agent_cost_analytics(agent_id)
            execution_time = time.time() - start_time
            
            # 9. Update agent cumulative statistics
            if usage_summary:
                await self.track_agent_usage(
                    agent_id=agent_id,
                    input_tokens=usage_summary['total_input_tokens'],
                    output_tokens=usage_summary['total_output_tokens'],
                    cost=usage_summary['total_cost']
                )
            
            # 10. Return comprehensive result
            return {
                'status': 'success',
                'agent_id': str(agent_id),
                'session_id': session_id,
                'result': final_result,
                'iterations': iteration_results,
                'usage_summary': usage_summary,
                'model_used': {
                    'model_key': effective_model,
                    'display_name': model_info['display_name'],
                    'provider_key': model_info['provider_key'],
                    'provider_name': validation_result.provider_info['name']
                },
                'execution_time_seconds': execution_time,
                'parameters_used': {
                    'temperature': effective_temperature,
                    'max_iterations': effective_max_iterations,
                    'model': effective_model,
                    'user_id': user_id
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error executing agent {agent_id}: {e}")
            execution_time = time.time() - start_time
            
            # Session cleanup handled by garbage collection
            
            return {
                'status': 'error',
                'agent_id': str(agent_id),
                'session_id': session_id if 'session_id' in locals() else None,
                'error': str(e),
                'execution_time_seconds': execution_time
            }
    
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
        """
        Execute agent for API consumption - returns DTO directly.
        
        This method encapsulates all business logic for agent execution
        and returns the response in the correct format for the API layer.
        Router should only orchestrate, not contain business logic.
        """
        # Execute agent using internal method
        result = await self.execute_agent(
            agent_id=agent_id,
            user_prompt=user_prompt,
            user_id=user_id,
            temperature=temperature,
            max_iterations=max_iterations,
            api_key=api_key,
            session_id=session_id
        )
        
        # Handle error cases
        if result.get("status") != "success":
            error_message = result.get("error", "Agent execution failed")
            raise WorkflowProcessingException(f"Agent execution failed: {error_message}")
        
        # Extract and convert to DTO format
        agent_result = result.get("result", {})
        
        # Business logic: Convert internal format to API format
        return AIAgentResponseDTO(
            steps=agent_result.get("steps", []),
            final_output=agent_result.get("final_output", ""),
            metadata={
                "execution_time_seconds": result.get("execution_time_seconds"),
                "model_used": result.get("model_used"),
                "usage_summary": result.get("usage_summary"),
                "iterations_count": len(result.get("iterations", [])),
                "session_id": result.get("session_id"),
                "agent_id": str(agent_id),
                "parameters_used": result.get("parameters_used", {}),
                "execution_source": "service"
            }
        )
    
    async def _resolve_agent_model_for_execution(self, agent) -> str:
        """
        Resolve the model key for the agent for execution
        """
        resolved_model = await self._resolve_model_references(agent.model)
        
        if not resolved_model:
            raise InvalidDataException(f"No valid model configuration found for agent {agent.agent_id}")
        
        return resolved_model.get('model_key', agent.model)


def get_ai_agent_service(
    db: AsyncSession = Depends(get_db),
    model_repo: LLMModelRepository = Depends(get_llm_model_repository),
    provider_repo: LLMProviderRepository = Depends(get_llm_provider_repository)
) -> AIAgentService:
    """
    Factory para inyección de dependencias
    ✅ Factory pasa session para transaction management
    """
    agent_repo = AIAgentRepository(db)
    return AIAgentService(agent_repo, model_repo, provider_repo, db)


def get_ai_agent_service_with_execution(
    db: AsyncSession = Depends(get_db),
    model_repo: LLMModelRepository = Depends(get_llm_model_repository),
    provider_repo: LLMProviderRepository = Depends(get_llm_provider_repository)
) -> AIAgentService:
    """
    Factory para AIAgentService con capacidades de ejecución simplificadas
    """
    agent_repo = AIAgentRepository(db)
    return AIAgentService(
        agent_repo, 
        model_repo, 
        provider_repo, 
        db
    )