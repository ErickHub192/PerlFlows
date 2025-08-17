"""
ChatCommandService - Procesa comandos especiales del chat
✅ Comandos de gestión de workflows
✅ Integración con FlowService para operaciones CRUD
✅ Respuestas formateadas para chat
"""
import logging
import re
from typing import Optional, Dict, Any, List
from uuid import UUID

from app.models.chat_models import ChatResponseModel
from app.services.flow_service import FlowService, get_flow_service
from app.repositories.flow_repository import FlowRepository
from app.services.trigger_orchestrator_service import get_trigger_orchestrator_service
from app.services.flow_definition_service import get_flow_definition_service
from app.db.database import get_db


logger = logging.getLogger(__name__)


class ChatCommandService:
    """
    Servicio para procesar comandos especiales en el chat
    
    Comandos soportados:
    - "mis workflows" / "mis flujos" - Lista workflows del usuario
    - "ejecuta [nombre]" / "correr [nombre]" - Ejecuta workflow manualmente
    - "activar [nombre]" - Activa un workflow guardado
    - "desactivar [nombre]" - Desactiva un workflow
    - "eliminar [nombre]" - Elimina un workflow
    """
    
    def __init__(self, flow_service: FlowService = None):
        self.flow_service = flow_service
    
    def is_command(self, message: str) -> bool:
        """
        Detecta si un mensaje es un comando especial
        
        Args:
            message: Mensaje del usuario
            
        Returns:
            bool: True si es un comando, False si es mensaje normal
        """
        message_lower = message.lower().strip()
        
        # Comandos de listado
        if any(phrase in message_lower for phrase in [
            "mis workflows", "mis flujos", "listar workflows", "listar flujos",
            "ver workflows", "ver flujos", "mostrar workflows", "mostrar flujos"
        ]):
            return True
            
        # Comandos de ejecución
        if any(message_lower.startswith(prefix) for prefix in [
            "ejecuta ", "correr ", "ejecutar ", "run "
        ]):
            return True
            
        # Comandos de activación/desactivación
        if any(message_lower.startswith(prefix) for prefix in [
            "activar ", "desactivar ", "activate ", "deactivate "
        ]):
            return True
            
        # Comandos de eliminación
        if any(message_lower.startswith(prefix) for prefix in [
            "eliminar ", "borrar ", "delete "
        ]):
            return True
            
        return False
    
    async def process_command(
        self, 
        message: str, 
        user_id: int, 
        chat_id: UUID,
        db_session = None
    ) -> ChatResponseModel:
        """
        Procesa un comando y retorna la respuesta apropiada
        
        Args:
            message: Comando del usuario
            user_id: ID del usuario
            chat_id: ID del chat
            db_session: Sesión de base de datos
            
        Returns:
            ChatResponseModel: Respuesta formateada del comando
        """
        try:
            # Inicializar flow_service si no existe
            if not self.flow_service and db_session:
                flow_repo = FlowRepository(db_session)
                trigger_orchestrator = get_trigger_orchestrator_service()
                definition_service = get_flow_definition_service()
                self.flow_service = FlowService(flow_repo, trigger_orchestrator, definition_service, db_session)
            
            message_lower = message.lower().strip()
            
            # Comando: Listar workflows
            if self._is_list_command(message_lower):
                return await self._handle_list_workflows(user_id)
                
            # Comando: Ejecutar workflow
            elif self._is_execute_command(message_lower):
                workflow_name = self._extract_workflow_name(message, ["ejecuta", "correr", "ejecutar", "run"])
                return await self._handle_execute_workflow(workflow_name, user_id)
                
            # Comando: Activar workflow
            elif self._is_activate_command(message_lower):
                workflow_name = self._extract_workflow_name(message, ["activar", "activate"])
                return await self._handle_activate_workflow(workflow_name, user_id, True)
                
            # Comando: Desactivar workflow
            elif self._is_deactivate_command(message_lower):
                workflow_name = self._extract_workflow_name(message, ["desactivar", "deactivate"])
                return await self._handle_activate_workflow(workflow_name, user_id, False)
                
            # Comando: Eliminar workflow
            elif self._is_delete_command(message_lower):
                workflow_name = self._extract_workflow_name(message, ["eliminar", "borrar", "delete"])
                return await self._handle_delete_workflow(workflow_name, user_id)
                
            else:
                return ChatResponseModel(
                    reply="❌ Comando no reconocido. Comandos disponibles:\n• mis workflows\n• ejecuta [nombre]\n• activar [nombre]\n• desactivar [nombre]\n• eliminar [nombre]",
                    finalize=True,
                    editable=False,
                    oauth_requirements=[],
                    steps=[]
                )
                
        except Exception as e:
            logger.error(f"Error processing command: {e}", exc_info=True)
            return ChatResponseModel(
                reply=f"❌ Error procesando comando: {str(e)}",
                finalize=True,
                editable=False,
                oauth_requirements=[],
                steps=[]
            )
    
    def _is_list_command(self, message: str) -> bool:
        """Detecta comandos de listado de workflows"""
        return any(phrase in message for phrase in [
            "mis workflows", "mis flujos", "listar workflows", "listar flujos",
            "ver workflows", "ver flujos", "mostrar workflows", "mostrar flujos"
        ])
    
    def _is_execute_command(self, message: str) -> bool:
        """Detecta comandos de ejecución de workflows"""
        return any(message.startswith(prefix) for prefix in [
            "ejecuta ", "correr ", "ejecutar ", "run "
        ])
    
    def _is_activate_command(self, message: str) -> bool:
        """Detecta comandos de activación de workflows"""
        return any(message.startswith(prefix) for prefix in [
            "activar ", "activate "
        ])
    
    def _is_deactivate_command(self, message: str) -> bool:
        """Detecta comandos de desactivación de workflows"""
        return any(message.startswith(prefix) for prefix in [
            "desactivar ", "deactivate "
        ])
    
    def _is_delete_command(self, message: str) -> bool:
        """Detecta comandos de eliminación de workflows"""
        return any(message.startswith(prefix) for prefix in [
            "eliminar ", "borrar ", "delete "
        ])
    
    def _extract_workflow_name(self, message: str, prefixes: List[str]) -> str:
        """
        Extrae el nombre del workflow del comando
        
        Args:
            message: Mensaje original
            prefixes: Lista de prefijos posibles
            
        Returns:
            str: Nombre del workflow extraído
        """
        message_lower = message.lower()
        
        for prefix in prefixes:
            if message_lower.startswith(prefix + " "):
                # Encontrar el nombre después del prefijo
                start_index = len(prefix) + 1
                workflow_name = message[start_index:].strip()
                return workflow_name
        
        return ""
    
    async def _handle_list_workflows(self, user_id: int) -> ChatResponseModel:
        """Maneja el comando de listar workflows del usuario"""
        try:
            if not self.flow_service:
                return ChatResponseModel(
                    reply="❌ Servicio de workflows no disponible",
                    finalize=True,
                    editable=False,
                    oauth_requirements=[],
                    steps=[]
                )
            
            # Obtener workflows del usuario
            workflows = await self.flow_service.get_user_flows(user_id)
            
            if not workflows:
                return ChatResponseModel(
                    reply="📝 No tienes workflows guardados aún.\n\nPuedes crear uno pidiendo ayuda para automatizar una tarea específica.",
                    finalize=True,
                    editable=False,
                    oauth_requirements=[],
                    steps=[]
                )
            
            # Formatear lista de workflows
            workflow_list = "📋 **Tus Workflows:**\n\n"
            for workflow in workflows:
                status_icon = "🟢" if workflow.is_active else "🔴"
                workflow_list += f"{status_icon} **{workflow.name}**\n"
                workflow_list += f"   • {workflow.description or 'Sin descripción'}\n"
                workflow_list += f"   • Estado: {'Activo' if workflow.is_active else 'Inactivo'}\n"
                workflow_list += f"   • Creado: {workflow.created_at.strftime('%d/%m/%Y')}\n\n"
            
            workflow_list += "\n💡 **Comandos disponibles:**\n"
            workflow_list += "• `ejecuta [nombre]` - Ejecutar manualmente\n"
            workflow_list += "• `activar [nombre]` - Activar workflow\n"
            workflow_list += "• `desactivar [nombre]` - Desactivar workflow\n"
            workflow_list += "• `eliminar [nombre]` - Eliminar workflow"
            
            return ChatResponseModel(
                reply=workflow_list,
                finalize=True,
                editable=False,
                oauth_requirements=[],
                steps=[]
            )
            
        except Exception as e:
            logger.error(f"Error listing workflows: {e}", exc_info=True)
            return ChatResponseModel(
                reply=f"❌ Error obteniendo workflows: {str(e)}",
                finalize=True,
                editable=False,
                oauth_requirements=[],
                steps=[]
            )
    
    async def _handle_execute_workflow(self, workflow_name: str, user_id: int) -> ChatResponseModel:
        """Maneja el comando de ejecutar workflow"""
        try:
            if not workflow_name:
                return ChatResponseModel(
                    reply="❌ Especifica el nombre del workflow a ejecutar.\nEjemplo: `ejecuta Mi Workflow`",
                    finalize=True,
                    editable=False,
                    oauth_requirements=[],
                    steps=[]
                )
            
            if not self.flow_service:
                return ChatResponseModel(
                    reply="❌ Servicio de workflows no disponible",
                    finalize=True,
                    editable=False,
                    oauth_requirements=[],
                    steps=[]
                )
            
            # Buscar workflow por nombre
            workflow = await self.flow_service.get_flow_by_name(user_id, workflow_name)
            
            if not workflow:
                return ChatResponseModel(
                    reply=f"❌ No se encontró el workflow '{workflow_name}'.\nUsa `mis workflows` para ver workflows disponibles.",
                    finalize=True,
                    editable=False,
                    oauth_requirements=[],
                    steps=[]
                )
            
            # Ejecutar workflow
            execution_result = await self.flow_service.execute_flow(workflow.id, user_id)
            
            return ChatResponseModel(
                reply=f"✅ Ejecutando workflow '{workflow_name}'...\n\nID de ejecución: {execution_result.get('execution_id', 'N/A')}\n\nPuedes verificar el estado en el panel de workflows.",
                finalize=True,
                editable=False,
                oauth_requirements=[],
                steps=[]
            )
            
        except Exception as e:
            logger.error(f"Error executing workflow: {e}", exc_info=True)
            return ChatResponseModel(
                reply=f"❌ Error ejecutando workflow: {str(e)}",
                finalize=True,
                editable=False,
                oauth_requirements=[],
                steps=[]
            )
    
    async def _handle_activate_workflow(self, workflow_name: str, user_id: int, activate: bool) -> ChatResponseModel:
        """Maneja comandos de activar/desactivar workflow"""
        try:
            if not workflow_name:
                action = "activar" if activate else "desactivar"
                return ChatResponseModel(
                    reply=f"❌ Especifica el nombre del workflow a {action}.\nEjemplo: `{action} Mi Workflow`",
                    finalize=True,
                    editable=False,
                    oauth_requirements=[],
                    steps=[]
                )
            
            if not self.flow_service:
                return ChatResponseModel(
                    reply="❌ Servicio de workflows no disponible",
                    finalize=True,
                    editable=False,
                    oauth_requirements=[],
                    steps=[]
                )
            
            # Buscar workflow por nombre
            workflow = await self.flow_service.get_flow_by_name(user_id, workflow_name)
            
            if not workflow:
                return ChatResponseModel(
                    reply=f"❌ No se encontró el workflow '{workflow_name}'.\nUsa `mis workflows` para ver workflows disponibles.",
                    finalize=True,
                    editable=False,
                    oauth_requirements=[],
                    steps=[]
                )
            
            # Cambiar estado del workflow
            await self.flow_service.toggle_flow_active(workflow.id, activate, user_id)
            
            action_text = "activado" if activate else "desactivado"
            status_icon = "🟢" if activate else "🔴"
            
            return ChatResponseModel(
                reply=f"{status_icon} Workflow '{workflow_name}' {action_text} exitosamente.",
                finalize=True,
                editable=False,
                oauth_requirements=[],
                steps=[]
            )
            
        except Exception as e:
            logger.error(f"Error toggling workflow: {e}", exc_info=True)
            return ChatResponseModel(
                reply=f"❌ Error modificando workflow: {str(e)}",
                finalize=True,
                editable=False,
                oauth_requirements=[],
                steps=[]
            )
    
    async def _handle_delete_workflow(self, workflow_name: str, user_id: int) -> ChatResponseModel:
        """Maneja el comando de eliminar workflow"""
        try:
            if not workflow_name:
                return ChatResponseModel(
                    reply="❌ Especifica el nombre del workflow a eliminar.\nEjemplo: `eliminar Mi Workflow`",
                    finalize=True,
                    editable=False,
                    oauth_requirements=[],
                    steps=[]
                )
            
            if not self.flow_service:
                return ChatResponseModel(
                    reply="❌ Servicio de workflows no disponible",
                    finalize=True,
                    editable=False,
                    oauth_requirements=[],
                    steps=[]
                )
            
            # Buscar workflow por nombre
            workflow = await self.flow_service.get_flow_by_name(user_id, workflow_name)
            
            if not workflow:
                return ChatResponseModel(
                    reply=f"❌ No se encontró el workflow '{workflow_name}'.\nUsa `mis workflows` para ver workflows disponibles.",
                    finalize=True,
                    editable=False,
                    oauth_requirements=[],
                    steps=[]
                )
            
            # Eliminar workflow
            await self.flow_service.delete_flow(workflow.id, user_id)
            
            return ChatResponseModel(
                reply=f"🗑️ Workflow '{workflow_name}' eliminado exitosamente.",
                finalize=True,
                editable=False,
                oauth_requirements=[],
                steps=[]
            )
            
        except Exception as e:
            logger.error(f"Error deleting workflow: {e}", exc_info=True)
            return ChatResponseModel(
                reply=f"❌ Error eliminando workflow: {str(e)}",
                finalize=True,
                editable=False,
                oauth_requirements=[],
                steps=[]
            )


# Factory function for dependency injection
async def get_chat_command_service(db_session = None) -> ChatCommandService:
    """Factory function para ChatCommandService"""
    try:
        if db_session:
            # Crear FlowService con dependencias
            flow_repo = FlowRepository(db_session)
            trigger_orchestrator = get_trigger_orchestrator_service()
            definition_service = get_flow_definition_service()
            flow_service = FlowService(flow_repo, trigger_orchestrator, definition_service, db_session)
            
            return ChatCommandService(flow_service)
        else:
            # Sin sesión de DB, crear servicio básico
            return ChatCommandService()
            
    except Exception as e:
        logger.error(f"Error creating ChatCommandService: {e}", exc_info=True)
        return ChatCommandService()