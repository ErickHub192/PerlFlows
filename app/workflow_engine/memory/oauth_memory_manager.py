"""
OAuth Memory Manager - Sistema modular para gestión de memoria OAuth
Arquitectura LEGO: Bloques intercambiables que funcionan en cualquier flujo
"""
import logging
from typing import List, Dict, Any, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class OAuthMemoryEvent(Enum):
    """Eventos del ciclo de vida OAuth"""
    CREDENTIALS_DETECTED = "credentials_detected"
    OAUTH_REQUIRED = "oauth_required" 
    OAUTH_COMPLETED = "oauth_completed"
    CREDENTIALS_REFRESHED = "credentials_refreshed"


@dataclass
class OAuthState:
    """Estado completo de OAuth para un chat"""
    satisfied_services: Set[str]
    required_services: Set[str] 
    pending_services: Set[str]
    failed_services: Set[str]
    
    @property
    def is_fully_satisfied(self) -> bool:
        """¿Todos los servicios requeridos están satisfechos?"""
        return len(self.pending_services) == 0 and len(self.failed_services) == 0
    
    @property
    def completion_percentage(self) -> float:
        """Porcentaje de completitud OAuth"""
        if not self.required_services:
            return 100.0
        return (len(self.satisfied_services) / len(self.required_services)) * 100.0


class OAuthMemoryManager:
    """
    🧱 BLOQUE LEGO: Gestión unificada de memoria OAuth
    
    Responsabilidades:
    - Detectar estado OAuth actual
    - Persistir cambios en memoria
    - Proporcionar contexto al LLM
    - Manejar todas las variantes de flujo
    """
    
    def __init__(self, memory_service, logger_instance=None):
        self.memory_service = memory_service
        self.logger = logger_instance or logger
        
    async def detect_oauth_state(
        self,
        db_session: AsyncSession,
        chat_id: str,
        user_id: int,
        planned_steps: List[Dict[str, Any]],
        auto_auth_trigger
    ) -> OAuthState:
        """
        🔍 DETECCIÓN UNIFICADA: Analiza el estado OAuth completo
        Funciona para TODAS las variantes de flujo
        """
        self.logger.info(f"🔍 OAUTH STATE DETECTION: Starting for chat {chat_id}")
        
        # Extraer servicios requeridos de los steps
        required_services = set()
        auth_required_steps = []
        
        for step in planned_steps:
            default_auth = step.get('default_auth')
            if default_auth:
                auth_required_steps.append(step)
                # Extraer nombre del servicio del auth string (ej: oauth2_gmail -> gmail)
                service_name = self._extract_service_name(default_auth)
                if service_name:
                    required_services.add(service_name)
        
        self.logger.info(f"🔍 REQUIRED SERVICES: {required_services}")
        
        # Verificar estado actual de cada servicio
        satisfied_services = set()
        pending_services = set()
        failed_services = set()
        
        if auto_auth_trigger and auth_required_steps:
            # Usar AutoAuthTrigger para verificar cada servicio
            oauth_requirements = await auto_auth_trigger.check_missing_oauth_for_selected_steps(
                user_id, auth_required_steps, chat_id
            )
            
            # Los servicios que NO están en oauth_requirements están satisfied
            required_auth_services = {req.service_id for req in oauth_requirements}
            satisfied_services = required_services - required_auth_services
            pending_services = required_auth_services
            
            self.logger.info(f"🔍 OAUTH DETECTION RESULT:")
            self.logger.info(f"  - Satisfied: {satisfied_services}")
            self.logger.info(f"  - Pending: {pending_services}")
            self.logger.info(f"  - Failed: {failed_services}")
        
        return OAuthState(
            satisfied_services=satisfied_services,
            required_services=required_services,
            pending_services=pending_services,
            failed_services=failed_services
        )
    
    async def process_oauth_event(
        self,
        event: OAuthMemoryEvent,
        db_session: AsyncSession,
        chat_id: str,
        user_id: int,
        oauth_state: OAuthState,
        event_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        🔇 PROCESAMIENTO SILENCIOSO: Solo persiste, NO genera contexto para LLM
        Bloque LEGO que solo guarda estado en memoria
        """
        self.logger.info(f"🔇 OAUTH EVENT (SILENT): {event.value} for chat {chat_id}")
        
        result = {
            "event": event.value,
            "actions_taken": [],
            "memory_updated": False
        }
        
        try:
            if event == OAuthMemoryEvent.CREDENTIALS_DETECTED:
                await self._handle_credentials_detected(
                    db_session, chat_id, user_id, oauth_state, result
                )
                
            elif event == OAuthMemoryEvent.OAUTH_REQUIRED:
                await self._handle_oauth_required(
                    db_session, chat_id, user_id, oauth_state, result
                )
                
            elif event == OAuthMemoryEvent.OAUTH_COMPLETED:
                await self._handle_oauth_completed(
                    db_session, chat_id, user_id, oauth_state, result, event_data
                )
                
            elif event == OAuthMemoryEvent.CREDENTIALS_REFRESHED:
                await self._handle_credentials_refreshed(
                    db_session, chat_id, user_id, oauth_state, result
                )
            
            # ❌ REMOVIDO: NO generar contexto LLM aquí - solo persistir
            
            self.logger.info(f"✅ OAUTH EVENT PERSISTED: {len(result['actions_taken'])} actions, no LLM context generated")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ OAUTH EVENT ERROR: {e}")
            result["error"] = str(e)
            return result
    
    async def _handle_credentials_detected(
        self, db_session, chat_id, user_id, oauth_state, result
    ):
        """Maneja cuando se detectan credenciales existentes"""
        if oauth_state.satisfied_services:
            # Persistir en memoria
            await self.memory_service.save_oauth_completion(
                db_session, chat_id, user_id, list(oauth_state.satisfied_services)
            )
            result["actions_taken"].append("saved_oauth_completion_memory")
            result["memory_updated"] = True
            
            self.logger.info(f"💾 CREDENTIALS DETECTED: Saved {len(oauth_state.satisfied_services)} services to memory")
    
    async def _handle_oauth_required(
        self, db_session, chat_id, user_id, oauth_state, result  
    ):
        """Maneja cuando se requiere OAuth"""
        if oauth_state.pending_services:
            # Opcional: Guardar estado de servicios pendientes
            result["actions_taken"].append("oauth_required_identified")
            
            self.logger.info(f"🔐 OAUTH REQUIRED: {len(oauth_state.pending_services)} services need auth")
    
    async def _handle_oauth_completed(
        self, db_session, chat_id, user_id, oauth_state, result, event_data
    ):
        """Maneja cuando OAuth se completa"""
        completed_services = event_data.get("completed_services", []) if event_data else []
        
        if completed_services:
            # Actualizar estado
            oauth_state.satisfied_services.update(completed_services)
            oauth_state.pending_services -= set(completed_services)
            
            # Persistir en memoria
            await self.memory_service.save_oauth_completion(
                db_session, chat_id, user_id, list(oauth_state.satisfied_services)
            )
            result["actions_taken"].append("oauth_completion_saved")
            result["memory_updated"] = True
            
            self.logger.info(f"✅ OAUTH COMPLETED: Saved {len(completed_services)} newly completed services")
    
    async def _handle_credentials_refreshed(
        self, db_session, chat_id, user_id, oauth_state, result
    ):
        """Maneja cuando se refrescan credenciales"""
        # Similar a credentials_detected pero con logging diferente
        await self._handle_credentials_detected(db_session, chat_id, user_id, oauth_state, result)
        result["actions_taken"].append("credentials_refreshed")
        
        self.logger.info(f"🔄 CREDENTIALS REFRESHED: Updated memory state") 
    
    def _build_llm_context(self, oauth_state: OAuthState) -> Dict[str, Any]:
        """
        🧠 CONTEXTO ESTANDARIZADO: Construye contexto unificado para el LLM
        """
        return {
            "oauth_completed_services": list(oauth_state.satisfied_services),
            "oauth_pending_services": list(oauth_state.pending_services),
            "oauth_failed_services": list(oauth_state.failed_services),
            "oauth_completion_percentage": oauth_state.completion_percentage,
            "oauth_fully_satisfied": oauth_state.is_fully_satisfied,
            "oauth_status": self._get_oauth_status_string(oauth_state)
        }
    
    def _get_oauth_status_string(self, oauth_state: OAuthState) -> str:
        """Genera string descriptivo del estado OAuth"""
        if oauth_state.is_fully_satisfied:
            return "all_services_authenticated"
        elif oauth_state.satisfied_services and oauth_state.pending_services:
            return "partially_authenticated"
        elif oauth_state.pending_services:
            return "authentication_required"
        else:
            return "no_authentication_needed"
    
    def _extract_service_name(self, auth_string: str) -> Optional[str]:
        """Extrae nombre del servicio del auth string (ej: oauth2_gmail -> gmail)"""
        if not auth_string:
            return None
            
        # Patrones comunes
        if auth_string.startswith("oauth2_"):
            return auth_string.replace("oauth2_", "")
        elif auth_string.startswith("oauth_"):
            return auth_string.replace("oauth_", "")
        elif auth_string.startswith("api_key_"):
            return auth_string.replace("api_key_", "")
        else:
            return auth_string
    
    async def get_current_memory_state(
        self, db_session: AsyncSession, chat_id: str
    ) -> Dict[str, Any]:
        """
        📖 ESTADO ACTUAL: Lee el estado actual de memoria OAuth
        """
        try:
            memory_context = await self.memory_service.load_memory_context(db_session, chat_id)
            return {
                "oauth_completed_services": memory_context.get("oauth_completed_services", []),
                "smart_forms_generated": memory_context.get("smart_forms_generated", []),
                "user_inputs_provided": memory_context.get("user_inputs_provided", {}),
                "selected_services": memory_context.get("selected_services", [])
            }
        except Exception as e:
            self.logger.error(f"❌ ERROR reading memory state: {e}")
            return {
                "oauth_completed_services": [],
                "smart_forms_generated": [],
                "user_inputs_provided": {},
                "selected_services": []
            }


# 🏭 FACTORY: Crear instancias del manager
def create_oauth_memory_manager(memory_service, logger_instance=None):
    """Factory para crear OAuthMemoryManager"""
    return OAuthMemoryManager(memory_service, logger_instance)