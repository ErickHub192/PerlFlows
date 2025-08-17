# app/handlers/ai_agent_creator_handler.py

import time
from typing import Any, Dict, Optional
from uuid import uuid4

from .connector_handler import ActionHandler
from app.services.ai_agent_service import AIAgentService, get_ai_agent_service
from app.dtos.ai_agent_create_request_dto import AIAgentCreateRequestDTO
from app.exceptions.api_exceptions import HandlerError
from app.connectors.factory import register_node
from app.db.database import get_db
from app.services.credential_service import get_credential_service, CredentialService
from app.dtos.credential_dto import CredentialInputDTO
from fastapi import Depends


@register_node("AI_Agent_Creator.create_agent")
class AIAgentCreatorHandler(ActionHandler):
    """
    Handler para CREAR nuevos AI Agents.
    
    Kyra diseña TODO (tools, prompt, plan) como siempre.
    Este handler solo:
    1. Recibe lo que Kyra ya diseñó
    2. Pide parámetros mínimos: modelo + credentials
    3. Crea el agente (no lo ejecuta)
    
    Parámetros que Kyra proporciona:
    - agent_name: str - Nombre que Kyra generó
    - agent_prompt: str - Prompt que Kyra diseñó
    - tools: List[str] - Tools que Kyra descubrió/seleccionó
    - trigger_node: str (opcional) - Trigger que Kyra sugiere (ej: "ScheduleTrigger.cron")
    - trigger_params: Dict (opcional) - Parámetros del trigger
    
    Parámetros que usuario debe dar:
    - model: str - Modelo LLM (dropdown)
    - api_key: str (opcional) - Nueva API key 
    - credential_id: str (opcional) - Credential existente
    - activation_type: str (opcional) - "manual" o "triggered"
    """

    def __init__(self, creds: Dict[str, Any]):
        super().__init__(creds)
        self.creds = creds

    async def execute(
        self,
        params: Dict[str, Any],
        creds: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        start = time.perf_counter()
        
        try:
            # 1. Validar y extraer parámetros
            agent_params = self._extract_and_validate_params(params)
            
            # 2. Manejar credentials (híbrido)
            # user_id viene del contexto del workflow (propagado desde la API autenticada)
            user_id = params.get("user_id")
            if not user_id:
                raise HandlerError("user_id is required for creating agent credentials")
            credential_info = await self._handle_credentials(agent_params, user_id)
            
            # 3. Crear el agente usando AIAgentService
            agent_service = await self._get_agent_service()
            
            # 4. Crear DTO de creación (usando lo que Kyra diseñó)
            create_dto = AIAgentCreateRequestDTO(
                name=agent_params["agent_name"],
                default_prompt=agent_params["agent_prompt"], 
                model=agent_params["model"],
                tools=agent_params["tools"],
                temperature=0.7,  # Default reasonable
                max_iterations=5,  # Default reasonable
                memory_schema={
                    "short_term_limit": 10,
                    "vector_store": "postgres"
                },
                # Triggers seleccionados por Kyra + Usuario
                activation_type=agent_params.get("activation_type", "manual"),
                trigger_config=agent_params.get("trigger_config"),
                is_active=agent_params.get("is_active", True)
            )
            
            # 5. Crear el agente
            created_agent = await agent_service.create_agent(create_dto)
            
            # 6. Formatear respuesta de éxito
            return self._format_success(created_agent, credential_info, start)
            
        except HandlerError as he:
            return self._format_error(str(he), start)
        except Exception as e:
            return self._format_error(f"Error creating agent: {e}", start)

    def _extract_and_validate_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrae y valida parámetros:
        - Lo que Kyra diseñó (agent_name, agent_prompt, tools)  
        - Lo que usuario debe dar (model, credentials)
        """
        # Lo que Kyra proporciona (requerido)
        agent_name = params.get("agent_name", "").strip()
        if not agent_name:
            raise HandlerError("Agent name (from Kyra design) is required")
        
        agent_prompt = params.get("agent_prompt", "").strip()
        if not agent_prompt:
            raise HandlerError("Agent prompt (from Kyra design) is required")
        
        tools = params.get("tools", [])
        if not isinstance(tools, list):
            raise HandlerError("Tools (from Kyra design) must be a list")
        
        # Lo que usuario debe dar
        model = params.get("model", "").strip()
        if not model:
            raise HandlerError("LLM model selection is required")
        
        # Credentials (uno de los dos requerido)
        api_key = params.get("api_key", "").strip()
        credential_id = params.get("credential_id", "").strip()
        
        if not api_key and not credential_id:
            raise HandlerError("Either 'api_key' or 'credential_id' is required")
        
        if api_key and credential_id:
            raise HandlerError("Provide either 'api_key' or 'credential_id', not both")
        
        # Trigger configuration (opcional - Kyra puede sugerir)
        activation_type = params.get("activation_type", "manual")
        trigger_node = params.get("trigger_node")  # ej: "ScheduleTrigger.cron"
        trigger_params = params.get("trigger_params", {})  # parámetros del trigger
        is_active = params.get("is_active", True)
        
        # Construir trigger_config si se especifica un trigger
        trigger_config = None
        if activation_type == "triggered" and trigger_node:
            trigger_config = {
                "trigger_node": trigger_node,
                "trigger_params": trigger_params
            }
        
        return {
            "agent_name": agent_name,
            "agent_prompt": agent_prompt,
            "tools": tools,
            "model": model,
            "api_key": api_key,
            "credential_id": credential_id,
            "activation_type": activation_type,
            "trigger_config": trigger_config,
            "is_active": is_active
        }

    async def _handle_credentials(self, agent_params: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """
        Maneja credentials de forma híbrida (igual que workflows)
        """
        try:
            if agent_params["api_key"]:
                # Crear nueva credential con API key usando el DTO correcto
                credential_input = CredentialInputDTO(
                    provider="openai",  # Default, could be inferred from model
                    flavor="api_key",
                    client_id="agent_" + str(uuid4())[:8],  # Unique identifier
                    client_secret=agent_params["api_key"]
                )
                
                # Usar el sistema de credentials existente correctamente
                from app.repositories.credential_repository import CredentialRepository
                from app.repositories.chat_session_repository import get_chat_session_repository
                
                async for session in get_db():
                    credential_repo = CredentialRepository(session)
                    chat_repo = await get_chat_session_repository(session)
                    credential_service = CredentialService(credential_repo, chat_repo)
                    created_credential = await credential_service.register(user_id, credential_input)
                    break
                
                return {
                    "type": "created",
                    "credential_id": created_credential["id"],
                    "message": "New credential created for agent"
                }
                
            else:
                # Usar credential existente
                credential_id = agent_params["credential_id"]
                
                # TODO: Validar que la credential existe
                # credential = await getCredential(credential_id)
                # if not credential:
                #     raise HandlerError(f"Credential {credential_id} not found")
                
                return {
                    "type": "existing",
                    "credential_id": credential_id,
                    "message": "Using existing credential"
                }
                
        except Exception as e:
            raise HandlerError(f"Failed to handle credentials: {e}")

    async def _get_agent_service(self) -> AIAgentService:
        """
        Obtiene una instancia de AIAgentService para crear el agente
        """
        try:
            # Get database session
            db_session = next(get_db())
            
            # Get service with dependency injection
            return get_ai_agent_service(db_session)
        except Exception as e:
            raise HandlerError(f"Failed to initialize agent service: {e}")

    def _format_success(self, created_agent, credential_info: Dict[str, Any], start: float) -> Dict[str, Any]:
        """
        Formatea la respuesta de éxito con el agente creado
        """
        return {
            "status": "success",
            "output": {
                "message": f"AI Agent '{created_agent.name}' created successfully",
                "agent": {
                    "id": str(created_agent.agent_id),
                    "name": created_agent.name,
                    "model": created_agent.model,
                    "tools": created_agent.tools,
                    "temperature": created_agent.temperature,
                    "max_iterations": created_agent.max_iterations,
                    "status": created_agent.status,
                    "created_at": created_agent.created_at.isoformat() if created_agent.created_at else None
                },
                "credentials": credential_info,
                "next_steps": [
                    "Your agent has been created and is ready to use",
                    f"Agent ID: {created_agent.agent_id}",
                    f"Credential ID: {credential_info['credential_id']}",
                    "You can now test the agent using the 'AI_Agent.run_agent' action",
                    "The agent will use the selected model and configured credentials"
                ]
            },
            "error": None,
            "duration_ms": int((time.perf_counter() - start) * 1000),
        }

    def _format_error(self, message: str, start: float) -> Dict[str, Any]:
        """
        Formatea la respuesta de error
        """
        return {
            "status": "error",
            "output": None,
            "error": message,
            "duration_ms": int((time.perf_counter() - start) * 1000),
        }

    def get_parameter_schema(self) -> Dict[str, Any]:
        """
        Schema simplificado: solo lo que el usuario debe dar.
        Kyra ya diseñó: agent_name, agent_prompt, tools
        Usuario da: model, credentials
        """
        return {
            "type": "object",
            "required": ["model"],
            "properties": {
                # Hidden fields - Kyra proporciona estos automáticamente
                "agent_name": {
                    "type": "string",
                    "title": "Agent Name",
                    "description": "Name generated by Kyra",
                    "readOnly": True,
                    "format": "hidden"
                },
                "agent_prompt": {
                    "type": "string", 
                    "title": "Agent Prompt",
                    "description": "Prompt designed by Kyra",
                    "readOnly": True,
                    "format": "hidden"
                },
                "tools": {
                    "type": "array",
                    "title": "Tools",
                    "description": "Tools selected by Kyra",
                    "readOnly": True,
                    "format": "hidden"
                },
                
                # User input fields - Solo esto ve el usuario
                "model": {
                    "type": "string",
                    "title": "LLM Model",
                    "description": "Select the language model for this agent",
                    "format": "model_selector",  # Usa nuestro ModelSelector dropdown
                    "required": True
                },
                "api_key": {
                    "type": "string",
                    "title": "API Key (Optional)",
                    "description": "Provide new API key, or use existing credential below",
                    "format": "password",
                    "minLength": 10
                },
                "credential_id": {
                    "type": "string", 
                    "title": "Existing Credential (Optional)",
                    "description": "Or select existing credential instead of new API key",
                    "format": "credential_selector"
                }
            },
            "dependencies": {
                "api_key": {
                    "not": {"required": ["credential_id"]}
                },
                "credential_id": {
                    "not": {"required": ["api_key"]}
                }
            }
        }