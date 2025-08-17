"""
ChatService - CLEAN VERSION con RESPONSABILIDAD ÚNICA
✅ Solo coordinación de mensajes
✅ Dependency injection apropiada  
✅ Sin responsabilidades mixtas
✅ Event-driven LLM calls
"""
import logging
import json
from typing import Any, List, Dict, Union, Optional
from uuid import UUID

from fastapi import Depends

from app.core.config import settings
from app.workflow_engine.constants.workflow_statuses import WorkflowStatus, WorkflowStatusGroups
from app.models.chat_models import ChatResponseModel
from app.models.form_payload import FormPayload
from app.models.clarify_models import ClarifyPayload
from app.services.IChat_service import IChatService
from app.exceptions.api_exceptions import InvalidDataException
from app.ai.llm_clients.llm_service import get_llm_service, LLMService
from app.services.chat_session_service import ChatSessionService, get_chat_session_service

# ✅ SEPARACIÓN LIMPIA: Solo import de coordinadores específicos
from app.dependencies.workflow_dependencies import get_simple_workflow_engine

logger = logging.getLogger(__name__)


class ChatService(IChatService):
    """
    ✅ RESPONSABILIDAD ÚNICA: Coordinación de mensajes
    
    SOLO SE ENCARGA DE:
    - Coordinar mensajes del usuario con WorkflowEngine
    - Formatear respuestas  
    - Persistir conversaciones
    - 🎯 EVENT-DRIVEN: LLM calls solo cuando es necesario
    
    NO SE ENCARGA DE (delegado a otros servicios):
    - Setup de WorkflowEngine (delegado a factory)
    - Reflection logic (delegado a ReflectionCoordinator)
    - Credential management (delegado a CredentialService)
    - OAuth verification (delegado a UnifiedOAuthManager)
    """
    
    def __init__(
        self,
        llm_service: LLMService,
        chat_session_service: ChatSessionService,
    ):
        self.llm = llm_service
        self.chat_session_service = chat_session_service
        # ✅ FIX: WorkflowEngine se obtiene dinámicamente con chat_id, no como dependencia fija
        
        # ✅ DEPENDENCY INJECTION: Todas las dependencias vienen del constructor
    
    async def _should_delegate_to_workflow_engine(self, context: Dict[str, Any] = None, user_message: str = "") -> bool:
        """
        🎯 DELEGATION CHECK: Determina si debe delegar al WorkflowEngine
        
        SIEMPRE delegar excepto para casos muy específicos donde necesitamos respuesta inmediata
        WorkflowEngine tiene la lógica completa de state management
        """
        # OAuth completion automático sin interacción usuario - manejar directamente
        if (context and context.get("continue_workflow") and 
            context.get("oauth_completed") and 
            not user_message.strip()):
            logger.info("🔇 DIRECT OAUTH: Handling OAuth completion directly, no workflow engine needed")
            return False
            
        # Por defecto SIEMPRE delegar al WorkflowEngine (fuente de verdad)
        return True
    
    async def _handle_direct_oauth_completion(self, context: Dict[str, Any]) -> ChatResponseModel:
        """
        🔇 DIRECT OAUTH: Maneja OAuth completion directamente sin WorkflowEngine
        Solo para casos donde necesitamos respuesta inmediata sin procesamiento LLM
        """
        oauth_services = context.get("oauth_completed", [])
        service_names = ", ".join(oauth_services) if oauth_services else "servicios"
        
        return ChatResponseModel(
            reply=f"🔐 Autorización completada para {service_names}. Procesando información...",
            finalize=False,
            editable=False,
            oauth_requirements=[],
            steps=[],
            status="oauth_completed_silent"
        )

    async def handle_message(
        self, 
        chat_id: UUID, 
        user_message: str, 
        user_id: int,
        context: Dict[str, Any] = None,
        db_session = None
    ) -> ChatResponseModel:
        """
        ✅ EVENT-DRIVEN: State check antes de llamar al LLM
        🎯 SMART ROUTING: LLM solo cuando es necesario
        """
        try:
            logger.info(f"Processing message for chat {chat_id}, user {user_id}")
            
            # 🎯 DELEGATION CHECK: Verificar si debe delegar al WorkflowEngine
            if not await self._should_delegate_to_workflow_engine(context, user_message):
                logger.info("🔇 DIRECT MODE: Handling OAuth completion directly without WorkflowEngine")
                return await self._handle_direct_oauth_completion(context)
            
            # 💾 BD-FIRST: Guardar mensaje del usuario INMEDIATAMENTE
            logger.info(f"💾 BD-FIRST: Saving user message to database before LLM processing")
            await self._save_user_message_immediately(chat_id, user_message)
            
            # 🆕 STEP 3.5: Verificar si es un comando de gestión de workflows
            from app.services.chat_command_service import ChatCommandService
            command_service = ChatCommandService()
            
            if command_service.is_command(user_message):
                logger.info(f"🎯 COMMAND: Processing workflow management command")
                try:
                    command_result = await command_service.process_command(
                        message=user_message,
                        user_id=user_id,
                        chat_id=chat_id,
                        db_session=db_session
                    )
                    
                    # ✅ Retornar respuesta del comando
                    return command_result
                    
                except Exception as e:
                    logger.error(f"Error processing command: {e}", exc_info=True)
                    # Continuar con workflow engine si el comando falla
            
            
            # 🧠 UNIFIED PATH: Todos los mensajes van al mismo workflow engine
            # El LLM planner usará la memoria para saber si continuar o crear nuevo workflow
            logger.info(f"🔄 UNIFIED: All messages go through workflow engine with memory context")
            
            try:
                # 1. ✅ FIX: Obtener WorkflowEngine dinámicamente con chat_id específico
                workflow_engine = await get_simple_workflow_engine(chat_id=str(chat_id))
                
                # 🔥 NUEVO FLUJO MVP: Ya no hay post-OAuth, todo es lineal
                
                # 2. ✅ Delegar procesamiento completo al WorkflowEngine (SOLO para nuevos workflows)
                logger.info(f"🔮 KYRA: Processing user request for user_id: {user_id}")
                logger.info(f"🔮 KYRA: User message: {user_message[:200]}...")
                
                # 🎯 SMARTFORM DETECTION: Check if user is submitting form data
                if self._is_smartform_submission(user_message):
                    logger.info("🎯 SMARTFORM: Detected SmartForm submission, processing data...")
                    try:
                        form_data = self._extract_smartform_data(user_message)
                        if form_data:
                            # Save user inputs to conversation memory
                            await self._save_smartform_data_to_memory(db_session, chat_id, user_id, form_data)
                            logger.info(f"🎯 SMARTFORM: Saved form data to conversation memory: {list(form_data.keys())}")
                            logger.info("🎯 SMARTFORM: Continuing with normal LLM processing to use the saved data...")
                            
                            # DON'T return early - let the LLM process with the updated memory context
                            
                    except Exception as e:
                        logger.error(f"🎯 SMARTFORM ERROR: Failed to process form data: {e}")
                        # Return error response for SmartForm processing
                        response = ChatResponseModel(
                            reply="❌ Hubo un problema procesando los datos del formulario. Por favor, intenta enviarlos nuevamente.",
                            status="error"
                        )
                        await self._persist_conversation(chat_id, user_message, response, user_id)
                        return response
                
                # ✅ FIX: Cargar historial completo para contexto del LLM
                # El historial es importante para continuidad
                workflow_context = {
                    "conversation": context.get("conversation", []) if context else [],  # Usar del frontend si está disponible
                    "workflow_type": context.get("workflow_type") if context else None,
                    "selected_services": context.get("selected_services") if context else None,
                    "chat_id": chat_id,  # Contexto de chat
                    # 🚨 NEW: OAuth system message injection context
                    "oauth_completed": context.get("oauth_completed") if context else None,
                    "system_message": context.get("system_message") if context else None,
                    "continue_workflow": context.get("continue_workflow", False) if context else False
                }
                logger.info(f"🧠 MEMORY: Loading complete conversation history for context")
                
                # ✅ DELEGATION: OAuth system message injection is now handled by WorkflowEngine
                
                result = await workflow_engine.create_workflow_from_intent_with_context(
                    user_message=user_message,
                    user_id=user_id,
                    context=workflow_context,
                    db_session=db_session
                )
            finally:
                # ✅ Process completed
                pass
            
            logger.info(f"🔮 KYRA: Raw result type: {type(result)}")
            logger.info(f"🔮 KYRA: Raw result status: {getattr(result, 'status', 'no status')}")
            logger.info(f"🔮 KYRA: Raw result steps count: {len(getattr(result, 'steps', []))}")
            
            if hasattr(result, 'steps') and result.steps:
                for i, step in enumerate(result.steps):
                    logger.info(f"🔮 KYRA: Step {i}: action_name={getattr(step, 'action_name', 'none')}")
                    if hasattr(step, 'params') and step.params:
                        logger.info(f"🔮 KYRA: Step {i} params keys: {list(step.params.keys()) if isinstance(step.params, dict) else 'not dict'}")
            
            # 3. ✅ Solo formatear respuesta (responsabilidad única)
            response = self._format_workflow_response(result)
            
            logger.info(f"🔮 KYRA: Formatted response type: {type(response)}")
            logger.info(f"🔮 KYRA: Formatted response reply: {getattr(response, 'reply', 'no reply')[:100]}...")
            logger.info(f"🔮 KYRA: Formatted response has steps: {hasattr(response, 'steps')}")
            logger.info(f"🔮 KYRA: Formatted response finalize: {getattr(response, 'finalize', False)}")
            
            # ✅ Response ready for return
            
            # 3.5. ✨ Carl translator - Convertir respuesta técnica a natural
            try:
                logger.info(f"🤖 CARL: Starting translation process...")
                
                from app.services.carl_translator_service import get_carl_translator
                carl = get_carl_translator()
                
                # Convertir result a dict para Carl (puede ser un objeto)
                if isinstance(result, dict):
                    result_dict = result
                    logger.info(f"🤖 CARL: Result is already dict")
                else:
                    logger.info(f"🤖 CARL: Converting result object to dict...")
                    # Convertir objeto a dict manejando StepMetaDTO y otros objetos
                    result_dict = {
                        "steps": [],
                        "confidence": getattr(result, 'confidence', 0.5),
                        "oauth_requirements": getattr(result, 'oauth_requirements', []),
                        "errors": getattr(result, 'errors', []),
                        "status": getattr(result, 'status', 'unknown'),
                        "metadata": getattr(result, 'metadata', {}),
                        "service_groups": getattr(result, 'metadata', {}).get('service_groups', []) if hasattr(result, 'metadata') else [],
                        # 🎯 WORKFLOW REVIEW: Include workflow review fields for Carl
                        "message": getattr(result, 'message', None),
                        "workflow_summary": getattr(result, 'workflow_summary', None),
                        "approval_message": getattr(result, 'approval_message', None)
                    }
                    
                    # 🎯 WORKFLOW REVIEW: Extract workflow review fields from metadata if not found directly
                    result_metadata = getattr(result, 'metadata', {})
                    if isinstance(result_metadata, dict):
                        if not result_dict["message"] and result_metadata.get("message"):
                            result_dict["message"] = result_metadata.get("message")
                        if not result_dict["workflow_summary"] and result_metadata.get("workflow_summary"):
                            result_dict["workflow_summary"] = result_metadata.get("workflow_summary")
                        if not result_dict["approval_message"] and result_metadata.get("approval_message"):
                            result_dict["approval_message"] = result_metadata.get("approval_message")
                    
                    # Convert oauth_requirements to dict for Carl
                    oauth_reqs = []
                    for req in result_dict["oauth_requirements"]:
                        if hasattr(req, 'model_dump'):
                            oauth_reqs.append(req.model_dump())
                        elif isinstance(req, dict):
                            oauth_reqs.append(req)
                        else:
                            oauth_reqs.append({
                                "type": getattr(req, 'type', 'oauth'),
                                "message": getattr(req, 'message', 'Authorization required'),
                                "oauth_url": getattr(req, 'oauth_url', '/auth/service/authorize')
                            })
                    result_dict["oauth_requirements"] = oauth_reqs
                    
                    # Convertir steps si existen
                    steps = getattr(result, 'steps', [])
                    if steps:
                        logger.info(f"🤖 CARL: Converting {len(steps)} steps...")
                        converted_steps = []
                        for step in steps:
                            if hasattr(step, '__dict__'):
                                # Convertir objeto a dict
                                step_dict = {
                                    "action_name": getattr(step, 'action_name', ''),
                                    "node_name": getattr(step, 'node_name', ''),
                                    "params": getattr(step, 'params', {}),
                                    "node_id": str(getattr(step, 'node_id', '')),
                                    "action_id": str(getattr(step, 'action_id', ''))
                                }
                                logger.info(f"🤖 CARL: Step converted - action_name: {step_dict['action_name']}")
                                if step_dict.get('params'):
                                    logger.info(f"🤖 CARL: Step params keys: {list(step_dict['params'].keys())}")
                                converted_steps.append(step_dict)
                            else:
                                converted_steps.append(step)
                        result_dict["steps"] = converted_steps
                
                logger.info(f"🤖 CARL: Final result_dict for translation:")
                logger.info(f"🤖 CARL: - Steps count: {len(result_dict.get('steps', []))}")
                logger.info(f"🤖 CARL: - Has errors: {bool(result_dict.get('errors'))}")
                logger.info(f"🤖 CARL: - Status: {result_dict.get('status')}")
                logger.info(f"🤖 CARL: - Service groups: {len(result_dict.get('service_groups', []))}")
                logger.info(f"🤖 CARL: - Metadata: {bool(result_dict.get('metadata'))}")
                
                # Carl traduce si hay contenido que traducir, oauth_required, clarificación de servicios, O nuevos status informativos
                status = result_dict.get("status", "")
                metadata_status = result_dict.get("metadata", {}).get("status", "")
                effective_status = metadata_status if metadata_status else status  # Priorizar metadata status
                
                has_service_clarification = bool(result_dict.get("service_groups")) or bool(result_dict.get("metadata", {}).get("service_groups"))
                
                # Nuevos status que requieren traducción
                informational_statuses = WorkflowStatusGroups.INFORMATIONAL_STATUSES
                has_informational_status = effective_status in informational_statuses
                
                # ✅ SMART FORMS EXCEPTION: No traducir cuando hay smart forms para preservar estructura
                has_smart_forms = bool(result_dict.get("metadata", {}).get("smart_forms_required"))
                
                logger.info(f"🤖 CARL: Translation conditions - steps: {bool(result_dict.get('steps'))}, errors: {bool(result_dict.get('errors'))}, oauth_required: {effective_status == 'oauth_required'}, service_clarification: {has_service_clarification}, informational_status: {has_informational_status}, effective_status: {effective_status}, smart_forms: {has_smart_forms}")
                
                if (result_dict.get("steps") or 
                    result_dict.get("errors") or 
                    effective_status == "oauth_required" or 
                    has_service_clarification or
                    (has_informational_status and not has_smart_forms)):  # ✅ NO traducir si hay smart forms
                    logger.info(f"🤖 CARL: Calling translate_kyra_response...")
                    
                    # 🔍 DEBUG: Log the complete response BEFORE Carl touches it
                    logger.info(f"🔍 BEFORE CARL - Complete response object:")
                    logger.info(f"🔍 - similar_services_found: {getattr(response, 'similar_services_found', 'NOT_FOUND')}")
                    logger.info(f"🔍 - service_groups: {getattr(response, 'service_groups', 'NOT_FOUND')}")
                    logger.info(f"🔍 - service_suggestions: {getattr(response, 'service_suggestions', 'NOT_FOUND')}")
                    
                    original_reply = response.reply
                    logger.info(f"🤖 CARL: Original reply: {original_reply[:100]}...")
                    
                    natural_message = await carl.translate_kyra_response(result_dict, user_message)
                    
                    if natural_message and natural_message.strip():
                        response.reply = natural_message
                        logger.info(f"✅ CARL SUCCESS: Replaced reply with natural message")
                        logger.info(f"✅ CARL: New reply: {natural_message[:100]}...")
                        
                        # 🔍 DEBUG: Log the complete response AFTER Carl
                        logger.info(f"🔍 AFTER CARL - Complete response object:")
                        logger.info(f"🔍 - similar_services_found: {getattr(response, 'similar_services_found', 'NOT_FOUND')}")
                        logger.info(f"🔍 - service_groups: {getattr(response, 'service_groups', 'NOT_FOUND')}")
                        logger.info(f"🔍 - service_suggestions: {getattr(response, 'service_suggestions', 'NOT_FOUND')}")
                    else:
                        logger.warning(f"⚠️ CARL: Got empty response, keeping original")
                else:
                    if has_smart_forms:
                        # ✅ SMART FORMS: Crear mensaje apropiado sin traducir
                        smart_form_message = result_dict.get("metadata", {}).get("message", "Por favor completa la información requerida para continuar.")
                        response.reply = smart_form_message
                        logger.info(f"🎯 SMART FORMS: Set smart form message without translation: {smart_form_message[:100]}...")
                    else:
                        logger.info(f"🤖 CARL: No content to translate (no steps or errors)")
                
            except Exception as e:
                logger.error(f"❌ CARL FAILED: {e}")
                logger.exception("Full Carl error traceback:")
                # Si Carl falla, continúa con la respuesta original
            
            # 4. ✅ Persistir conversación
            await self._persist_conversation(chat_id, user_message, response, user_id)
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            return ChatResponseModel(
                reply="Lo siento, hubo un error procesando tu mensaje."
            )

    async def handle_workflow_modification(
        self,
        chat_id: UUID,
        user_message: str,
        current_workflow: Dict[str, Any],
        user_id: int,
        context: Dict[str, Any] = None
    ) -> ChatResponseModel:
        """
        Maneja modificaciones de workflows existentes basadas en feedback del usuario.
        """
        try:
            logger.info(f"Processing workflow modification for chat {chat_id}")
            
            # 1. Obtener WorkflowEngine ESPECÍFICO para este chat_id
            # ✅ FIX: Pasar chat_id para preservar contexto Kyra
            workflow_engine = await get_simple_workflow_engine(chat_id=str(chat_id))
            logger.info(f"🔄 Using WorkflowEngine for chat_id: {chat_id} (workflow modification)")
            
            # 2. Verificar si tiene método de modificación
            if hasattr(workflow_engine, 'modify_workflow_from_feedback'):
                # Usar método específico si existe
                result = await workflow_engine.modify_workflow_from_feedback(
                    user_message=user_message,
                    current_workflow=current_workflow,
                    user_id=user_id,
                    conversation=context.get("conversation", []) if context else []
                )
            else:
                # Fallback: usar planner directamente con CAG vacío (usa memoria para modificaciones)
                from app.workflow_engine.llm.llm_workflow_planner import get_unified_workflow_planner
                planner = await get_unified_workflow_planner()
                
                # OPTIMIZACIÓN: No reconstruir CAG para modificaciones - usar memoria del LLM
                # Modificar workflow usando solo memoria conversacional
                result = await planner.modify_workflow(
                    user_message=user_message,
                    current_workflow=current_workflow,
                    cag_context=[]  # CAG vacío - forzar uso de memoria para modificaciones
                )
            
            # 3. Formatear respuesta
            response = self._format_workflow_response(result)
            
            # 4. Persistir conversación
            await self._persist_conversation(chat_id, user_message, response, user_id)
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling workflow modification: {e}", exc_info=True)
            return ChatResponseModel(
                response="Lo siento, hubo un error modificando el workflow.",
                chat_id=chat_id
            )
    
    async def handle_clarification(
        self,
        chat_id: UUID,
        payload: ClarifyPayload,
        user_id: int
    ) -> ChatResponseModel:
        """
        ✅ RESPONSABILIDAD ÚNICA: Coordinar clarificación con WorkflowEngine
        """
        try:
            logger.info(f"Processing clarification for chat {chat_id}")
            
            # ✅ Obtener WorkflowEngine ESPECÍFICO para este chat_id
            # ✅ FIX: Pasar chat_id para preservar contexto Kyra  
            workflow_engine = await get_simple_workflow_engine(chat_id=str(chat_id))
            logger.info(f"🔄 Using WorkflowEngine for chat_id: {chat_id} (OAuth clarification)")
            
            # 🧠 MEMORIA PERSISTENTE: Con memoria automática, simplemente procesamos como mensaje normal
            # El frontend ya inyectó el mensaje "OAuth completed successfully..." que se guardó en memoria
            # Solo necesitamos procesar el mensaje normal - la memoria maneja el contexto
            
            # Construir mensaje que el frontend debería haber enviado
            user_message = f"OAuth completed successfully. Please continue with the workflow using the authenticated services."
            
            result = await workflow_engine.create_workflow_from_intent(
                user_message=user_message,
                user_id=user_id,
                conversation=None,  # La memoria persistente manejará el historial automáticamente
                workflow_type=payload.workflow_type,
                selected_services=payload.selected_services or []
            )
            
            response = self._format_workflow_response(result)
            await self._persist_conversation(chat_id, "OAuth clarification", response, user_id)
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling clarification: {e}", exc_info=True)
            return ChatResponseModel(
                response="Error procesando la clarificación OAuth.",
                chat_id=chat_id
            )
    
    async def handle_form_submission(
        self,
        chat_id: UUID, 
        payload: FormPayload,
        user_id: int
    ) -> ChatResponseModel:
        """
        ✅ RESPONSABILIDAD ÚNICA: Coordinar form submission con WorkflowEngine
        CONTEXT: Esta función se llama cuando el usuario llena el smart form
        """
        try:
            logger.info(f"Processing form submission for chat {chat_id}")
            
            # ✅ Obtener WorkflowEngine ESPECÍFICO para este chat_id
            # ✅ FIX: Pasar chat_id para preservar contexto Kyra
            workflow_engine = await get_simple_workflow_engine(chat_id=str(chat_id))
            logger.info(f"🔄 Using WorkflowEngine for chat_id: {chat_id} (form submission)")
            
            # ✅ Delegar manejo de form al engine
            result = await workflow_engine.handle_form_completion(
                user_id=user_id,
                form_data=payload.model_dump()
            )
            
            response = self._format_workflow_response(result)
            await self._persist_conversation(chat_id, "Form submission", response, user_id)
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling form submission: {e}", exc_info=True)
            return ChatResponseModel(
                response="Error procesando el formulario.",
                chat_id=chat_id
            )
    
    def _format_workflow_response(self, workflow_result) -> ChatResponseModel:
        """
        ✅ RESPONSABILIDAD ÚNICA: Solo formatear respuesta
        Convertir workflow result a ChatResponseModel con todos los campos
        """
        try:
            # Extraer datos del workflow_result
            reply = getattr(workflow_result, 'reply', None)
            if not reply:
                # TODO: Investigate why workflow_result.reply is None - this should come from Kyra/LLM
                logger.warning(f"🔥 workflow_result.reply is None, using fallback string representation")
                logger.warning(f"🔥 workflow_result type: {type(workflow_result)}")
                logger.warning(f"🔥 workflow_result str preview: {str(workflow_result)[:200]}...")
                reply = str(workflow_result)
            steps = getattr(workflow_result, 'steps', [])
            execution_plan = getattr(workflow_result, 'execution_plan', [])
            finalize = getattr(workflow_result, 'finalize', False)
            editable = getattr(workflow_result, 'editable', False)
            
            # 🎯 SPECIAL CASE: workflow_ready_for_review should enable review interface
            workflow_status = getattr(workflow_result, 'status', None)
            if workflow_status == WorkflowStatus.WORKFLOW_READY_FOR_REVIEW:
                finalize = True  # Trigger finalize behavior
                editable = True  # Enable editing in frontend
                logger.info("🎯 CHAT SERVICE: workflow_ready_for_review detected - setting finalize=True, editable=True") 
            oauth_requirements_raw = getattr(workflow_result, 'oauth_requirements', [])
            # Convert ClarifyOAuthItemDTO objects to dictionaries for frontend
            oauth_requirements = []
            logger.info(f"🔥 PROCESSING OAuth requirements: {len(oauth_requirements_raw)} items")
            for i, req in enumerate(oauth_requirements_raw):
                logger.info(f"🔥 Processing OAuth req {i}: type={type(req)}, has_model_dump={hasattr(req, 'model_dump')}")
                if hasattr(req, 'model_dump'):
                    # Pydantic model - convert to dict
                    converted = req.model_dump()
                    oauth_requirements.append(converted)
                    logger.info(f"🔥 CONVERTED OAuth DTO to dict: {converted}")
                elif isinstance(req, dict):
                    # Already a dict
                    oauth_requirements.append(req)
                    logger.info(f"🔥 OAuth already dict: {req}")
                else:
                    # Fallback - convert to dict manually
                    fallback = {
                        "type": getattr(req, 'type', 'oauth'),
                        "node_id": str(getattr(req, 'node_id', '')),
                        "message": getattr(req, 'message', 'Authorization required'),
                        "oauth_url": getattr(req, 'oauth_url', '/auth/service/authorize')
                    }
                    oauth_requirements.append(fallback)
                    logger.info(f"🔥 OAuth fallback conversion: {fallback}")
            confidence = getattr(workflow_result, 'confidence', 0.5)
            
            # 🏗️ ARQUITECTURA LIMPIA: ChatService NO convierte steps
            # Los steps son responsabilidad del WorkflowContextService
            # Frontend debe llamar /api/workflow-context/{chat_id} para obtener steps
            steps_dict = []  # Always empty - frontend gets steps from WorkflowContextService
            
            # ✨ Detectar si hay clarificación de servicios similares
            similar_services_found = False
            service_groups = None
            
            # ✨ Extraer información de Smart Forms
            smart_form = None
            smart_forms_required = False
            
            # 1. Buscar en metadata del workflow result (Smart Forms + Service Groups)
            metadata = getattr(workflow_result, 'metadata', {})
            logger.info(f"🔍 METADATA CHECK: has_metadata={bool(metadata)}, metadata_keys={list(metadata.keys()) if metadata else []}")
            
            # Extraer service groups (servicios similares)
            if metadata and metadata.get('service_groups'):
                service_groups = metadata.get('service_groups')
                similar_services_found = True
                logger.info(f"🎯 FOUND SERVICE CLARIFICATION IN METADATA: {len(service_groups)} groups")
            
            # ✨ Extraer smart form structure
            if metadata and metadata.get('smart_forms_required'):
                smart_forms_required = True
                smart_form = metadata.get('smart_form', {})
                logger.info(f"🎯 FOUND SMART FORM IN METADATA: {bool(smart_form)}, smart_forms_required: {smart_forms_required}")
            
            # 2. Fallback: buscar en steps (legacy)
            if not service_groups:
                for step in steps_dict:
                    if step.get('action_name') == 'request_clarification':
                        similar_services = step.get('params', {}).get('similar_services', [])
                        if similar_services:
                            similar_services_found = True
                            service_groups = similar_services
                            logger.info(f"🎯 FOUND SERVICE CLARIFICATION IN STEPS: {len(similar_services)} groups")
                            break
            
            # 🔧 WORKFLOW STATE MAPPING: Map workflow status to button states
            workflow_status_str = str(workflow_status) if workflow_status else None
            workflow_action = None
            status = "ready" if steps else "waiting"
            
            # Determine button action based on workflow status
            if workflow_status_str == "WorkflowStatus.WORKFLOW_READY_FOR_REVIEW":
                workflow_action = "save"
                status = "ready_for_review"
            # 🚫 DISABLED: These workflow statuses are now handled by buttons
            # elif workflow_status_str == "WorkflowStatus.SAVE_WORKFLOW":
            #     workflow_action = "saved"
            #     status = "saved"
            # elif workflow_status_str == "WorkflowStatus.ACTIVATE_WORKFLOW":
            #     workflow_action = "activate"
            #     status = "activate_workflow"
            # elif workflow_status_str == "WorkflowStatus.EXECUTE_WORKFLOW":
            #     workflow_action = "execute"
            #     status = "execute_workflow"
            elif hasattr(workflow_result, 'reply') and workflow_result.reply and "activado" in workflow_result.reply:
                workflow_action = "activated"
                status = "activated"
            elif steps:
                workflow_action = "save"
                status = "ready_for_review"
            
            logger.info(f"🔧 BUTTON STATE: status='{status}', workflow_action='{workflow_action}', original_workflow_status='{workflow_status_str}'")
            
            # Crear ChatResponseModel con todos los campos
            return ChatResponseModel(
                reply=reply,
                finalize=finalize,
                editable=editable,  # ✨ NUEVO: Campo editable
                steps=steps_dict,  # ✨ NUEVO: Incluir steps
                execution_plan=execution_plan,  # 🚀 NUEVO: Source of truth for workflow extraction
                oauth_requirements=oauth_requirements,
                enhanced_workflow=bool(steps),  # True si hay workflow
                discovered_files=0,  # Default
                similar_services_found=similar_services_found,  # ✨ NUEVO
                service_groups=service_groups,  # ✨ NUEVO
                smart_form=smart_form,  # ✨ NUEVO: Smart form structure
                smart_forms_required=smart_forms_required,  # ✨ NUEVO: Smart forms flag
                # 🔧 BUTTON STATE FIELDS
                status=status,
                workflow_status=workflow_status_str,
                workflow_action=workflow_action,
                metadata=metadata or {}
            )
            
        except Exception as e:
            logger.error(f"Error formatting workflow response: {e}")
            # Fallback simple
            return ChatResponseModel(
                reply=str(workflow_result),
                finalize=False,
                editable=False,
                steps=[],
                status="error",
                workflow_status="error",
                workflow_action=None,
                metadata={"error": str(e)}
            )
    
    async def _persist_conversation(
        self, 
        chat_id: UUID, 
        user_message: str, 
        response: ChatResponseModel,
        user_id: int
    ):
        """
        ✅ RESPONSABILIDAD ÚNICA: Solo persistir conversación y trigger auto-title
        💾 BD-FIRST: User message ya se guardó, solo guardamos assistant reply
        """
        try:
            # 💾 BD-FIRST: El user message ya se guardó inmediatamente en handle_message
            # Solo necesitamos guardar la respuesta del assistant
            logger.info(f"💾 BD-FIRST: Saving assistant response to database")
            await self.chat_session_service.add_message(chat_id, "assistant", response.reply)
            
            # Verificar si necesitamos generar título automáticamente
            await self._check_and_generate_title(chat_id, user_id)
            
        except Exception as e:
            logger.error(f"Error persisting conversation: {e}")

    async def _check_and_generate_title(self, chat_id: UUID, user_id: int = None):
        """
        Verificar si la sesión necesita generación automática de título
        """
        try:
            # Skip if user_id is None
            if user_id is None:
                logger.warning(f"Cannot generate title for session {chat_id}: user_id is None")
                return
                
            # Verificar si la sesión actual tiene un título genérico o vacío
            session = await self.chat_session_service.get_session(chat_id)
            current_title = session.get('title', '')
            
            # Solo generar título si es genérico o está vacío
            if current_title in ['Nuevo chat', '', None]:
                # Contar mensajes
                message_count = await self.chat_session_service.count_messages_for_session(chat_id)
                
                # Generar título después de 3+ mensajes
                if message_count >= 3:
                    logger.info(f"Auto-generating title for session {chat_id} (has {message_count} messages)")
                    
                    # Importar y usar ChatTitleService
                    from app.services.chat_title_service import get_chat_title_service
                    from app.dtos.chat_title_dto import TitleGenerationRequestDTO
                    
                    # Crear servicio de título directamente usando nueva sesión DB
                    try:
                        from app.db.database import async_session
                        from app.repositories.chat_session_repository import ChatSessionRepository
                        from app.services.chat_title_service import ChatTitleService
                        from app.dtos.chat_title_dto import TitleGenerationRequestDTO
                        
                        # Crear nueva sesión DB para auto-generación
                        async with async_session() as db:
                            try:
                                repo = ChatSessionRepository(db)
                                title_service = ChatTitleService(repo)
                                
                                # Generar título usando método correcto
                                generated_title = await title_service.generate_title_for_session(str(chat_id))
                                
                                if generated_title:
                                    logger.info(f"Auto-generated title: '{generated_title}' for session {chat_id}")
                                    await db.commit()
                                else:
                                    logger.warning(f"Auto-title generation failed for session {chat_id}")
                                    
                            except Exception as e:
                                await db.rollback()
                                raise e
                                
                    except Exception as title_error:
                        logger.warning(f"Auto-title generation failed for session {chat_id}: {title_error}")
                        
        except Exception as e:
            logger.error(f"Error checking auto-title generation for session {chat_id}: {e}")

    async def process_chat(
        self,
        session_id: UUID,
        user_message: str,
        conversation: List[Dict[str, Any]],
        user_id: int,
        db_session,
        workflow_type: str = None,
        selected_services: List[str] = None,
        # 🚨 NEW: OAuth system message injection parameters
        oauth_completed: List[str] = None,
        system_message: str = None,
        continue_workflow: bool = False
    ) -> ChatResponseModel:
        """
        ✅ Implementation of required IChatService method
        Delegates to handle_message for actual processing
        🚨 ENHANCED: Now supports OAuth system message injection
        """
        context = {
            "conversation": conversation, 
            "workflow_type": workflow_type,  # No default - let backend handle None
            "selected_services": selected_services,
            # 🚨 NEW: OAuth context
            "oauth_completed": oauth_completed,
            "system_message": system_message,
            "continue_workflow": continue_workflow
        }
        response = await self.handle_message(
            chat_id=session_id,
            user_message=user_message,
            user_id=user_id,
            context=context,
            db_session=db_session
        )
        # Asegurar que la respuesta incluya el session_id
        response.session_id = session_id
        return response

    async def get_session(self, session_id: UUID) -> Dict[str, Any]:
        """Get a chat session by ID"""
        return await self.chat_session_service.get_session(session_id)

    async def delete_session(self, session_id: UUID) -> bool:
        """Delete a chat session and all its messages"""
        return await self.chat_session_service.delete_session(session_id)

    async def update_session(self, session_id: UUID, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a chat session"""
        return await self.chat_session_service.update_session(session_id, update_data)
    
    async def execute_approved_workflow(
        self,
        session_id: str,
        user_id: int,
        db_session
    ) -> ChatResponseModel:
        """
        Execute workflow after user approval.
        Triggers ReflectionService with approved workflow.
        """
        try:
            logger.info(f"Executing approved workflow for session {session_id}")
            
            # Get WorkflowEngine for this session
            workflow_engine = await get_simple_workflow_engine(chat_id=session_id)
            
            # Trigger workflow execution via user confirmation message
            result = await workflow_engine.handle_message(
                user_message="Sí, ejecuta el workflow",  # User approval message
                user_id=user_id,
                context={"user_approved": True},  # Flag for execution
                db_session=db_session
            )
            
            response = self._format_workflow_response(result)
            await self._persist_conversation(UUID(session_id), "Workflow approved", response, user_id)
            
            return response
            
        except Exception as e:
            logger.error(f"Error executing approved workflow: {e}", exc_info=True)
            return ChatResponseModel(
                reply="Error ejecutando el workflow aprobado.",
                session_id=UUID(session_id)
            )

    # 🎯 SMARTFORM HELPER METHODS
    
    def _is_smartform_submission(self, user_message: str) -> bool:
        """
        Detecta si el mensaje del usuario es una submission de SmartForm
        """
        import re
        # Pattern: "Completé la información requerida: {JSON data}"
        pattern = r"Completé la información requerida:\s*\{.*\}"
        return bool(re.search(pattern, user_message, re.IGNORECASE))
    
    def _extract_smartform_data(self, user_message: str) -> Optional[Dict[str, Any]]:
        """
        Extrae los datos JSON del mensaje de SmartForm submission
        """
        import re
        import json
        
        try:
            # Pattern to extract JSON after "Completé la información requerida:"
            pattern = r"Completé la información requerida:\s*(\{.*\})"
            match = re.search(pattern, user_message, re.IGNORECASE)
            
            if match:
                json_str = match.group(1)
                return json.loads(json_str)
                
        except json.JSONDecodeError as e:
            logger.error(f"🎯 SMARTFORM: Failed to parse JSON from message: {e}")
        except Exception as e:
            logger.error(f"🎯 SMARTFORM: Unexpected error extracting form data: {e}")
            
        return None
    
    async def _save_smartform_data_to_memory(self, db_session, chat_id: UUID, user_id: int, form_data: Dict[str, Any]):
        """
        Guarda los datos del SmartForm en la memoria de conversación
        """
        try:
            from app.services.conversation_memory_service import ConversationMemoryService
            
            memory_service = ConversationMemoryService()
            await memory_service.save_user_inputs_memory(
                db_session=db_session,
                chat_id=str(chat_id),
                user_id=user_id,
                user_inputs=form_data
            )
            logger.info(f"🎯 SMARTFORM: Successfully saved form data to conversation memory")
            
        except Exception as e:
            logger.error(f"🎯 SMARTFORM: Failed to save data to memory: {e}")
            raise

    # 💾 BD-FIRST PERSISTENCE: Core function for immediate message saving
    async def _save_user_message_immediately(self, chat_id: UUID, user_message: str):
        logger.info(f"🔍 SAVE_TRACE: CHAT_SERVICE - chat_id: {chat_id}, msg_preview: '{user_message[:50]}...'")
        """
        💾 BD-FIRST: Guarda el mensaje del usuario inmediatamente en BD
        Esto garantiza que NUNCA se pierdan mensajes, incluso si el LLM falla
        """
        try:
            logger.info(f"💾 BD-FIRST: Saving user message immediately to database")
            
            # Usar chat_session_service que ya maneja BD persistence
            await self.chat_session_service.add_message(chat_id, "user", user_message)
            
            logger.info(f"✅ BD-FIRST: User message saved successfully to BD before LLM processing")
            
        except Exception as e:
            logger.error(f"❌ BD-FIRST: CRITICAL ERROR saving user message: {e}", exc_info=True)
            # NO levantar la excepción - no queremos bloquear el flujo si BD falla
            # Pero sí logear como crítico porque perdemos persistencia

    # ✅ CLEAN CODE: Simplified ChatService without deduplication complexity


# ✅ FACTORY con dependency injection apropiada
async def get_chat_service(
    llm_service: LLMService = Depends(get_llm_service),
    chat_session_service: ChatSessionService = Depends(get_chat_session_service),
) -> IChatService:
    """
    ✅ Factory function con dependency injection apropiada
    WorkflowEngine ahora se obtiene dinámicamente con chat_id
    """
    return ChatService(llm_service, chat_session_service)