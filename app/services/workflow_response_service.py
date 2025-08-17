"""
WorkflowResponseService - Servicio para crear y guardar respuestas de workflow
Centraliza la lógica de formateo de respuestas y guardado en memoria persistente
"""
import logging
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.workflow_engine.core.interfaces import WorkflowCreationResult
from app.services.conversation_memory_service import get_conversation_memory_service

logger = logging.getLogger(__name__)


class WorkflowResponseService:
    """
    Servicio para manejar respuestas de workflow y su persistencia
    """
    
    def __init__(self):
        self.memory_service = get_conversation_memory_service()
    
    async def save_workflow_result_to_memory(
        self, 
        db_session: Session, 
        user_id: int, 
        context: Dict[str, Any], 
        result: WorkflowCreationResult,
        extra_info: str = "",
        chat_id: str = None
    ):
        """
        Helper para guardar respuesta del WorkflowResult en memoria persistente
        """
        # Obtener chat_id desde múltiples fuentes
        actual_chat_id = chat_id or (context.get('chat_id') if context else None)
        
        if actual_chat_id and result:
            # Crear resumen de la respuesta
            steps_count = len(result.steps) if result.steps else 0
            workflow_type = result.workflow_type.value if result.workflow_type else "unknown"
            confidence = getattr(result, 'confidence', 'unknown')
            
            response_summary = f"Workflow: {steps_count} pasos, tipo: {workflow_type}, confianza: {confidence}"
            if extra_info:
                response_summary += f" - {extra_info}"
            
            if result.steps:
                step_names = [step.get('action_name', 'unknown') for step in result.steps[:3]]
                response_summary += f" - Pasos: {', '.join(step_names)}"
                if len(result.steps) > 3:
                    response_summary += f" y {len(result.steps) - 3} más"
            
            await self.memory_service.save_assistant_response(db_session, actual_chat_id, user_id, response_summary)
            logger.debug(f"🧠 MEMORIA: Guardada respuesta del workflow")
        else:
            logger.debug(f"🧠 MEMORIA: Sin chat_id para guardar respuesta")
    
    def create_workflow_summary(self, result: WorkflowCreationResult, extra_context: str = "") -> str:
        """
        Crea un resumen legible de un WorkflowResult para persistencia
        """
        if not result:
            return "Workflow: Sin resultado"
        
        steps_count = len(result.steps) if result.steps else 0
        workflow_type = result.workflow_type.value if result.workflow_type else "unknown"
        confidence = getattr(result, 'confidence', 'unknown')
        
        summary = f"Workflow {workflow_type}: {steps_count} pasos, confianza: {confidence}"
        
        if extra_context:
            summary += f" - {extra_context}"
        
        if result.steps and steps_count > 0:
            # Agregar nombres de los primeros pasos
            step_names = []
            for step in result.steps[:3]:
                step_name = step.get('action_name', step.get('name', 'unknown'))
                step_names.append(step_name)
            
            summary += f" | Pasos: {', '.join(step_names)}"
            if steps_count > 3:
                summary += f" y {steps_count - 3} más"
        
        return summary


# Singleton instance
_workflow_response_service = None

def get_workflow_response_service() -> WorkflowResponseService:
    """
    Obtiene la instancia singleton del WorkflowResponseService
    """
    global _workflow_response_service
    if _workflow_response_service is None:
        _workflow_response_service = WorkflowResponseService()
    return _workflow_response_service