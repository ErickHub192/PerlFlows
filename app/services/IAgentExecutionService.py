# app/services/IAgentExecutionService.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from uuid import UUID


class IAgentExecutionService(ABC):
    """
    Interface para el servicio de ejecución de agentes.
    Maneja la ejecución de agentes AI con validación, tracking de costos y analytics.
    """

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
        """
        Ejecuta un agente con validación consolidada, tracking de costos y analytics de uso.
        
        Args:
            agent_id: ID del agente a ejecutar
            user_prompt: Prompt del usuario
            user_id: ID del usuario (opcional)
            temperature: Temperatura para el modelo LLM (opcional)
            max_iterations: Máximo número de iteraciones (opcional)
            api_key: API key para el modelo (opcional)
            session_id: ID de sesión (opcional)
            
        Returns:
            Dict con resultado de la ejecución, métricas y costos
            
        Raises:
            InvalidDataException: Si los datos de entrada son inválidos
            WorkflowProcessingException: Si hay errores durante la ejecución
        """
        pass