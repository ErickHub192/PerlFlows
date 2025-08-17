# app/services/IWorkflowRunner_service.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
from uuid import UUID

from app.dtos.workflow_result_dto import WorkflowResultDTO


class IWorkflowRunnerService(ABC):
    """
    Interface para el servicio de ejecución de workflows.
    Maneja la ejecución de pasos de workflow con manejo de errores.
    """

    @abstractmethod
    async def run_workflow(
        self,
        steps: List[Dict[str, Any]],
        user_id: int,
        flow_id: UUID = None,
        inputs: Dict[str, Any] = None,
        simulate: bool = False
    ) -> Tuple[UUID, WorkflowResultDTO]:
        """
        Ejecuta un workflow con los pasos especificados.
        
        Args:
            steps: Lista de pasos del workflow a ejecutar
            user_id: ID del usuario que ejecuta el workflow
            flow_id: ID del flujo (opcional)
            inputs: Inputs para el workflow
            simulate: Si True, ejecuta en modo simulación
            
        Returns:
            Tuple con execution_id y WorkflowResultDTO
        """
        pass