# app/services/IAgentDeploymentService.py

from abc import ABC, abstractmethod
from typing import Dict, Any
from uuid import UUID

from app.dtos.ai_agent_deploy_request_dto import AIAgentDeployRequestDTO


class IAgentDeploymentService(ABC):
    """
    Interface para el servicio de deployment de agentes.
    Maneja el despliegue de agentes AI en diferentes canales.
    """

    @abstractmethod
    async def deploy_agent(
        self, 
        agent_id: UUID, 
        deploy_request: AIAgentDeployRequestDTO
    ) -> Dict[str, Any]:
        """
        Despliega un agente AI en el canal especificado.
        
        Args:
            agent_id: ID del agente a desplegar
            deploy_request: Configuración del deployment
            
        Returns:
            Dict con información del deployment exitoso
            
        Raises:
            HTTPException: Si el agente no existe o el canal no es soportado
        """
        pass