# app/services/agent_deployment_service.py

import logging
from typing import Dict, Any
from uuid import UUID

from fastapi import HTTPException, Depends

from app.services.IAgentDeploymentService import IAgentDeploymentService
from app.services.ai_agent_service import get_ai_agent_service, AIAgentService
from app.dtos.ai_agent_deploy_request_dto import AIAgentDeployRequestDTO
from app.repositories.telegram_credential_repository import (
    TelegramCredentialRepository, 
    get_telegram_repo
)
from app.routers.ai_agent_deployers import CHANNEL_DEPLOYERS
from app.db.models import AIAgent

logger = logging.getLogger(__name__)


async def get_agent_deployment_service(
    agent_service: AIAgentService = Depends(get_ai_agent_service),
    telegram_repo: TelegramCredentialRepository = Depends(get_telegram_repo)
) -> IAgentDeploymentService:
    """
    Factory para inyectar AgentDeploymentService en FastAPI
    """
    return AgentDeploymentService(agent_service, telegram_repo)


class AgentDeploymentService(IAgentDeploymentService):
    """
    Servicio que maneja el deployment de agentes AI en diferentes canales.
    
    RESPONSABILIDADES:
    - Validar existencia de agentes
    - Validar canales soportados
    - Orquestar el proceso de deployment
    - Manejo de errores específicos de deployment
    """
    
    def __init__(
        self, 
        agent_service: AIAgentService,
        telegram_repo: TelegramCredentialRepository
    ):
        self.agent_service = agent_service
        self.telegram_repo = telegram_repo
    
    async def deploy_agent(
        self, 
        agent_id: UUID, 
        deploy_request: AIAgentDeployRequestDTO
    ) -> Dict[str, Any]:
        """
        ✅ LÓGICA DE NEGOCIO: Deployment de agentes movida desde router
        """
        try:
            # 1) Validar que el agente existe
            agent = await self._get_agent_for_deployment(agent_id)
            
            # 2) Validar que el canal es soportado
            deployer = await self._get_channel_deployer(deploy_request.channel)
            
            # 3) Ejecutar deployment
            logger.info(f"Desplegando agente {agent_id} en canal {deploy_request.channel}")
            result = await deployer(agent, self.telegram_repo, deploy_request)
            
            return result
            
        except HTTPException:
            # Re-raise HTTP exceptions (validation errors)
            raise
        except Exception as e:
            logger.error(f"Error deploying agent {agent_id}: {e}")
            raise HTTPException(
                status_code=500, 
                detail=f"Error durante deployment: {str(e)}"
            )
    
    async def _get_agent_for_deployment(self, agent_id: UUID):
        """
        Obtiene el agente y valida que existe para deployment.
        """
        # Usar el repository directamente para obtener el modelo completo
        # (el AIAgentService devuelve DTOs, pero el deployer necesita el modelo)
        agent = await self.telegram_repo.db.get(AIAgent, agent_id)
        
        if agent is None:
            logger.error(f"Agente {agent_id} no encontrado para deployment")
            raise HTTPException(
                status_code=404, 
                detail="Agente no encontrado"
            )
            
        return agent
    
    async def _get_channel_deployer(self, channel: str):
        """
        Obtiene el deployer para el canal especificado.
        """
        deployer = CHANNEL_DEPLOYERS.get(channel)
        
        if not deployer:
            logger.error(f"Canal {channel} no soportado")
            raise HTTPException(
                status_code=400, 
                detail="Canal no soportado"
            )
            
        return deployer