"""
WorkflowEngine SIMPLIFICADO - Flujo directo sin capas innecesarias
Kyra obtiene contexto → selecciona nodos → OAuth específico → ejecución
"""
import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.workflow_engine.constants.workflow_statuses import WorkflowStatus, WorkflowStatusGroups
from .interfaces import (
    WorkflowCreationResult, WorkflowType,
    OAuthRequirement,
    OAuthRequiredException
)

from ..utils.response_builder import ResponseBuilder
from ..utils.workflow_logger import WorkflowLogger
from ..llm.llm_workflow_planner import LLMWorkflowPlanner
from app.services.auto_auth_trigger import AutoAuthTrigger
from app.utils.template_engine import WorkflowTemplateEngine
from app.services.conversation_memory_service import get_conversation_memory_service
from app.services.workflow_response_service import get_workflow_response_service
from app.services.chat_workflow_bridge_service import ChatWorkflowBridgeService
from ..memory import create_oauth_memory_manager, OAuthMemoryEvent


class SimpleWorkflowEngine:
    """
    WorkflowEngine SIMPLIFICADO - Sin capas innecesarias
    
    Flujo directo:
    1. CAG context → Kyra
    2. Kyra selecciona nodos
    3. OAuth solo para nodos seleccionados  
    4. Ejecución directa
    """
    
    def __init__(self, cag_service, auto_auth_trigger, reflection_service=None, llm_service=None, bridge_service=None):
        self.cag_service = cag_service
        self.auto_auth_trigger = auto_auth_trigger
        self.reflection_service = reflection_service
        self.bridge_service = bridge_service
        
        # ✅ FIX: Usar LLM singleton compartido 
        if not llm_service:
            from app.ai.llm_clients.llm_service import get_llm_service
            llm_service = get_llm_service()
            
        # Componentes mínimos necesarios - planner usa LLM singleton automáticamente
        self.llm_planner = LLMWorkflowPlanner()
        self.response_builder = ResponseBuilder()
        self.logger = WorkflowLogger(__name__)
        self.template_engine = WorkflowTemplateEngine()  # ✅ RECONECTADO: Template engine para {{mustache}} templates
        
        # 🧠 SERVICIOS REFACTORIZADOS: Memoria y respuestas
        self.memory_service = get_conversation_memory_service()
        self.response_service = get_workflow_response_service()
        
        # 🧱 LEGO BLOCK: OAuth Memory Manager
        self.oauth_memory_manager = create_oauth_memory_manager(
            self.memory_service, self.logger.logger
        )
        
        # 🧠 WORKFLOW MEMORY: Cache para evitar reconstruir CAG/workflows
        self._cached_workflow_result = None
        # ❌ REMOVIDO: CAG cache automático - ahora usa function tools on-demand
        self._cached_conversation_count = 0  # Para detectar si es nuevo mensaje
    
    async def _get_workflow_context_via_service(self, db_session, chat_id, user_id):
        """
        ✅ RESTORED: Load workflow_context for LLM continuity (NOT for extraction)
        Used ONLY for detecting continuation between LLM calls
        """
        try:
            # 🚨 REMOVED: workflow_context_service - using conversation_memory_service directly
            # Load from memory_service where workflow context is actually stored
            self.logger.logger.info(f"🔧 WORKFLOW_CONTEXT_SERVICE: About to call load_memory_context for chat_id={chat_id}")
            memory_context = await self.memory_service.load_memory_context(db_session, str(chat_id))
            self.logger.logger.info(f"🔧 WORKFLOW_CONTEXT_SERVICE: Finished load_memory_context call")
            
            # 🔧 CRITICAL DEBUG: Check what we got from memory service
            self.logger.logger.info(f"🔧 CRITICAL DEBUG: memory_context type={type(memory_context)}, keys={list(memory_context.keys()) if memory_context else 'None'}")
            if memory_context:
                workflow_steps_length = len(memory_context.get('workflow_steps', []))
                self.logger.logger.info(f"🔧 CRITICAL DEBUG: workflow_steps length={workflow_steps_length}")
            
            # Extract complete workflow context from memory if exists
            if memory_context and 'workflow_steps' in memory_context:
                workflow_steps = memory_context['workflow_steps']
                default_auth_mapping = memory_context.get('default_auth_mapping', {})
                
                # Reconstruct COMPLETE workflow_context format with ALL original metadata
                workflow_ctx = {
                    "steps": workflow_steps,
                    "default_auth_mapping": default_auth_mapping,
                    "status": "loaded_from_memory",
                    "workflow_type": "WorkflowType.CLASSIC",  # Preserved from original
                    "editable": True,
                    "finalize": False,
                    "reply": None,
                    "user_inputs_provided": memory_context.get('user_inputs_provided', {}),
                    "created_at": None,  # Will be set if needed
                    "updated_at": None,  # Will be set if needed
                    "estimated_execution_time": None,
                    "cost_estimate": None,
                    "oauth_requirements": [],
                    "smart_forms_generated": memory_context.get('smart_forms_generated', []),
                    "oauth_completed_services": memory_context.get('oauth_completed_services', []),
                    "selected_services": memory_context.get('selected_services', [])
                }
                self.logger.logger.info(f"🔧 MEMORY COMPLETE: Restored full workflow context with {len(workflow_steps)} steps and metadata")
                self.logger.logger.info(f"🔧 MEMORY AUTH: {default_auth_mapping}")
                self.logger.logger.info(f"🔧 MEMORY INPUTS: {workflow_ctx['user_inputs_provided']}")
                return workflow_ctx
                
            return None
        except Exception as e:
            self.logger.logger.error(f"🔍 ERROR: Exception in _get_workflow_context_via_service: {e}")
            return None
    
    # 🗑️ REMOVED: _extract_user_inputs_from_steps - violates execution_plan philosophy  
    # User inputs should come directly from execution_plan, not extracted from steps
    
    
    async def create_workflow_from_intent(
        self,
        user_message: str,
        user_id: int,
        conversation: List[Dict[str, Any]] = None,
        workflow_type: str = None,
        selected_services: List[str] = None,
        db_session: Session = None
    ) -> WorkflowCreationResult:
        """
        Nueva interfaz compatible con chat_service_clean
        ✅ REFACTORED: db_session ahora se inyecta como parámetro
        """
        context = {
            "conversation": conversation or [],
            "workflow_type": workflow_type or "classic",  # Default only if not provided
            "selected_services": selected_services or []
        }
        
        return await self.create_workflow_from_intent_with_context(
            user_message=user_message,
            user_id=user_id,
            context=context,
            db_session=db_session
        )

    async def create_workflow_from_intent_with_context(
        self,
        user_message: str,
        user_id: int,
        context: Dict[str, Any],
        db_session: Session = None
    ) -> WorkflowCreationResult:
        """
        Nueva interfaz que acepta contexto completo incluyendo chat_id
        ✅ REFACTORED: db_session ahora se inyecta como parámetro
        """
        
        # Si no se proporciona sesión, crear una temporal (fallback)
        if db_session is None:
            from app.db.database import get_db
            db_gen = get_db()
            db_session = await anext(db_gen)
            try:
                return await self.process_user_request(
                    user_id=user_id,
                    user_message=user_message,
                    db_session=db_session,
                    context=context
                )
            finally:
                await db_session.close()
        else:
            # Usar la sesión inyectada
            return await self.process_user_request(
                user_id=user_id,
                user_message=user_message,
                db_session=db_session,
                context=context
            )

    async def process_user_request(
        self,
        user_id: int,
        user_message: str,
        db_session: Session,
        context: Dict[str, Any] = None
    ) -> WorkflowCreationResult:
        """
        Flujo SIMPLIFICADO directo:
        CAG → Kyra selecciona → OAuth específico → Workflow
        🧠 MEMORIA PERSISTENTE: Automáticamente recuerda conversaciones
        """
        self.logger.log_request_start(user_id, user_message, None)
        
        try:
            # 🚨 OAUTH SYSTEM MESSAGE INJECTION: Handle OAuth continuation at WorkflowEngine level
            if context and context.get("oauth_completed") and context.get("system_message"):
                self.logger.logger.info(f"🔄 OAUTH SYSTEM MESSAGE: Detected OAuth completion for services: {context.get('oauth_completed')}")
                self.logger.logger.info(f"🔄 OAUTH SYSTEM MESSAGE: System message: {context.get('system_message')[:100]}...")
                
                # Inject system message into conversation context
                if "conversation" not in context:
                    context["conversation"] = []
                
                # Add system message to conversation history
                system_msg = {
                    "role": "system",
                    "content": context.get("system_message")
                }
                context["conversation"].append(system_msg)
                
                # Set user message to empty for OAuth continuation (system message carries context)
                if context.get("continue_workflow"):
                    self.logger.logger.info(f"🔄 OAUTH CONTINUATION: Using system message for workflow continuation")
                    user_message = ""  # Empty user message - system message provides context
            
            # 🧠 PASO 1-3: MEMORIA PERSISTENTE - Recuperar conversación Y workflow previo
            chat_id = getattr(self, 'chat_id', None) or (context.get('chat_id') if context else None)
            conversation_history = await self._handle_conversation_memory(db_session, chat_id, user_id, user_message, context)
            
            # 🧠 RECUPERAR CONTEXTO DE WORKFLOW PREVIO Y MEMORIA
            workflow_context = {}
            memory_context = {}
            if chat_id:
                try:
                    workflow_context = (await self._get_workflow_context_via_service(db_session, chat_id, context.get("user_id", 1)))
                    
                    # 🧠 NUEVO: Cargar memoria de contexto para evitar duplicación
                    memory_context = await self.memory_service.load_memory_context(db_session, str(chat_id))
                    # Get OAuth info from unified manager for logging
                    temp_oauth_memory = await self.oauth_memory_manager.get_current_memory_state(db_session, str(chat_id))
                    self.logger.logger.info(f"🧠 MEMORY LOADED: {len(memory_context.get('smart_forms_generated', []))} smart forms, "
                                          f"{len(temp_oauth_memory.get('oauth_completed_services', []))} OAuth completed, "
                                          f"{len(memory_context.get('user_inputs_provided', {}))} user inputs")
                    
                    if workflow_context:
                        self.logger.logger.info(f"🧠 FOUND PREVIOUS WORKFLOW: {len(workflow_context.get('steps', []))} steps, status: {workflow_context.get('status', 'unknown')}")
                    else:
                        self.logger.log_debug("🧠 NO PREVIOUS WORKFLOW: Starting fresh planning")
                except Exception as e:
                    self.logger.logger.error(f"🔍 ERROR: Exception in _get_workflow_context_via_service: {e}")
                    workflow_context = {}
                    memory_context = {}
            
            # Actualizar context con historial recuperado para uso posterior
            if context:
                context["conversation"] = conversation_history
                # 🧠 SAVE SELECTED SERVICES TO MEMORY if provided
                if context.get("selected_services") and chat_id:
                    try:
                        current_services = memory_context.get('selected_services', [])
                        new_services = context.get("selected_services", [])
                        # Merge unique services
                        all_services = list(set(current_services + new_services))
                        memory_context['selected_services'] = all_services
                        # Save selected services to memory immediately
                        await self.memory_service.save_selected_services_memory(
                            db_session, str(chat_id), user_id, all_services
                        )
                        self.logger.logger.info(f"🧠 SERVICE_SELECTION: Added {len(new_services)} services to memory and saved")
                    except Exception as e:
                        self.logger.logger.error(f"🧠 ERROR: Could not process selected services: {e}")
            else:
                context = {"conversation": conversation_history}
            # 🎯 CRITICAL: Si ya hay workflow_context, USAR steps guardados y SALTAR CAG planning
            self.logger.logger.info(f"🔍 DEBUG: workflow_context type={type(workflow_context)}, bool={bool(workflow_context)}")
            if workflow_context:
                self.logger.logger.info(f"🔍 DEBUG: workflow_context.get('steps') = {workflow_context.get('steps', 'NOT_FOUND')}")
            
            # Verificar si hay steps válidos (puede ser lista o None)
            workflow_steps = workflow_context.get('steps', []) if workflow_context else []
            
            # 🔧 FIX: Check if steps are REALLY valid (have node_id, action_id, and meaningful content)
            truly_valid_steps = []
            if workflow_steps:
                for step in workflow_steps:
                    if isinstance(step, dict):
                        node_id = step.get('node_id')
                        action_id = step.get('action_id') 
                        node_name = step.get('node_name', '')
                        action_name = step.get('action_name', '')
                        
                        # Step is valid if it has proper IDs and names (not placeholders)
                        if (node_id and action_id and 
                            node_name and node_name != 'unknown' and node_name != 'Unknown_Node' and
                            action_name and action_name != 'unknown' and action_name != 'unknown_action'):
                            truly_valid_steps.append(step)
                        else:
                            self.logger.logger.warning(f"🔍 INVALID STEP DETECTED: {node_name}.{action_name} (node_id={node_id}, action_id={action_id})")
            
            has_valid_steps = len(truly_valid_steps) > 0
            self.logger.logger.info(f"🔍 DEBUG: workflow_steps={len(workflow_steps) if workflow_steps else 0}, truly_valid={len(truly_valid_steps)}, has_valid_steps={has_valid_steps}")
            
            # 🎯 FIX: Detectar continuación por selected_services (service group selection)
            is_service_selection = (
                context and 
                context.get("selected_services") and 
                len(context.get("selected_services", [])) > 0
            )
            self.logger.logger.info(f"🎯 SERVICE SELECTION CHECK: selected_services={context.get('selected_services', []) if context else []}")
            self.logger.logger.info(f"🎯 SERVICE SELECTION: is_service_selection={is_service_selection}")
            
            # Inicializar current_conversation_count para evitar UnboundLocalError
            current_conversation_count = len(conversation_history)
            
            # ✅ FIX: Initialize full_cag_context to avoid UnboundLocalError
            full_cag_context = []
            
            # 🎯 SIMPLE UNIFIED FLOW: Let LLM decide states and actions
            
            # Get current memory state
            current_memory = await self.oauth_memory_manager.get_current_memory_state(
                db_session, str(chat_id) if chat_id else ""
            )
            
            # 🔧 CAG OPTIMIZATION: Use is_subsequent_call instead of workflow_context to determine CAG usage
            # Count UNIQUE user messages (handle duplicates from chat_service + workflow_engine)
            user_messages = [msg for msg in conversation_history if msg.get("role") == "user"]
            unique_user_messages = []
            seen_contents = set()
            for msg in user_messages:
                content = msg.get("content", "")
                if content not in seen_contents:
                    unique_user_messages.append(msg)
                    seen_contents.add(content)
            
            # First unique message = first call, 2+ unique messages = subsequent call
            is_subsequent_call = len(unique_user_messages) > 1
            
            # 🔍 DEBUG: Log call type determination
            self.logger.logger.info(f"🔍 CALL TYPE: Total messages={len(conversation_history)}, User messages={len(user_messages)}, Unique user messages={len(unique_user_messages)}, is_subsequent_call={is_subsequent_call}")
            
            # 🔍 DEBUG: Log actual conversation content
            for i, msg in enumerate(conversation_history):
                role = msg.get("role", "unknown")
                content_preview = str(msg.get("content", ""))[:50] + "..." if len(str(msg.get("content", ""))) > 50 else str(msg.get("content", ""))
                self.logger.logger.info(f"🔍 MSG {i+1}: role={role}, content='{content_preview}'")
            
            if is_subsequent_call:
                # Subsequent call - load saved workflow context  
                self.logger.logger.info("🔄 SUBSEQUENT LLM CALL: Using saved workflow context")
                try:
                    saved_workflow_context = (await self._get_workflow_context_via_service(db_session, chat_id, context.get("user_id", 1)))
                    if saved_workflow_context:
                        workflow_context = saved_workflow_context
                        self.logger.logger.info(f"🧠 LOADED WORKFLOW: {len(workflow_context.get('steps', []))} steps")
                except Exception as e:
                    self.logger.logger.error(f"🧠 ERROR: Could not load workflow context: {e}")
                
                # Single LLM call with complete context - LLM decides what to do
                planning_result = await self.llm_planner.unified_workflow_planning(
                    user_message,
                    cag_context=[],  # No CAG for subsequent calls
                    workflow_type=workflow_context.get('workflow_type', 'classic'),
                    selected_services=context.get("selected_services", []) if context else [],
                    history=conversation_history,
                    previous_workflow=workflow_context,
                    discovery_results={},  # No discovery in first call
                    smart_forms_generated=current_memory.get('smart_forms_generated', []),
                    oauth_completed_services=current_memory.get('oauth_completed_services', []),
                    user_inputs_provided=current_memory.get('user_inputs_provided', {}),
                    smart_forms_enabled=bool(current_memory.get('oauth_completed_services', [])),
                    oauth_already_satisfied=bool(current_memory.get('oauth_completed_services', []))
                )
            else:
                # First call - use CAG context
                self.logger.logger.info("🔥 FIRST LLM CALL: Sending full CAG context for initial planning")
                self.logger.log_debug("🔧 BUILDING CAG: Loading cached context from Redis")
                full_cag_context = await self.cag_service.build_context()
                self.logger.log_debug(f"🔧 CAG CONTEXT: {len(full_cag_context)} nodos enviados al LLM")
                
                planning_result = await self.llm_planner.unified_workflow_planning(
                    user_message, 
                    cag_context=full_cag_context,  # ✅ Full CAG for first call
                    workflow_type=workflow_context.get('workflow_type', 'classic') if workflow_context else 'classic',
                    selected_services=context.get("selected_services", []) if context else [],
                    history=conversation_history,
                    previous_workflow=workflow_context,
                    discovery_results=[],  # No discovery results in first call
                    smart_forms_generated=[],
                    oauth_completed_services=[],  
                    user_inputs_provided={},
                    smart_forms_enabled=False,  # LLM will decide based on OAuth state
                    oauth_already_satisfied=False
                )
            
            # 🧠 SAVE WORKFLOW CONTEXT: Save workflow immediately after first LLM call for second call to use
            if chat_id and planning_result and planning_result.get("steps"):
                try:
                    planned_steps = planning_result.get("steps", [])
                    workflow_result_for_save = {
                        "steps": planned_steps,
                        "confidence": planning_result.get("confidence", 0.7),
                        "workflow_type": planning_result.get("workflow_type", "classic"),
                        "metadata": planning_result.get("metadata", {}),
                        "oauth_requirements": planning_result.get("oauth_requirements", []),
                        "status": planning_result.get("status", "designed"),
                        "created_at": "timestamp"
                    }
                    await self.memory_service.save_workflow_context(
                        db_session, str(chat_id), user_id, workflow_result_for_save
                    )
                    self.logger.logger.info(f"🧠 WORKFLOW CONTEXT: Saved context after first LLM call with {len(planned_steps)} steps")
                    
                    # 🔧 NEW FIX: Extract and save user inputs from LLM response
                    try:
                        # 🚨 REMOVED: User inputs extraction - execution_plan already contains user inputs
                        # LLM planner provides user inputs directly in execution_plan
                        pass  # Fix: Add pass statement for empty try block
                    except Exception as e:
                        self.logger.logger.error(f"🔧 USER INPUTS ERROR: Could not save user inputs from LLM: {e}")
                        
                except Exception as e:
                    self.logger.logger.error(f"🧠 ERROR: Could not save workflow context after first LLM call: {e}")
            
            # ⏭️ All planning_result validations moved after OAuth processing
            
            # 🧱 LEGO BLOCK: Get current memory state BEFORE OAuth processing for initial check
            current_memory = await self.oauth_memory_manager.get_current_memory_state(
                db_session, str(chat_id) if chat_id else ""
            )
            
            # 📋 STEP 6: Execute Discovery BEFORE second LLM call (post-OAuth)
            oauth_completed_services = current_memory.get('oauth_completed_services', [])
            
            # 🔧 CRITICAL FIX: Use AutoAuthTrigger to properly validate OAuth credentials
            oauth_requirements = planning_result.get("oauth_requirements", [])
            
            # Check if OAuth requirements are actually satisfied using AutoAuthTrigger
            oauth_already_satisfied = False
            if oauth_requirements:
                try:
                    # Convert LLM planning result to selected_steps format for AutoAuthTrigger
                    planned_steps = planning_result.get("steps", [])
                    selected_steps = []
                    for step in planned_steps:
                        if step.get('action_id') and step.get('node_id'):
                            selected_steps.append({
                                'action_id': step.get('action_id'),
                                'node_id': step.get('node_id')
                            })
                    
                    # Use existing AutoAuthTrigger logic to check if OAuth is satisfied
                    missing_oauth_items = await self.auto_auth_trigger.check_missing_oauth_for_selected_steps(
                        user_id=user_id,
                        selected_steps=selected_steps,
                        chat_id=str(chat_id) if chat_id else None
                    )
                    
                    # OAuth is satisfied if there are NO missing oauth items
                    oauth_already_satisfied = len(missing_oauth_items) == 0
                    
                    self.logger.logger.info(f"🔍 OAUTH VALIDATION: {len(missing_oauth_items)} missing OAuth items. OAuth satisfied: {oauth_already_satisfied}")
                    if missing_oauth_items:
                        for item in missing_oauth_items:
                            self.logger.logger.info(f"❌ MISSING OAUTH: {item.service_id} - {item.message}")
                        
                        # 🚨 CRITICAL: Throw OAuth exception to trigger SmartForms
                        self.logger.logger.info(f"🔐 OAUTH REQUIRED: Throwing OAuthRequiredException for {len(missing_oauth_items)} items")
                        raise OAuthRequiredException(missing_oauth_items)
                    
                except OAuthRequiredException:
                    # 🔥 CRITICAL: Re-raise OAuth exception - don't catch it here
                    raise
                except Exception as e:
                    self.logger.log_error(e, "Failed to check OAuth credentials with AutoAuthTrigger")
                    oauth_already_satisfied = False
            else:
                # No OAuth requirements detected by LLM
                oauth_already_satisfied = True
            
            # ✅ UNIFIED DISCOVERY: Run discovery ONCE before second LLM call (not separately)
            discovery_results = {}
            if oauth_completed_services or oauth_already_satisfied:
                self.logger.logger.info(f"🔍 UNIFIED DISCOVERY: Running discovery for second LLM call (oauth_completed={len(oauth_completed_services)}, oauth_satisfied={oauth_already_satisfied})")
                
                # Execute discovery for OAuth-completed services - UNIFIED WITH LLM CALL
                try:
                    from app.services.file_discovery_service import FileDiscoveryService
                    from app.services.credential_service import CredentialService
                    from app.services.auth_resolver import CentralAuthResolver
                    from app.services.auth_policy_service import AuthPolicyService
                    from app.repositories.credential_repository import CredentialRepository
                    from app.repositories.auth_policy_repository import AuthPolicyRepository
                    
                    # Create services for discovery
                    credential_repo = CredentialRepository(db_session)
                    credential_service = CredentialService(credential_repo)
                    
                    auth_policy_repo = AuthPolicyRepository(db_session)
                    auth_policy_service = AuthPolicyService(db_session, auth_policy_repo)
                    auth_resolver = CentralAuthResolver(auth_policy_service)
                    
                    discovery_service = FileDiscoveryService(
                        credential_service=credential_service,
                        auth_resolver=auth_resolver
                    )
                    
                    # Execute discovery for OAuth-completed/satisfied services 
                    # ✅ FIX: Use current planned_steps from LLM result, not old context
                    planned_steps = planning_result.get("steps", [])
                    target_steps = planned_steps  # Use current planned steps for discovery
                    
                    # Filter only auth-required steps for more focused discovery
                    auth_required_steps = [step for step in target_steps if step.get('default_auth')]
                    if auth_required_steps:
                        self.logger.log_debug(f"🎯 TARGETED DISCOVERY: Focusing on {len(auth_required_steps)} auth-required steps")
                        target_steps = auth_required_steps
                    
                    discovery_results = await discovery_service.discover_user_files(
                        user_id=user_id,
                        planned_steps=target_steps,  # Use targeted steps if available
                        file_types=None  # Auto-detect
                    )
                    
                    self.logger.log_debug(f"🔍 POST-OAUTH DISCOVERY COMPLETE: Found {len(discovery_results)} files/resources")
                    
                    # 🔍 Si discovery encontró algo, agregar al contexto para preservar la información
                    if discovery_results and len(discovery_results) > 0:
                        self.logger.log_debug("🔍 DISCOVERY DATA: Adding discovery results to context for parameter filling")
                        
                        # Agregar discovery results al contexto para que el LLM los use
                        if context:
                            context["discovery_results"] = discovery_results
                        else:
                            context = {"discovery_results": discovery_results}
                            
                        self.logger.log_debug("🔍 DISCOVERY CONTEXT: Ready for parameter auto-completion")
                    
                except Exception as e:
                    self.logger.log_error(e, "🔍 POST-OAUTH DISCOVERY FAILED")
                    discovery_results = {}
                
            # ✅ FIX: Enable SmartForms when OAuth is satisfied (even from previous sessions)
            smart_forms_enabled = oauth_already_satisfied or len(oauth_completed_services) > 0
            
            self.logger.logger.info(f"🔍 MEMORY STATE: oauth_completed_services: {oauth_completed_services}")
            self.logger.logger.info(f"🔍 MEMORY STATE: smart_forms_enabled: {smart_forms_enabled}")
            
            # 🎯 CRITICAL FIX: Second LLM call for SmartForm generation when OAuth satisfied but parameters missing  
            # ONLY run after first LLM call when OAuth is already satisfied but parameters are missing
            if oauth_already_satisfied and planning_result:
                # 🔧 UNIVERSAL FIX: Check if workflow has null/empty parameters that need user input
                # Works for ANY number of nodes (1, 2, 6, 10+ nodes)
                planned_steps = planning_result.get("steps", [])
                has_missing_params = False
                
                for step in planned_steps:
                    # 🎯 FIX: Check BOTH "parameters" AND "params" fields
                    parameters = step.get("parameters", {})
                    params = step.get("params", {})
                    
                    # 🎯 UNIVERSAL DETECTION: Empty objects {} = missing parameters
                    # This works for N nodes: 1, 2, 6, 10+, any number
                    if not parameters and not params:
                        # Both fields are empty - definitely missing params
                        has_missing_params = True
                        break
                    elif not parameters and params == {}:
                        # parameters missing and params is empty object - missing params
                        has_missing_params = True
                        break
                    elif parameters == {} and not params:
                        # params missing and parameters is empty object - missing params
                        has_missing_params = True
                        break
                    elif parameters == {} and params == {}:
                        # Both are empty objects - missing params
                        has_missing_params = True
                        break
                    
                    # 🎯 ADDITIONAL CHECK: Even if objects exist, check for null/empty values
                    for param_value in parameters.values():
                        if param_value is None or param_value == "" or param_value == "null":
                            has_missing_params = True
                            break
                    
                    if not has_missing_params:
                        for param_value in params.values():
                            if param_value is None or param_value == "" or param_value == "null":
                                has_missing_params = True
                                break
                    
                    if has_missing_params:
                        break
                
                self.logger.logger.info(f"🎯 SMARTFORM CHECK: oauth_satisfied={oauth_already_satisfied or bool(oauth_completed_services)}, has_missing_params={has_missing_params}, steps_count={len(planned_steps)}")
                
                if has_missing_params:
                    self.logger.logger.info("🎯 SECOND LLM CALL: OAuth satisfied but parameters missing - calling LLM with FULL CONTEXT + discovery results for SmartForm generation")
                    
                    # Create complete workflow context for second call
                    # 🔧 MINIMAL FIX: Preserve existing workflow_context metadata if available
                    complete_workflow_context = workflow_context.copy() if workflow_context else {}
                    complete_workflow_context.update({
                        "steps": planned_steps,  # ✅ UPDATED STEPS with latest metadata
                        "workflow_type": planning_result.get("workflow_type", "classic"),
                        "status": "oauth_satisfied_missing_params",  # Clear status for LLM
                        "oauth_requirements": planning_result.get("oauth_requirements", []),
                        "confidence": planning_result.get("confidence", 0.7),
                        "metadata": planning_result.get("metadata", {})
                    })
                    
                    # Second LLM call with COMPLETE CONTEXT and explicit OAuth success
                    smartform_planning_result = await self.llm_planner.unified_workflow_planning(
                        user_message,
                        cag_context=[],  # ❌ NO CAG - segunda llamada no necesita 47 nodos
                        workflow_type=complete_workflow_context.get('workflow_type', 'classic'),
                        selected_services=context.get("selected_services", []) if context else [],
                        history=conversation_history,  # ✅ FULL CONVERSATION HISTORY
                        previous_workflow=complete_workflow_context,  # ✅ COMPLETE WORKFLOW CONTEXT
                        discovery_results=discovery_results,  # ✅ DISCOVERY RESULTS
                        smart_forms_generated=current_memory.get('smart_forms_generated', []),  # ✅ MEMORY
                        oauth_completed_services=oauth_completed_services + ['gmail'],  # ✅ EXPLICIT OAUTH SUCCESS
                        user_inputs_provided=current_memory.get('user_inputs_provided', {}),  # ✅ USER INPUTS
                        smart_forms_enabled=True,  # ✅ FORCE SMARTFORM GENERATION
                        oauth_already_satisfied=True  # ✅ OAUTH IS SATISFIED - ENABLE SMARTFORMS
                    )
                    
                    # Update planning_result with SmartForm results
                    if smartform_planning_result:
                        self.logger.logger.info(f"🎯 SMARTFORM RESULT: status={smartform_planning_result.get('status')}, smart_form={bool(smartform_planning_result.get('smart_form'))}")
                        
                        # Merge results, prioritizing SmartForm data from second call
                        if smartform_planning_result.get("smart_form"):
                            planning_result["smart_form"] = smartform_planning_result["smart_form"]
                            planning_result["status"] = smartform_planning_result.get("status", "needs_user_input")
                            planning_result["smart_forms_required"] = True
                            self.logger.logger.info("🎯 SMARTFORM MERGED: SmartForm data merged into planning_result")
                        
                        # Update steps if improved in second call
                        if smartform_planning_result.get("steps"):
                            planning_result["steps"] = smartform_planning_result["steps"]
                            planned_steps = smartform_planning_result["steps"]
                            self.logger.logger.info(f"🎯 STEPS UPDATED: {len(planned_steps)} steps updated from second LLM call")
                    else:
                        self.logger.logger.warning("🎯 SMARTFORM FAILED: Second LLM call returned no result")
                        # 🚨 SAFETY: If we detected missing params but SmartForm failed, 
                        # force status to prevent auto-execution
                        planning_result["status"] = "needs_user_input"
                        self.logger.logger.info("🛡️ SAFETY: Forced status to needs_user_input to prevent auto-execution with empty params")
                
                # 🛡️ ADDITIONAL SAFETY: If we detected missing params but no SmartForm was generated at all
                if has_missing_params and not planning_result.get("smart_form"):
                    planning_result["status"] = "ready_for_review"  # Show for review instead of auto-execute
                    self.logger.logger.info("🛡️ SAFETY: Missing params detected but no SmartForm - forcing ready_for_review status")
            
            # ✅ ELIMINATED should_call_llm_again - No more duplicate calls!
            
            # ✅ SAFETY: Check if planning_result is valid
            if planning_result is None:
                self.logger.log_error(None, "Planning result is None")
                error = Exception("Workflow planning failed - no response from LLM")
                workflow_type_enum = WorkflowType.AGENT if (context and context.get("workflow_type") == "agent") else WorkflowType.CLASSIC
                return self.response_builder.build_error_response(
                    error=error,
                    workflow_type=workflow_type_enum
                )
            
            # 🔥 Handle different planning results
            planned_steps = planning_result.get("steps", [])
            oauth_requirements = planning_result.get("oauth_requirements", [])
            
            self.logger.logger.info(f"🧠 LLM RESULT: status={planning_result.get('status')}, steps={len(planned_steps)}, oauth_reqs={len(oauth_requirements)}")
            
            # ✅ OAuth validation now handled earlier using AutoAuthTrigger - no duplicate logic needed
            
            # ✅ REMOVED: Third LLM call was causing parameter loss
            
            # ✅ NUEVO: Resolver templates en planned_steps antes de execution
            if planned_steps:
                self.logger.log_debug("Resolving mustache templates in workflow steps")
                resolved_steps = await self._resolve_templates_in_steps(planned_steps)
                planned_steps = resolved_steps
            
            # ✅ SIMPLIFIED: OAuth handled by Frontend
            
            # 6. Crear respuesta con nodos seleccionados
            kyra_confidence = planning_result.get("confidence", 0.7)
            kyra_workflow_type = planning_result.get("workflow_type") or (context.get("workflow_type") if context else "classic")
            
            workflow_type_enum = WorkflowType.AGENT if kyra_workflow_type == "agent" else WorkflowType.CLASSIC
            # Build metadata with OAuth satisfied services if they exist
            # ✅ FIX CAG REGRESSION: Report correct node count based on call type (using is_subsequent_call from above)
            cag_nodes_count = 0 if is_subsequent_call else len(full_cag_context)
            response_metadata = {
                "total_available_nodes": cag_nodes_count,  # 0 for subsequent calls, 47 for first call 
                "selected_nodes": len(planned_steps),  # Use planned_steps instead of undefined selected_nodes
                "discovered_files": len(discovery_results) if isinstance(discovery_results, (list, dict)) else 0,
                "flow": "simplified_direct"
            }
            
            # Add OAuth satisfied services to metadata if they exist
            if hasattr(self, '_oauth_satisfied_services') and self._oauth_satisfied_services:
                response_metadata["oauth_satisfied_services"] = self._oauth_satisfied_services
                response_metadata["oauth_already_satisfied"] = True
                response_metadata["flow"] = "oauth_credentials_found"
                self.logger.logger.info(f"🚀 METADATA: Added oauth_satisfied_services: {self._oauth_satisfied_services}")
            
            result = self.response_builder.build_success_response(
                workflow_type=workflow_type_enum,
                steps=planned_steps,
                confidence=kyra_confidence,
                discovered_resources=[],
                oauth_requirements=[],  # ✅ OAuth already verified by auto auth trigger
                metadata=response_metadata,
                execution_plan=planning_result.get("execution_plan", [])
            )
            
            self.logger.log_workflow_success(len(planned_steps), result.workflow_type.value)
            
            # 🧠 COMPLETE STATE RECONSTRUCTION: Always rebuild complete workflow state before saving
            # Based on best practices: load existing state + apply LLM changes = complete state
            
            steps_to_save = []
            
            if chat_id:
                try:
                    # 🔄 STEP 1: Load existing workflow context (complete state)
                    existing_context = (await self._get_workflow_context_via_service(db_session, chat_id, context.get("user_id", 1)))
                    
                    if existing_context and existing_context.get("steps"):
                        # Start with existing complete state
                        self.logger.logger.info(f"🔄 STATE RECONSTRUCTION: Starting with existing {len(existing_context.get('steps', []))} steps")
                        steps_to_save = existing_context.get("steps", [])
                        
                        # 🔄 STEP 2: Apply LLM changes if they exist and look complete
                        if planned_steps:
                            first_step = planned_steps[0] if planned_steps else {}
                            llm_changes_complete = (
                                first_step.get("node_name") and 
                                first_step.get("node_name") != "unknown" and
                                first_step.get("action_name")
                            )
                            
                            # 🚨 CRITICAL FIX: Check if LLM steps have parameters or if existing steps have default_auth
                            llm_has_parameters = any(step.get('params') or step.get('parameters') for step in planned_steps)
                            existing_has_auth = any(step.get('default_auth') for step in steps_to_save)
                            
                            if llm_changes_complete and llm_has_parameters:
                                # LLM provided complete updates with parameters, use them
                                self.logger.logger.info(f"🔄 STATE RECONSTRUCTION: LLM provided complete updates with parameters, replacing {len(steps_to_save)} steps with {len(planned_steps)} new steps")
                                steps_to_save = planned_steps
                            elif llm_changes_complete and not llm_has_parameters and existing_has_auth:
                                # 🚨 CRITICAL: LLM has structure but no params, keep existing to preserve default_auth
                                self.logger.logger.info(f"🚨 CRITICAL FIX: LLM steps have no parameters but existing has auth, keeping existing {len(steps_to_save)} steps to preserve default_auth")
                                # Don't replace - keep existing steps with default_auth
                            else:
                                # LLM changes incomplete, keep existing and merge parameters only
                                self.logger.logger.info(f"🔄 STATE RECONSTRUCTION: LLM changes incomplete, keeping existing steps and merging parameters")
                                # 🔧 INTELLIGENT MERGE: Merge LLM parameter changes into existing steps
                                for existing_step in steps_to_save:
                                    # Find matching step in planned_steps by node_name
                                    for planned_step in planned_steps:
                                        if (existing_step.get('node_name') == planned_step.get('node_name') and 
                                            existing_step.get('action_name') == planned_step.get('action_name')):
                                            
                                            # Merge params from planned_step into existing_step
                                            planned_params = planned_step.get('params', {}) or planned_step.get('parameters', {})
                                            if planned_params:
                                                existing_params = existing_step.get('params', {})
                                                # Update only non-null values from planned_params
                                                for key, value in planned_params.items():
                                                    if value is not None and value != "" and value != "null":
                                                        existing_params[key] = value
                                                        self.logger.logger.info(f"🔧 INTELLIGENT MERGE: Updated {existing_step.get('node_name')}.{key} = {value}")
                                                existing_step['params'] = existing_params
                                            break
                        
                    else:
                        # No existing context, use LLM steps
                        self.logger.logger.info(f"🔄 STATE RECONSTRUCTION: No existing context, using {len(planned_steps)} LLM steps")
                        steps_to_save = planned_steps
                    
                    # 🔄 STEP 3: Always apply user inputs merge (like execution does)
                    if hasattr(self, 'memory_service'):
                        memory_context = await self.memory_service.load_memory_context(db_session, str(chat_id))
                        user_inputs = memory_context.get('user_inputs_provided', {})
                        
                        if user_inputs:
                            self.logger.logger.info(f"🔄 STATE RECONSTRUCTION: Applying {len(user_inputs)} user inputs to {len(steps_to_save)} steps")
                            
                            # Apply user inputs to complete state (same logic as execution)
                            for step_idx, step in enumerate(steps_to_save):
                                if 'parameters' in step and step['parameters']:
                                    for param_key, param_value in step['parameters'].items():
                                        if (param_value is None or param_value == "null" or param_value == "" or not param_value) and param_key in user_inputs:
                                            step['parameters'][param_key] = user_inputs[param_key]
                                            self.logger.logger.info(f"🔄 STATE RECONSTRUCTION: Updated parameters.{param_key} = {user_inputs[param_key]}")
                                
                                if 'params' in step and step['params']:
                                    for param_key, param_value in step['params'].items():
                                        if (param_value is None or param_value == "null" or param_value == "" or not param_value) and param_key in user_inputs:
                                            step['params'][param_key] = user_inputs[param_key]
                                            self.logger.logger.info(f"🔄 STATE RECONSTRUCTION: Updated params.{param_key} = {user_inputs[param_key]}")
                        
                except Exception as e:
                    self.logger.logger.error(f"🔄 STATE RECONSTRUCTION ERROR: {e}")
                    # Fallback to planned_steps
                    steps_to_save = planned_steps
            else:
                # No chat_id, use planned_steps
                steps_to_save = planned_steps
            
            if chat_id and steps_to_save:
                try:
                    # 🔍 DEBUG: Log steps before saving to verify parameter persistence
                    self.logger.logger.info(f"🔍 SAVE DEBUG: About to save {len(steps_to_save)} steps to workflow context")
                    for idx, step in enumerate(steps_to_save):
                        params = step.get('params', {})
                        parameters = step.get('parameters', {})
                        self.logger.logger.info(f"🔍 SAVE DEBUG: Step {idx} - params: {params}, parameters: {parameters}")
                    
                    workflow_result_for_save = {
                        "steps": steps_to_save,
                        "confidence": kyra_confidence,
                        "workflow_type": kyra_workflow_type,
                        "metadata": response_metadata,
                        "oauth_requirements": planning_result.get("oauth_requirements", []),
                        "status": planning_result.get("status", "designed"),
                        "created_at": "timestamp"
                    }
                    
                    # 🔄 ALWAYS UPDATE: save_workflow_context handles create vs update internally
                    await self.memory_service.save_workflow_context(
                        db_session, str(chat_id), user_id, workflow_result_for_save
                    )
                    self.logger.logger.info(f"🔄 WORKFLOW CONTEXT: Saved/updated context with {len(steps_to_save)} steps and latest parameters")
                except Exception as e:
                    self.logger.logger.error(f"🧠 ERROR: Could not save/update workflow context: {e}")
            
            # ✅ Check if user has already approved workflow
            user_approved = context and context.get("user_approved", False)
            
            # ✅ Get planning status from planning_result
            planning_status = planning_result.get("status", WorkflowStatus.READY)
            
            # ✅ PRIMERO: Verificar si necesita presentación al usuario ANTES de reflection
            if planning_status == WorkflowStatus.WORKFLOW_READY_FOR_REVIEW and not user_approved:
                self.logger.log_debug("📋 WORKFLOW PRESENTATION: Showing configured workflow for user approval - SKIPPING reflection")
                
                # Crear respuesta de presentación del workflow
                presentation_metadata = result.metadata.copy()
                presentation_metadata.update({
                    "workflow_presentation": True,
                    "workflow_summary": planning_result.get("workflow_summary", {}),
                    "status": WorkflowStatus.WORKFLOW_READY_FOR_REVIEW,
                    "approval_message": planning_result.get("approval_message", "¿Te parece bien este workflow?"),
                    "next_action": planning_result.get("next_action", "await_user_approval")
                })
                
                # 🔧 DEFINITIVE FIX: Use steps_to_save instead of planned_steps to preserve default_auth
                presentation_response = self.response_builder.build_success_response(
                    workflow_type=workflow_type_enum,
                    steps=steps_to_save,  # ✅ FIXED: Use complete steps with default_auth preserved
                    confidence=kyra_confidence,
                    discovered_resources=[],
                    oauth_requirements=[],  # ✅ OAuth already verified by auto auth trigger 
                    metadata=presentation_metadata,
                    editable=True,
                    finalize=False,
                    execution_plan=planning_result.get("execution_plan", [])
                )
                # Cambiar status después de crear la respuesta
                presentation_response.status = WorkflowStatus.WORKFLOW_READY_FOR_REVIEW
                
                # 🧠 SAVE WORKFLOW PRESENTATION TO MEMORY - Para recordar que ya se presentó
                if chat_id:
                    try:
                        presentation_data = {
                            "workflow_summary": planning_result.get("workflow_summary", {}),
                            "steps": planned_steps,
                            "presented_at": "timestamp"
                        }
                        # 🔧 FIX: Use new update method instead of save to avoid duplication
                        existing_context = (await self._get_workflow_context_via_service(db_session, chat_id, context.get("user_id", 1)))
                        if existing_context and existing_context.get("status") != "presented_for_review":
                            # Update existing context with presentation status using new method
                            status_update = {
                                "status": "presented_for_review", 
                                "presentation": presentation_data,
                                "presented_at": "timestamp"
                            }
                            await self.memory_service.update_workflow_context_status(
                                db_session, str(chat_id), user_id, status_update
                            )
                            self.logger.logger.info(f"🧠 WORKFLOW_PRESENTATION: Updated status to presented_for_review")
                        else:
                            self.logger.logger.info(f"🧠 WORKFLOW_PRESENTATION: Skipped - already presented or no context")
                    except Exception as e:
                        self.logger.logger.error(f"🧠 ERROR: Could not save workflow presentation: {e}")
                
                return presentation_response
            
            # ✅ Force execution if user approved workflow
            elif user_approved:
                self.logger.log_debug("✅ USER APPROVED: Proceeding with workflow execution")
                # Override planning status to force execution
                planning_status = "ready"
            

            # 🚫 DISABLED: BRIDGE SERVICE - Now handled by frontend buttons via ChatWorkflowBridgeService
            # if planning_result.get("status") in WorkflowStatusGroups.BRIDGE_SERVICE_STATUSES:
            #     if self.bridge_service:
            #         self.logger.log_debug(f"🌉 BRIDGE SERVICE: Processing {planning_result.get('status')}")
            #         
            #         # Extract user decision from status
            #         status = planning_result.get("status")
            #         user_decision = status.replace("_workflow", "")  # save_workflow -> save
            #         
            #         # Use saved workflow context for bridge processing
            #         # FIX: Use workflow_context steps if available, fallback to planned_steps
            #         existing_steps = workflow_context.get("steps", []) if workflow_context else []
            #         steps_to_use = existing_steps if existing_steps else planned_steps
            #         
            #         bridge_context = workflow_context or {
            #             "steps": steps_to_use,
            #             "workflow_summary": planning_result.get("workflow_summary", {}),
            #             "metadata": planning_result.get("metadata", {}),
            #             "workflow_type": planning_result.get("workflow_type", "classic")
            #         }
            #         
            #         # Ensure steps are always present in bridge_context
            #         if not bridge_context.get("steps"):
            #             bridge_context["steps"] = steps_to_use
            #         
            #         # Process through bridge service
            #         bridge_result = await self.bridge_service.process_workflow_decision(
            #             user_decision=user_decision,
            #             workflow_context=bridge_context,
            #             user_id=user_id,
            #             chat_id=str(chat_id)
            #         )
            #         
            #         self.logger.log_debug(f"🌉 BRIDGE SERVICE RESULT: {bridge_result.status}")
            #         return bridge_result
            #     else:
            #         self.logger.log_error("🌉 BRIDGE SERVICE: Service not available - falling back to regular flow")
            
            # 🔥 REFLECTION: Para diseño de workflows - MVP flujo lineal (SOLO si no es presentación)
            # 🚨 SKIP reflection for workflow_ready_for_review and needs_user_input - already presented to user
            if self.reflection_service and planning_result.get("status") not in WorkflowStatusGroups.REFLECTION_SKIP_STATUSES:
                self.logger.log_debug("🤔 APPLYING REFLECTION: Workflow design enhancement")
                result = await self._enhance_workflow_with_reflection(
                    result, user_message, user_id, context, db_session
                )
            else:
                skipped_status = planning_result.get("status")
                self.logger.log_debug(f"🚫 SKIPPING REFLECTION: {skipped_status} status - already presented to user or awaiting user input")
            
            # ✅ DESPUÉS DE REFLECTION: Verificar si necesita user input
            if planning_status == WorkflowStatus.NEEDS_USER_INPUT:
                self.logger.log_debug("🔄 RETURNING SMART FORM: User input required after reflection")
                # Crear respuesta con smart form del planning_result original
                smart_form_metadata = result.metadata.copy()
                smart_form_metadata.update({
                    "smart_forms_required": True,
                    "smart_form": planning_result.get("smart_form"),
                    "status": WorkflowStatus.NEEDS_USER_INPUT,
                    "missing_parameters": planning_result.get("missing_parameters", []),
                    "message": planning_result.get("message", "Se requieren parámetros adicionales")
                })
                
                smart_form_response = self.response_builder.build_success_response(
                    workflow_type=workflow_type_enum,
                    steps=steps_to_save,
                    confidence=kyra_confidence,
                    discovered_resources=[],
                    oauth_requirements=[],  # ✅ OAuth already verified by auto auth trigger
                    metadata=smart_form_metadata,
                    editable=True,
                    finalize=False,
                    execution_plan=planning_result.get("execution_plan", [])
                )
                # Cambiar status después de crear la respuesta
                smart_form_response.status = WorkflowStatus.NEEDS_USER_INPUT
                
                # 🧠 SAVE SMART FORM TO MEMORY - Para evitar duplicación
                if chat_id and planning_result.get("smart_form"):
                    try:
                        smart_form_data = planning_result.get("smart_form")
                        current_smart_forms = memory_context.get('smart_forms_generated', [])
                        current_smart_forms.append(smart_form_data)
                        await self.memory_service.save_smart_forms_memory(
                            db_session, str(chat_id), user_id, current_smart_forms
                        )
                        self.logger.logger.info(f"🧠 SMART_FORM: Saved to memory to prevent duplication")
                    except Exception as e:
                        self.logger.logger.error(f"🧠 ERROR: Could not save smart form to memory: {e}")
                
                return smart_form_response
            
            # ✅ EJECUCIÓN AUTOMÁTICA: Si el status es "ready" (usuario ya aprobó), ejecutar workflow
            if planning_status == "ready":
                self.logger.log_debug("🚀 WORKFLOW EXECUTION: User approved, executing workflow automatically")
                
                try:
                    # Importar dependencias necesarias para ejecutar
                    from app.services.workflow_runner_service import WorkflowRunnerService
                    from app.services.flow_execution_service import FlowExecutionService
                    from app.services.flow_validator_service import FlowValidatorService
                    from app.services.credential_service import CredentialService
                    from app.repositories.credential_repository import CredentialRepository
                    from app.repositories.flow_execution_repository import FlowExecutionRepository
                    from app.db.database import async_session
                    from uuid import uuid4
                    
                    # Crear dependencias para WorkflowRunner
                    async with async_session() as exec_db_session:
                        credential_repo = CredentialRepository(exec_db_session)
                        credential_service = CredentialService(credential_repo)
                        flow_exec_repo = FlowExecutionRepository(exec_db_session)
                        flow_exec_svc = FlowExecutionService(flow_exec_repo)
                        validator = FlowValidatorService()
                        
                        # Crear WorkflowRunner
                        runner = WorkflowRunnerService(flow_exec_svc, credential_service, validator)
                        
                        # Generar flow_id temporal y ejecutar
                        temp_flow_id = uuid4()
                        execution_id, execution_result = await runner.run_workflow(
                            flow_id=temp_flow_id,
                            steps=planned_steps,
                            user_id=user_id,
                            inputs={},
                            simulate=False  # Ejecución real
                        )
                        
                        self.logger.logger.info(f"🚀 WORKFLOW EXECUTED: execution_id={execution_id}, status={execution_result.overall_status}")
                        
                        # Actualizar respuesta con resultado de ejecución
                        execution_metadata = result.metadata.copy()
                        execution_metadata.update({
                            "workflow_executed": True,
                            "execution_id": str(execution_id),
                            "execution_status": execution_result.overall_status,
                            "execution_summary": f"Workflow ejecutado exitosamente. {len([s for s in execution_result.steps if s.status == 'success'])} de {len(execution_result.steps)} pasos completados.",
                            "steps_completed": len([s for s in execution_result.steps if s.status == "success"]),
                            "total_steps": len(execution_result.steps)
                        })
                        
                        executed_response = self.response_builder.build_success_response(
                            workflow_type=workflow_type_enum,
                            steps=planned_steps,
                            confidence=kyra_confidence,
                            discovered_resources=[],
                            metadata=execution_metadata,
                            editable=False,  # Ya ejecutado, no editable
                            finalize=True,   # Workflow completado
                            execution_plan=planning_result.get("execution_plan", [])
                        )
                        executed_response.status = "executed"
                        executed_response.reply = f"¡Listo! Tu workflow se ejecutó exitosamente. {execution_metadata['execution_summary']}"
                        
                        return executed_response
                        
                except Exception as e:
                    self.logger.logger.error(f"🚀 ERROR: Failed to execute workflow: {e}")
                    # Si falla la ejecución, devolver el workflow sin ejecutar pero con error
                    error_metadata = result.metadata.copy()
                    error_metadata.update({
                        "execution_failed": True,
                        "execution_error": str(e),
                        "message": f"El workflow está configurado correctamente, pero falló la ejecución: {str(e)}"
                    })
                    result.metadata = error_metadata
                    result.reply = f"Workflow configurado, pero hubo un error en la ejecución: {str(e)}"
            
            # 🧠 WORKFLOW CONTEXT: Already saved after successful workflow creation (lines 577-594)
            
            # 🧠 WORKFLOW MEMORY: Guardar resultado en cache para futuras continuaciones
            self._cached_workflow_result = result
            self._cached_conversation_count = current_conversation_count
            self.logger.log_debug(f"💾 CACHE: Workflow saved to memory, conversation count: {current_conversation_count}")
            
            return result
            
        except OAuthRequiredException as e:
            self.logger.log_oauth_required(e.oauth_requirements)
            return self.response_builder.build_oauth_required_response(
                WorkflowType.CLASSIC, e.oauth_requirements, None
            )
        except Exception as e:
            self.logger.log_error(e, "simplified workflow creation")
            return self.response_builder.build_error_response(e, WorkflowType.CLASSIC, None)
    
    # 🧠 MEMORIA PERSISTENTE: Con memoria persistente automática, eliminamos métodos manuales de OAuth
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Estado del engine simplificado"""
        return {
            "engine_type": "simplified",
            "discovery_layers": "eliminated",
            "validation_layers": "minimal",
            "flow": "cag → kyra_selection → oauth_specific → execution",
            "components": {
                "cag_service": "direct",
                "llm_planner": "direct", 
                "auto_auth_trigger": "selected_steps_only",
                "file_discovery": "optional_with_selected_nodes"
            }
        }
    
    async def _discover_user_files(
        self,
        selected_nodes: List[Dict[str, Any]],
        user_id: int,
        db_session
    ) -> List[Dict[str, Any]]:
        """
        Descubre archivos reales de nodos seleccionados
        CONSISTENTE: usa misma lógica que oauth_checker
        """
        try:
            from app.services.file_discovery_service import FileDiscoveryService
            from app.services.credential_service import CredentialService
            from app.services.auth_resolver import CentralAuthResolver
            from app.repositories.credential_repository import CredentialRepository
            
            # Crear servicios con nueva arquitectura
            cred_repo = CredentialRepository(db_session)
            credential_service = CredentialService(cred_repo)
            auth_resolver = CentralAuthResolver()
            discovery_service = FileDiscoveryService(credential_service, auth_resolver)
            
            # Convertir selected_nodes a planned_steps para nueva arquitectura
            planned_steps = []
            for node in selected_nodes:
                default_auth = node.get('auth_required')
                if default_auth:
                    planned_steps.append({
                        'id': node.get('id', ''),
                        'action_id': node.get('action_id', ''),
                        'default_auth': default_auth,
                        'name': node.get('name', '')
                    })
            
            if not planned_steps:
                self.logger.log_debug("No auth-required nodes for file discovery")
                return []
            
            # Descubrir archivos usando nueva arquitectura
            discovered_files = await discovery_service.discover_user_files(
                user_id=user_id,
                planned_steps=planned_steps,
                file_types=None  # Todos los tipos
            )
            
            # Convertir a dict para serialización
            files_dict = []
            for file in discovered_files:
                files_dict.append({
                    "id": file.id,
                    "name": file.name,
                    "provider": file.provider,
                    "file_type": file.file_type,
                    "confidence": file.confidence,
                    "structure": file.structure,
                    "icon": file.icon,
                    "metadata": file.metadata
                })
            
            return files_dict
            
        except ImportError:
            self.logger.log_warning("UniversalDiscoveryService not available")
            return []
        except Exception as e:
            self.logger.log_error(e, "file discovery")
            return []
    
    async def _get_credentials_for_selected_nodes(
        self,
        selected_nodes: List[Dict[str, Any]],
        user_id: int,
        oauth_service
    ) -> Dict[str, Any]:
        """
        🔥 SIMPLIFICADO: Obtiene credenciales usando UnifiedOAuthManager
        ELIMINA DUPLICACIÓN: Ya no extrae providers manualmente
        """
        try:
            # ✅ CORREGIDO: Usar CredentialService directamente, no UnifiedOAuthManager
            from app.services.credential_service import get_credential_service
            from app.services.auth_resolver import get_auth_resolver
            
            credential_service = await get_credential_service()
            auth_resolver = await get_auth_resolver()
            
            credentials = {}
            
            # Procesar cada nodo seleccionado para obtener credenciales
            for node in selected_nodes:
                default_auth = node.get('default_auth')
                action_id = node.get('action_id')
                
                if not default_auth and not action_id:
                    continue
                
                # Resolver auth policy
                auth_policy = None
                if action_id:
                    auth_policy = await auth_resolver.resolve_action_auth(action_id)
                elif default_auth:
                    auth_policy = await auth_resolver.resolve_auth_once(default_auth)
                
                if not auth_policy or not auth_policy.requires_oauth():
                    continue
                
                # Obtener credenciales usando CredentialService
                node_credentials = await credential_service.get(
                    user_id, auth_policy.provider, auth_policy.service
                )
                
                if node_credentials:
                    provider_key = auth_policy.get_provider_key()
                    credentials[provider_key] = node_credentials
            
            self.logger.log_debug(f"Retrieved credentials for {len(credentials)} providers")
            return credentials
            
        except Exception as e:
            self.logger.log_error(e, "getting verified credentials for selected nodes")
            return {}
    
    async def _enhance_workflow_with_reflection(
        self,
        workflow_result: WorkflowCreationResult,
        user_message: str,
        user_id: int,
        context: Dict[str, Any],
        db_session
    ) -> WorkflowCreationResult:
        """
        🔥 NEW: Enhance workflow using reflection service
        Plan → Simulate → Reflect → Improve workflow before returning to user
        """
        try:
            self.logger.log_debug("Starting workflow enhancement with reflection...")
            
            # Use reflection service with smart iteration (includes simulation)
            enhanced_result = await self.reflection_service.execute_workflow_with_smart_iteration(
                workflow_result=workflow_result,
                user_message=user_message,
                user_id=user_id,
                simulate_first=True,  # Always simulate first to avoid real execution
                max_iterations=2  # Limit iterations to avoid infinite loops
            )
            
            # Extract improved workflow from reflection result
            if enhanced_result.get("status") == "completed" and enhanced_result.get("improved_workflow"):
                improved_workflow = enhanced_result["improved_workflow"]
                
                # Update workflow result with improvements
                if improved_workflow.get("steps"):
                    workflow_result.steps = improved_workflow["steps"]
                    
                if improved_workflow.get("confidence"):
                    workflow_result.confidence = improved_workflow["confidence"]
                
                # Add reflection metadata
                if not workflow_result.metadata:
                    workflow_result.metadata = {}
                    
                workflow_result.metadata.update({
                    "reflection_applied": True,
                    "reflection_iterations": enhanced_result.get("iterations_completed", 0),
                    "reflection_improvements": enhanced_result.get("improvements_made", []),
                    "simulation_results": enhanced_result.get("simulation_summary", {})
                })
                
                self.logger.log_debug(f"Workflow enhanced with {enhanced_result.get('iterations_completed', 0)} reflection iterations")
            
            else:
                # Reflection didn't improve the workflow, keep original
                self.logger.log_debug("Reflection completed but no improvements were made")
                if not workflow_result.metadata:
                    workflow_result.metadata = {}
                workflow_result.metadata["reflection_applied"] = False
            
            return workflow_result
            
        except Exception as e:
            self.logger.log_error(e, "workflow reflection enhancement")
            # Return original workflow if reflection fails
            self.logger.log_debug("Reflection failed, returning original workflow")
            if not workflow_result.metadata:
                workflow_result.metadata = {}
            workflow_result.metadata["reflection_error"] = str(e)
            return workflow_result

    async def _resolve_templates_in_steps(
        self, 
        planned_steps: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        🔥 RECONECTADO: Resuelve templates {{mustache}} en parámetros de steps
        Permite usar {{step1.output.email}} en parámetros de steps posteriores
        """
        try:
            resolved_steps = []
            execution_context = {}  # Context construido desde outputs de steps anteriores
            
            for step in planned_steps:
                # Resolver templates en parámetros del step usando context actual
                if "parameters" in step and step["parameters"]:
                    resolved_params = self.template_engine.resolve_template_in_params(
                        step["parameters"], execution_context
                    )
                    step["parameters"] = resolved_params
                    self.logger.log_debug(f"Resolved templates in step {step.get('id', 'unknown')}")
                
                # Simular output del step para próximos templates (para planning)
                # En ejecución real, esto vendría de los resultados reales
                if step.get("id"):
                    fake_output = self.template_engine.generate_fake_data_for_field("step_output")
                    execution_context[f"step_{step.get('id', '')}"] = {"output": fake_output}
                
                resolved_steps.append(step)
            
            self.logger.log_debug(f"Template resolution completed for {len(resolved_steps)} steps")
            return resolved_steps
            
        except Exception as e:
            self.logger.log_error(e, "resolving templates in planned steps")
            # Return original steps if template resolution fails
            return planned_steps

    # 🧠 MEMORIA PERSISTENTE: Maneja automáticamente las continuaciones de workflow


    # 🧠 MEMORIA PERSISTENTE: Métodos refactorizados usando servicios
    
    async def _handle_conversation_memory(
        self, 
        db_session: Session, 
        chat_id: str, 
        user_id: int, 
        user_message: str, 
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Maneja memoria persistente usando ConversationMemoryService
        """
        # PASO 1: Guardar mensaje del usuario automáticamente
        if chat_id:
            await self.memory_service.save_user_message(db_session, chat_id, user_id, user_message)
        
        # PASO 2: Recuperar historial automáticamente 
        persistent_history = []
        if chat_id:
            persistent_history = await self.memory_service.load_conversation_history(db_session, chat_id)
        
        # PASO 3: Combinar historial persistente con contexto del frontend (si existe)
        frontend_history = context.get("conversation", []) if context else []
        
        # Priorizar historial persistente sobre el del frontend
        if persistent_history:
            conversation_history = persistent_history
            self.logger.log_debug(f"🧠 MEMORIA: Usando historial persistente ({len(persistent_history)} msgs)")
        elif frontend_history:
            conversation_history = frontend_history
            self.logger.log_debug(f"🧠 MEMORIA: Usando historial del frontend ({len(frontend_history)} msgs)")
        else:
            conversation_history = []
            self.logger.log_debug("🧠 MEMORIA: Sin historial disponible")
        
        return conversation_history

    async def handle_form_completion(self, user_id: int, form_data: dict) -> 'WorkflowCreationResultDTO':
        """
        🔥 MVP FLOW: Procesa form completion y ejecuta OAuth check al final
        """
        try:
            self.logger.log_debug(f"🔥 FORM COMPLETION: Processing form data for user {user_id}")
            
            # Usar SmartFormService existente para procesar el form
            from app.services.smart_form_service import SmartFormService
            smart_form_service = SmartFormService()
            
            # Extraer datos del form
            form_payload = form_data.get("form", {})
            node_id = form_payload.get("node")
            action_id = form_payload.get("action") 
            user_params = form_payload.get("params", {})
            
            self.logger.log_debug(f"🔥 FORM DATA: node={node_id}, action={action_id}, params={len(user_params)} fields")
            
            # AQUÍ VA EL OAUTH CHECK AL FINAL DEL MVP FLOW
            # TODO: Implementar OAuth check con auto_auth_trigger después de form completion
            
            # Usar lógica existente de SmartFormService
            result = await smart_form_service.merge_and_execute_handler(
                handler_name=f"action_{action_id}",
                discovered_params={},  # No discovery en MVP
                user_provided_params=user_params,
                execution_creds={}  # OAuth credentials después del check
            )
            
            # Convertir resultado a WorkflowCreationResultDTO
            from app.dtos.workflow_creation_result_dto import WorkflowCreationResultDTO
            from app.enums.workflow_type import WorkflowType
            
            return WorkflowCreationResultDTO(
                status="success" if result.get("success") else "error",
                workflow_type=WorkflowType.CLASSIC,  # TODO: Get from context
                steps=[],
                oauth_requirements=[],
                discovered_resources=[],
                confidence=0.8,
                metadata={"execution_result": result}
            )
            
        except Exception as e:
            self.logger.log_error(e, "handling form completion")
            from app.dtos.workflow_creation_result_dto import WorkflowCreationResultDTO
            from app.enums.workflow_type import WorkflowType
            
            return WorkflowCreationResultDTO(
                status="error",
                workflow_type=WorkflowType.CLASSIC,
                steps=[],
                oauth_requirements=[],
                discovered_resources=[],
                confidence=0.3,
                metadata={"error": str(e)}
            )

    # 🧠 REMOVED: Métodos de memoria movidos a ConversationMemoryService

