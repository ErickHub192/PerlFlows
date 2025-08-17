# app/services/ITriggerOrchestratorService.py

from abc import ABC, abstractmethod
from typing import Dict, Any
from uuid import UUID


class ITriggerOrchestratorService(ABC):
    """
    Interface para el servicio de orquestación de triggers.
    Maneja la programación y cancelación de triggers de flujos.
    """

    @abstractmethod
    async def schedule_flow(
        self, 
        flow_id: UUID, 
        spec: Dict[str, Any], 
        user_id: int
    ) -> None:
        """
        Programa un flujo para ejecución automática basado en su spec.
        
        Args:
            flow_id: ID del flujo a programar
            spec: Especificación del flujo con triggers
            user_id: ID del usuario propietario
        """
        pass

    @abstractmethod
    async def unschedule_flow(
        self, 
        flow_id: UUID, 
        spec: Dict[str, Any], 
        user_id: int
    ) -> None:
        """
        Cancela la programación de un flujo.
        
        Args:
            flow_id: ID del flujo a desprogramar
            spec: Especificación del flujo
            user_id: ID del usuario propietario
        """
        pass