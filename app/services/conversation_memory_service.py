"""
ConversationMemoryService - Servicio para memoria persistente de conversaciones
Maneja lógica de negocio y coordinación con el Repository
"""
import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.repositories.conversation_memory_repository import get_conversation_memory_repository

logger = logging.getLogger(__name__)


class ConversationMemoryService:
    """
    Servicio para manejar memoria persistente de conversaciones.
    Permite que el LLM recuerde automáticamente sin depender del frontend.
    """
    
    def __init__(self):
        self.repo = get_conversation_memory_repository()
    
    async def save_user_message(
        self, 
        db_session: AsyncSession, 
        chat_id: str, 
        user_id: int, 
        message: str
    ):
        """
        Guarda mensaje del usuario en memoria persistente
        """
        await self._save_message(db_session, chat_id, user_id, "user", message)
        logger.debug(f"🧠 MEMORIA: Guardado mensaje del usuario en chat_id: {chat_id}")
    
    async def save_assistant_response(
        self, 
        db_session: AsyncSession, 
        chat_id: str, 
        user_id: int, 
        response: str
    ):
        """
        Guarda respuesta del asistente en memoria persistente
        """
        await self._save_message(db_session, chat_id, user_id, "assistant", response)
        logger.debug(f"🧠 MEMORIA: Guardada respuesta del asistente")
    
    async def save_workflow_context(
        self,
        db_session: AsyncSession,
        chat_id: str,
        user_id: int,
        workflow_result: Dict[str, Any]
    ):
        """
        Guarda el contexto del workflow diseñado para futuras continuaciones
        🔧 SIMPLIFIED: Always use complete workflow_result directly (no hybrid approach)
        """
        try:
            # 🔧 ALWAYS USE WORKFLOW_RESULT: workflow_result contains complete reconstructed state
            # Check if existing workflow context message exists to decide between create vs update
            history = await self.load_conversation_history(db_session, chat_id)
            existing_workflow_message = None
            for msg in reversed(history):
                if msg.get("role") == "system" and msg.get("content", "").startswith("WORKFLOW_CONTEXT:"):
                    existing_workflow_message = msg
                    break
            
            if existing_workflow_message and workflow_result.get("steps"):
                logger.info(f"🔥 DIRECT UPDATE: Existing workflow context found, updating with {len(workflow_result.get('steps', []))} steps")
                # Update existing context with complete state from workflow_result
                await self._force_update_workflow_context(db_session, chat_id, user_id, workflow_result)
                
                # Force flush after update
                try:
                    await db_session.flush()
                    logger.info(f"🔄 DIRECT UPDATE: Flushed changes after workflow context update")
                except Exception as e:
                    logger.error(f"🔄 DIRECT UPDATE FLUSH ERROR: {e}")
                    await db_session.rollback()
                    raise
                return
            
            import json
            
            # 🔧 DIRECT SAVE: workflow_result contains complete reconstructed state from workflow_engine
            steps = workflow_result.get("steps", [])
            
            # 🔍 DEBUG: Log what we're receiving (should be complete)
            logger.info(f"🔍 DIRECT SAVE: Received complete workflow_result with {len(steps)} steps")
            for idx, step in enumerate(steps):
                # 🔍 END-TO-END TRACE: Log default_auth at save point
                default_auth = step.get('default_auth') if isinstance(step, dict) else getattr(step, 'default_auth', None)
                node_name = step.get('node_name') if isinstance(step, dict) else getattr(step, 'node_name', 'unknown')
                logger.info(f"🔍 E2E TRACE MEMORY SAVE: Step {idx+1} ({node_name}) default_auth = {default_auth}")
                logger.debug(f"🔍 DIRECT SAVE: Step {idx}: {step}")
            
            # 🔧 USE PROPER DTO SERIALIZATION: Convert to Pydantic DTOs for proper serialization
            try:
                from app.dtos.step_meta_dto import StepMetaDTO
                from app.dtos.workflow_creation_result_dto import WorkflowCreationResultDTO, WorkflowType
                
                # Convert dict steps to proper StepMetaDTO objects
                step_dtos = []
                for idx, step in enumerate(steps):
                    try:
                        # 🔍 EXHAUSTIVE TRACE: Log step state before DTO conversion
                        step_params = step.get("params", {})
                        step_parameters = step.get("parameters", {})
                        step_default_auth = step.get("default_auth")
                        step_node_name = step.get("node_name", "unknown")
                        logger.info(f"🔍 DTO CONVERSION STEP {idx+1} BEFORE:")
                        logger.info(f"🔍   Node: {step_node_name}")
                        logger.info(f"🔍   params: {json.dumps(step_params, indent=2, default=str)}")
                        logger.info(f"🔍   parameters: {json.dumps(step_parameters, indent=2, default=str)}")
                        logger.info(f"🔍   default_auth: {step_default_auth}")
                        
                        # Create StepMetaDTO from dict, filling missing fields with defaults
                        step_dto = StepMetaDTO(
                            id=step.get("id", step.get("step_id")),
                            node_id=step.get("node_id", step.get("id")),
                            action_id=step.get("action_id", step.get("id")),
                            node_name=step.get("node_name", "unknown"),
                            action_name=step.get("action_name", "unknown"),
                            default_auth=step.get("default_auth"),
                            params=step.get("params", step.get("parameters", {})),
                            params_meta=step.get("params_meta", []),
                            uses_mcp=step.get("uses_mcp", False),
                            retries=step.get("retries", 0),
                            timeout_ms=step.get("timeout_ms"),
                            simulate=step.get("simulate", False),
                            next=step.get("next")
                        )
                        step_dtos.append(step_dto)
                        
                        # 🔍 EXHAUSTIVE TRACE: Log step state after DTO conversion
                        dto_params = step_dto.params
                        dto_default_auth = step_dto.default_auth
                        logger.info(f"🔍 DTO CONVERSION STEP {idx+1} AFTER:")
                        logger.info(f"🔍   DTO params: {json.dumps(dto_params, indent=2, default=str)}")
                        logger.info(f"🔍   DTO default_auth: {dto_default_auth}")
                        
                        logger.info(f"🔧 DIRECT DTO CONVERSION: Successfully converted step {step.get('node_name', 'unknown')}")
                    except Exception as step_error:
                        logger.error(f"🔧 DIRECT DTO CONVERSION ERROR: Failed to convert step {step}: {step_error}")
                        # Fallback: keep original dict
                        step_dtos.append(step)
                
                # 🔧 FIX: Filter oauth_requirements to only include valid ClarifyOAuthItemDTO objects
                raw_oauth_requirements = workflow_result.get("oauth_requirements", [])
                valid_oauth_requirements = []
                
                for oauth_req in raw_oauth_requirements:
                    try:
                        # Check if it has all required fields for ClarifyOAuthItemDTO
                        if (isinstance(oauth_req, dict) and 
                            oauth_req.get("type") == "oauth" and
                            oauth_req.get("node_id") and 
                            oauth_req.get("message") and
                            oauth_req.get("oauth_url") and
                            oauth_req.get("service_id")):
                            valid_oauth_requirements.append(oauth_req)
                        else:
                            logger.warning(f"🔧 OAUTH FILTER: Skipping invalid oauth_requirement: {oauth_req}")
                    except Exception as oauth_error:
                        logger.warning(f"🔧 OAUTH FILTER ERROR: {oauth_error}")
                
                logger.info(f"🔧 OAUTH FILTER: Filtered {len(raw_oauth_requirements)} -> {len(valid_oauth_requirements)} valid oauth requirements")
                
                # Create WorkflowCreationResultDTO for proper serialization
                workflow_dto = WorkflowCreationResultDTO(
                    status=workflow_result.get("status", "designed"),
                    workflow_type=WorkflowType.CLASSIC if workflow_result.get("workflow_type", "classic") == "classic" else WorkflowType.AGENT,
                    steps=[step.model_dump() if hasattr(step, 'model_dump') else step for step in step_dtos],
                    oauth_requirements=valid_oauth_requirements,
                    discovered_resources=workflow_result.get("discovered_resources", []),
                    confidence=workflow_result.get("confidence", 0.5),
                    next_actions=workflow_result.get("next_actions", []),
                    metadata=workflow_result.get("metadata", {}),
                    reply=workflow_result.get("reply")
                )
                
                # Use Pydantic serialization (preserves all fields correctly)
                context_json = workflow_dto.model_dump_json(exclude_none=False)
                logger.info(f"🔧 DIRECT PYDANTIC SERIALIZATION: Successfully serialized {len(step_dtos)} steps")
                
            except Exception as dto_error:
                logger.error(f"🔧 DIRECT DTO SERIALIZATION ERROR: {dto_error}")
                # Fallback to old method
                workflow_context = {
                    "type": "workflow_context",
                    "steps": steps,
                    "confidence": workflow_result.get("confidence", 0.5),
                    "workflow_type": workflow_result.get("workflow_type", "classic"),
                    "metadata": workflow_result.get("metadata", {}),
                    "oauth_requirements": workflow_result.get("oauth_requirements", []),
                    "status": workflow_result.get("status", "designed"),
                    "created_at": workflow_result.get("created_at")
                }
                context_json = json.dumps(workflow_context, default=str)
                logger.warning(f"🔧 DIRECT FALLBACK SERIALIZATION: Using old method due to DTO error")
            
            # 🔍 DEBUG: Log final serialized content
            logger.info(f"🔍 DIRECT FINAL SAVE DEBUG: Serialized content length: {len(context_json)}")
            
            # Guardar como mensaje especial del sistema
            await self._save_message(db_session, chat_id, user_id, "system", f"WORKFLOW_CONTEXT: {context_json}")
            
            logger.info(f"🧠 WORKFLOW: Guardado NUEVO contexto del workflow con {len(workflow_result.get('steps', []))} steps (DIRECT from workflow_result)")
            
        except Exception as e:
            logger.error(f"🧠 ERROR: No se pudo guardar contexto del workflow: {e}")
    
    async def _force_update_workflow_context(
        self,
        db_session: AsyncSession,
        chat_id: str,
        user_id: int,
        workflow_result: Dict[str, Any]
    ):
        """
        🔧 EMERGENCY FIX: Preserve existing parameters before update
        Prevents parameter loss during SmartForms cycling
        """
        try:
            import json
            
            # 🔍 EXHAUSTIVE DEBUG: Log workflow_result as it arrives
            logger.info(f"🔍 FORCE UPDATE ENTRY: chat_id={chat_id}, user_id={user_id}")
            logger.info(f"🔍 FORCE UPDATE RAW WORKFLOW_RESULT KEYS: {list(workflow_result.keys())}")
            
            # Log steps specifically
            steps_in_result = workflow_result.get('steps', [])
            logger.info(f"🔍 FORCE UPDATE STEPS COUNT: {len(steps_in_result)} steps received")
            
            for idx, step in enumerate(steps_in_result):
                logger.info(f"🔍 WORKFLOW_RESULT STEP {idx+1}:")
                logger.info(f"🔍   RAW node_name: {step.get('node_name')} | action_name: {step.get('action_name')}")
                logger.info(f"🔍   RAW node_id: {step.get('node_id')} | action_id: {step.get('action_id')}")
                logger.info(f"🔍   RAW id: {step.get('id')} | step_id: {step.get('step_id')}")
                
                # WEBHOOK SPECIFIC DEBUG
                if step.get('node_name') == 'Webhook' or step.get('node_name') == 'Unknown_Node' or 'webhook' in str(step.get('node_name', '')).lower():
                    logger.info(f"🔍 WEBHOOK IN WORKFLOW_RESULT: Complete data:")
                    logger.info(f"🔍   {json.dumps(step, indent=2, default=str)}")
            
            # 🚨 PRESERVE PARAMS: Load existing context first
            # Load existing context from conversation memory to preserve parameters
            existing_context = await self.load_memory_context(db_session, chat_id)
            existing_steps = {}
            
            if existing_context and existing_context.get("workflow_context") and existing_context["workflow_context"].get("steps"):
                for step in existing_context["workflow_context"]["steps"]:
                    step_id = step.get("id")
                    if step_id:
                        existing_steps[step_id] = {
                            "params": step.get("params", {}),
                            "parameters": step.get("parameters", {}),
                            "params_meta": step.get("params_meta", []),
                            "parameters_metadata": step.get("parameters_metadata", [])
                        }
                        logger.debug(f"🔍 PRESERVED: Found existing params for step {step_id}: {step.get('params', {})}")
            
            # 🔧 DIRECT UPDATE: workflow_result contains complete state from workflow_engine
            steps = workflow_result.get("steps", [])
            
            # 🔧 MERGE: Preserve params if new ones are empty
            for step in steps:
                step_id = step.get("id")
                if step_id in existing_steps:
                    # Check if new params are empty/invalid
                    new_params = step.get("params", {})
                    new_parameters = step.get("parameters", {})
                    
                    # Detect empty/invalid parameters
                    params_empty = not new_params or all(v is None or v == "" or v == {} for v in new_params.values())
                    parameters_empty = not new_parameters or all(v is None or v == "" or v == {} for v in new_parameters.values())
                    
                    if params_empty and existing_steps[step_id]["params"]:
                        logger.warning(f"🔧 PRESERVING PARAMS: Step {step_id} ({step.get('node_name', 'unknown')}) has empty params, preserving existing")
                        step["params"] = existing_steps[step_id]["params"]
                        step["params_meta"] = existing_steps[step_id]["params_meta"]
                    
                    if parameters_empty and existing_steps[step_id]["parameters"]:
                        logger.warning(f"🔧 PRESERVING PARAMETERS: Step {step_id} ({step.get('node_name', 'unknown')}) has empty parameters, preserving existing")
                        step["parameters"] = existing_steps[step_id]["parameters"]
                        step["parameters_metadata"] = existing_steps[step_id]["parameters_metadata"]
            
            # 🔍 EXHAUSTIVE DEBUG: Log exactly what arrives in steps
            import json
            logger.info(f"🔍 DIRECT FORCE UPDATE: Processing {len(steps)} steps after parameter preservation")
            for idx, step in enumerate(steps):
                params_count = len(step.get("params", {}))
                logger.info(f"🔍 DIRECT FORCE UPDATE STEP {idx+1}:")
                logger.info(f"🔍   node_name: {step.get('node_name')} | action_name: {step.get('action_name')}")
                logger.info(f"🔍   node_id: {step.get('node_id')} | action_id: {step.get('action_id')}")
                logger.info(f"🔍   id: {step.get('id')} | step_id: {step.get('step_id')}")
                logger.info(f"🔍   params: {params_count} params")
                
                # 🔍 WEBHOOK ESPECÍFICO: Log completo si es webhook
                if step.get('node_name') == 'Webhook' or step.get('node_name') == 'Unknown_Node' or 'webhook' in str(step.get('node_name', '')).lower():
                    logger.info(f"🔍 WEBHOOK DETECTED: Full step data:")
                    logger.info(f"🔍   {json.dumps(step, indent=2, default=str)}")
            
            # 🔧 USE PROPER DTO SERIALIZATION: Convert to Pydantic DTOs for proper serialization (same as save method)
            try:
                from app.dtos.step_meta_dto import StepMetaDTO
                from app.dtos.workflow_creation_result_dto import WorkflowCreationResultDTO, WorkflowType
                
                # Convert dict steps to proper StepMetaDTO objects
                step_dtos = []
                for idx, step in enumerate(steps):
                    try:
                        # 🔍 EXHAUSTIVE DEBUG: Log every field before StepMetaDTO creation
                        step_id = step.get("id", step.get("step_id"))
                        step_node_id = step.get("node_id", step.get("id"))
                        step_action_id = step.get("action_id", step.get("id"))
                        step_node_name = step.get("node_name", "unknown")
                        step_action_name = step.get("action_name", "unknown")
                        
                        logger.info(f"🔍 STEP {idx+1} RAW DATA BEFORE DTO:")
                        logger.info(f"🔍   step['id']: {step.get('id')} (type: {type(step.get('id'))})")
                        logger.info(f"🔍   step['step_id']: {step.get('step_id')} (type: {type(step.get('step_id'))})")
                        logger.info(f"🔍   step['node_id']: {step.get('node_id')} (type: {type(step.get('node_id'))})")
                        logger.info(f"🔍   step['action_id']: {step.get('action_id')} (type: {type(step.get('action_id'))})")
                        logger.info(f"🔍   step['node_name']: {step.get('node_name')} (type: {type(step.get('node_name'))})")
                        logger.info(f"🔍   step['action_name']: {step.get('action_name')} (type: {type(step.get('action_name'))})")
                        
                        logger.info(f"🔍 STEP {idx+1} COMPUTED VALUES:")
                        logger.info(f"🔍   final_id: {step_id}")
                        logger.info(f"🔍   final_node_id: {step_node_id}")
                        logger.info(f"🔍   final_action_id: {step_action_id}")
                        logger.info(f"🔍   final_node_name: {step_node_name}")
                        logger.info(f"🔍   final_action_name: {step_action_name}")
                        
                        step_dto = StepMetaDTO(
                            id=step_id,
                            node_id=step_node_id,
                            action_id=step_action_id,
                            node_name=step_node_name,
                            action_name=step_action_name,
                            default_auth=step.get("default_auth"),
                            params=step.get("params", step.get("parameters", {})),
                            params_meta=step.get("params_meta", []),
                            uses_mcp=step.get("uses_mcp", False),
                            retries=step.get("retries", 0),
                            timeout_ms=step.get("timeout_ms"),
                            simulate=step.get("simulate", False),
                            next=step.get("next")
                        )
                        step_dtos.append(step_dto)
                        logger.info(f"✅ STEP {idx+1} DTO CREATED: {step_node_name} -> {step_action_name}")
                    except Exception as step_error:
                        logger.error(f"🔧 DIRECT FORCE UPDATE DTO ERROR STEP {idx+1}: {step_error}")
                        logger.error(f"🔧 FAILED STEP RAW DATA: {step}")
                        step_dtos.append(step)
                
                # 🔧 FIX: Filter oauth_requirements (same as above)
                raw_oauth_requirements = workflow_result.get("oauth_requirements", [])
                valid_oauth_requirements = []
                
                for oauth_req in raw_oauth_requirements:
                    try:
                        if (isinstance(oauth_req, dict) and 
                            oauth_req.get("type") == "oauth" and
                            oauth_req.get("node_id") and 
                            oauth_req.get("message") and
                            oauth_req.get("oauth_url") and
                            oauth_req.get("service_id")):
                            valid_oauth_requirements.append(oauth_req)
                        else:
                            logger.warning(f"🔧 FORCE UPDATE OAUTH FILTER: Skipping invalid oauth_requirement: {oauth_req}")
                    except Exception as oauth_error:
                        logger.warning(f"🔧 FORCE UPDATE OAUTH FILTER ERROR: {oauth_error}")
                
                logger.info(f"🔧 FORCE UPDATE OAUTH FILTER: Filtered {len(raw_oauth_requirements)} -> {len(valid_oauth_requirements)} valid oauth requirements")
                
                # 🔧 PRESERVE USER_INPUTS_PROVIDED: Extract from existing context
                existing_user_inputs = {}
                if existing_context and existing_context.get("user_inputs_provided"):
                    existing_user_inputs = existing_context["user_inputs_provided"]
                    logger.info(f"🔧 PRESERVE USER_INPUTS: Found existing user_inputs_provided: {existing_user_inputs}")
                
                # 🔧 MERGE USER_INPUTS: Combine with new ones (if any)
                new_user_inputs = workflow_result.get("user_inputs_provided", {})
                merged_user_inputs = {**existing_user_inputs, **new_user_inputs}
                logger.info(f"🔧 MERGE USER_INPUTS: Existing: {existing_user_inputs}, New: {new_user_inputs}, Merged: {merged_user_inputs}")

                # Create WorkflowCreationResultDTO
                workflow_dto = WorkflowCreationResultDTO(
                    status=workflow_result.get("status", "designed"),
                    workflow_type=WorkflowType.CLASSIC if workflow_result.get("workflow_type", "classic") == "classic" else WorkflowType.AGENT,
                    steps=[step.model_dump() if hasattr(step, 'model_dump') else step for step in step_dtos],
                    oauth_requirements=valid_oauth_requirements,
                    discovered_resources=workflow_result.get("discovered_resources", []),
                    confidence=workflow_result.get("confidence", 0.5),
                    next_actions=workflow_result.get("next_actions", []),
                    metadata=workflow_result.get("metadata", {}),
                    reply=workflow_result.get("reply")
                )
                
                # 🔧 ADD USER_INPUTS TO SERIALIZED CONTEXT: Manually add to JSON after Pydantic serialization
                workflow_dict = workflow_dto.model_dump()
                if merged_user_inputs:
                    workflow_dict["user_inputs_provided"] = merged_user_inputs
                    logger.info(f"🔧 ADD USER_INPUTS TO CONTEXT: Added user_inputs_provided to workflow context")
                
                # Use enhanced serialization with user_inputs_provided
                import json
                context_json = json.dumps(workflow_dict, default=str)
                logger.info(f"🔧 DIRECT FORCE UPDATE ENHANCED: Serialized {len(step_dtos)} steps with user_inputs_provided")
                
            except Exception as dto_error:
                logger.error(f"🔧 DIRECT FORCE UPDATE DTO ERROR: {dto_error}")
                # 🔧 FALLBACK WITH USER_INPUTS PRESERVATION
                existing_user_inputs = {}
                if existing_context and existing_context.get("user_inputs_provided"):
                    existing_user_inputs = existing_context["user_inputs_provided"]
                new_user_inputs = workflow_result.get("user_inputs_provided", {})
                merged_user_inputs = {**existing_user_inputs, **new_user_inputs}
                
                workflow_context = {
                    "type": "workflow_context",
                    "steps": steps,
                    "confidence": workflow_result.get("confidence", 0.5),
                    "workflow_type": workflow_result.get("workflow_type", "classic"),
                    "metadata": workflow_result.get("metadata", {}),
                    "oauth_requirements": workflow_result.get("oauth_requirements", []),
                    "status": workflow_result.get("status", "designed"),
                    "created_at": workflow_result.get("created_at")
                }
                if merged_user_inputs:
                    workflow_context["user_inputs_provided"] = merged_user_inputs
                    logger.info(f"🔧 FALLBACK USER_INPUTS: Added user_inputs_provided to fallback context")
                context_json = json.dumps(workflow_context, default=str)
            
            # 🔍 DEBUG: Log final serialized content
            logger.info(f"🔍 DIRECT FORCE UPDATE FINAL DEBUG: Serialized content length: {len(context_json)}")
            
            # Get all messages to find and replace the workflow context message
            history = await self.load_conversation_history(db_session, chat_id)
            
            # Find the workflow context message to update
            for msg in reversed(history):
                if msg.get("role") == "system" and msg.get("content", "").startswith("WORKFLOW_CONTEXT:"):
                    # Update the message content with new context
                    new_content = f"WORKFLOW_CONTEXT: {context_json}"
                    
                    # Update the message in database
                    message_id = msg.get("message_id")
                    if message_id:
                        await self.repo.update_message_content(db_session, message_id, new_content)
                        logger.info(f"🔧 DIRECT FORCE UPDATE: Updated complete workflow context with {len(workflow_result.get('steps', []))} steps")
                        return
                    break
            
            logger.warning(f"🧠 DIRECT FORCE UPDATE: Could not find workflow context message to update")
            
        except Exception as e:
            logger.error(f"🧠 ERROR: Could not force update workflow context: {e}")
    
    async def update_workflow_context_status(
        self,
        db_session: AsyncSession,
        chat_id: str,
        user_id: int,
        status_update: Dict[str, Any]
    ):
        """
        🔧 NEW: Updates existing workflow context status without creating duplicate
        """
        try:
            # Load existing context from conversation memory
            existing_context = await self.load_memory_context(db_session, chat_id)
            if not existing_context:
                logger.warning(f"🧠 UPDATE: No existing context found for chat {chat_id}")
                return
            
            # Update context with new status data
            updated_context = existing_context.copy()
            updated_context.update(status_update)
            
            # Get all messages to find and replace the workflow context message
            history = await self.load_conversation_history(db_session, chat_id)
            
            # Find the workflow context message to update
            import json
            for msg in reversed(history):
                if msg.get("role") == "system" and msg.get("content", "").startswith("WORKFLOW_CONTEXT:"):
                    # Update the message content with new context
                    context_json = json.dumps(updated_context, default=str)
                    new_content = f"WORKFLOW_CONTEXT: {context_json}"
                    
                    # Update the message in database
                    message_id = msg.get("message_id")
                    if message_id:
                        await self.repo.update_message_content(db_session, message_id, new_content)
                        logger.info(f"🧠 UPDATE: Updated workflow context status to {status_update.get('status', 'unknown')}")
                        return
                    break
            
            logger.warning(f"🧠 UPDATE: Could not find workflow context message to update")
            
        except Exception as e:
            logger.error(f"🧠 ERROR: Could not update workflow context status: {e}")
    
    
    async def save_smart_forms_memory(
        self,
        db_session: AsyncSession,
        chat_id: str,
        user_id: int,
        smart_forms_data: List[Dict[str, Any]]
    ):
        """
        Guarda la memoria de smart forms generados para evitar duplicación
        """
        try:
            import json
            context_json = json.dumps(smart_forms_data, default=str)
            await self._save_message(db_session, chat_id, user_id, "system", f"SMART_FORMS_MEMORY: {context_json}")
            logger.debug(f"🧠 SMART_FORMS: Guardados {len(smart_forms_data)} smart forms en memoria")
        except Exception as e:
            logger.error(f"🧠 ERROR: No se pudo guardar smart forms memory: {e}")
    
    async def save_oauth_completion(
        self,
        db_session: AsyncSession,
        chat_id: str,
        user_id: int,
        completed_services: List[str]
    ):
        """
        Guarda el estado de OAuth completado para servicios específicos
        """
        try:
            logger.info(f"🧠 OAUTH MEMORY: Starting save - chat_id: {chat_id}, user_id: {user_id}, services: {completed_services}")
            import json
            context_json = json.dumps(completed_services, default=str)
            logger.info(f"🧠 OAUTH MEMORY: JSON serialized: {context_json}")
            await self._save_message(db_session, chat_id, user_id, "system", f"OAUTH_COMPLETED: {context_json}")
            logger.info(f"🧠 OAUTH: Successfully saved OAuth completion for services: {completed_services}")
        except Exception as e:
            logger.error(f"🧠 ERROR: Failed to save OAuth completion: {e}", exc_info=True)
            raise
    
    async def save_user_inputs_memory(
        self,
        db_session: AsyncSession,
        chat_id: str,
        user_id: int,
        user_inputs: Dict[str, Any]
    ):
        """
        🔧 SUPER FIX: Guarda parámetros del SmartForm PRESERVANDO COMPLETAMENTE el workflow context existente
        
        PROBLEMA IDENTIFICADO: Mi fix anterior cargaba load_memory_context() que NO incluye workflow steps.
        SOLUCIÓN: Usar WorkflowContextService que SÍ incluye los steps con default_auth.
        """
        try:
            import json
            
            # 🚨 CRITICAL FIX: Load WORKFLOW context, not memory context!
            logger.info(f"🔧 SUPER FIX: Loading WORKFLOW context to preserve default_auth and steps")
            # ✅ REFACTORED: Use WorkflowContextService instead of deprecated load_workflow_context
            # 🚨 REMOVED: workflow_context_service - using execution_plan directly
            # 🔧 FIX: Load existing workflow context from memory since workflow_context param doesn't exist
            memory_context = await self.load_memory_context(db_session, chat_id)
            existing_workflow_context = memory_context.get("workflow_context") if memory_context else None
            
            if existing_workflow_context:
                # 🔧 PRESERVE EVERYTHING: Keep all existing workflow data
                preserved_context = existing_workflow_context.copy()
                
                # 🔧 ADD USER INPUTS: Only add user inputs without overwriting anything else
                if "user_inputs_provided" not in preserved_context:
                    preserved_context["user_inputs_provided"] = {}
                preserved_context["user_inputs_provided"].update(user_inputs)
                
                logger.info(f"🔧 SUPER FIX: Preserved complete workflow context with {len(preserved_context.get('steps', []))} steps")
                logger.info(f"🔧 SUPER FIX: Added {len(user_inputs)} user inputs to existing context")
                
                # Log steps for debugging
                steps = preserved_context.get("steps", [])
                for i, step in enumerate(steps):
                    node_name = step.get("node_name", "unknown")
                    default_auth = step.get("default_auth")
                    logger.info(f"🔧 SUPER FIX: Step {i+1} ({node_name}) default_auth = {default_auth}")
                
                # 🔧 OVERWRITE COMPLETELY: Replace the WORKFLOW_CONTEXT message entirely
                context_json = json.dumps(preserved_context, default=str)
                
                # Find and update the existing WORKFLOW_CONTEXT message
                history = await self.load_conversation_history(db_session, chat_id)
                for msg in reversed(history):
                    if msg.get("role") == "system" and msg.get("content", "").startswith("WORKFLOW_CONTEXT:"):
                        message_id = msg.get("message_id")
                        if message_id:
                            new_content = f"WORKFLOW_CONTEXT: {context_json}"
                            await self.repo.update_message_content(db_session, message_id, new_content)
                            logger.info(f"🔧 SUPER FIX: Updated existing WORKFLOW_CONTEXT with user inputs preserved")
                            return
                        break
                
                # If no existing message found, create new one
                await self._save_message(db_session, chat_id, user_id, "system", f"WORKFLOW_CONTEXT: {context_json}")
                logger.info(f"🔧 SUPER FIX: Created new WORKFLOW_CONTEXT with preserved data")
                
            else:
                # 🔧 FALLBACK: Load memory context if no workflow context exists
                logger.warning(f"🔧 SUPER FIX: No workflow context found, loading memory context as fallback")
                existing_context = await self.load_memory_context(db_session, chat_id)
                
                if existing_context and "user_inputs_provided" in existing_context:
                    # 🔧 CRITICAL FIX: Preserve existing workflow_steps and default_auth_mapping from memory
                    existing_context["user_inputs_provided"].update(user_inputs)
                    
                    # 🔧 FIELD NAME CONSISTENCY: Ensure both "steps" and "workflow_steps" are preserved
                    if "steps" not in existing_context and "workflow_steps" not in existing_context:
                        existing_context["steps"] = []
                        existing_context["workflow_steps"] = []
                    elif "steps" not in existing_context:
                        existing_context["steps"] = existing_context.get("workflow_steps", [])
                    elif "workflow_steps" not in existing_context:
                        existing_context["workflow_steps"] = existing_context.get("steps", [])
                    
                    if "default_auth_mapping" not in existing_context:
                        existing_context["default_auth_mapping"] = {}
                    
                    logger.info(f"🔧 SUPER FIX FALLBACK: Merged {len(user_inputs)} new inputs with existing memory context")
                    logger.info(f"🔧 SUPER FIX FALLBACK: Preserved {len(existing_context.get('workflow_steps', []))} existing workflow steps")
                else:
                    # 🔧 CRITICAL FIX: When creating new context, try to get workflow_steps from existing memory first
                    fallback_context = {
                        "smart_forms_generated": [],
                        "oauth_completed_services": [],
                        "user_inputs_provided": user_inputs,
                        "selected_services": [],
                        "steps": [],  # 🔧 FIXED: Use "steps" consistent with loading logic
                        "workflow_steps": [],  # 🔧 BACKWARD COMPATIBILITY: Keep both for now  
                        "default_auth_mapping": {}
                    }
                    
                    # Try to preserve workflow_steps from existing_context if it exists but just doesn't have user_inputs_provided
                    if existing_context:
                        # 🔧 FIELD NAME CONSISTENCY: Check both "steps" and "workflow_steps" for compatibility
                        existing_steps = existing_context.get("steps", existing_context.get("workflow_steps", []))
                        fallback_context["steps"] = existing_steps
                        fallback_context["workflow_steps"] = existing_steps  # Backward compatibility
                        fallback_context["default_auth_mapping"] = existing_context.get("default_auth_mapping", {})
                        fallback_context["smart_forms_generated"] = existing_context.get("smart_forms_generated", [])
                        fallback_context["oauth_completed_services"] = existing_context.get("oauth_completed_services", [])
                        fallback_context["selected_services"] = existing_context.get("selected_services", [])
                        logger.info(f"🔧 SUPER FIX FALLBACK: Preserved {len(existing_steps)} workflow steps from existing context")
                    
                    existing_context = fallback_context
                    logger.info(f"🔧 SUPER FIX FALLBACK: Created new context with {len(user_inputs)} inputs and {len(existing_context['workflow_steps'])} preserved steps")
                
                context_json = json.dumps(existing_context, default=str)
                await self._save_message(db_session, chat_id, user_id, "system", f"WORKFLOW_CONTEXT: {context_json}")
                logger.info(f"🔧 SUPER FIX FALLBACK: Successfully saved fallback context")
            
        except Exception as e:
            logger.error(f"🔧 SUPER FIX ERROR: Failed to preserve workflow context: {e}")
            # Final fallback to original behavior
            try:
                context_json = json.dumps(user_inputs, default=str)
                await self._save_message(db_session, chat_id, user_id, "system", f"USER_INPUTS_MEMORY: {context_json}")
                logger.warning(f"🔧 SUPER FIX: Used original method due to complete failure")
            except Exception as fallback_error:
                logger.error(f"🔧 SUPER FIX: All methods failed: {fallback_error}")
                raise
    
    async def save_selected_services_memory(
        self,
        db_session: AsyncSession,
        chat_id: str,
        user_id: int,
        selected_services: List[str]
    ):
        """
        Guarda servicios seleccionados por el usuario para mantener persistencia
        """
        try:
            import json
            context_json = json.dumps(selected_services, default=str)
            await self._save_message(db_session, chat_id, user_id, "system", f"SELECTED_SERVICES: {context_json}")
            logger.debug(f"🧠 SELECTED_SERVICES: Guardados {len(selected_services)} servicios seleccionados")
        except Exception as e:
            logger.error(f"🧠 ERROR: No se pudo guardar selected services memory: {e}")
    
    async def load_memory_context(self, db_session: AsyncSession, chat_id: str) -> Dict[str, Any]:
        """
        Recupera toda la memoria de contexto para prevenir duplicación de acciones
        """
        try:
            import json
            logger.info(f"🔧 DEBUG LOAD_MEMORY_CONTEXT: Starting for chat_id {chat_id}")
            
            # Obtener historial completo
            history = await self.load_conversation_history(db_session, chat_id)
            logger.info(f"🔧 DEBUG LOAD_MEMORY_CONTEXT: Found {len(history)} messages in history")
            
            # 🚨 ENHANCED DEBUG: Log all WORKFLOW_CONTEXT messages found
            workflow_contexts = []
            for msg in history:
                if msg.get("role") == "system" and msg.get("content", "").startswith("WORKFLOW_CONTEXT:"):
                    workflow_contexts.append({
                        "message_id": msg.get("message_id", "unknown"),
                        "created_at": msg.get("created_at", "unknown"),
                        "content_preview": msg.get("content", "")[:200] + "..." if len(msg.get("content", "")) > 200 else msg.get("content", "")
                    })
            logger.info(f"🔧 DEBUG WORKFLOW_CONTEXTS FOUND: {len(workflow_contexts)} contexts")
            for i, ctx in enumerate(workflow_contexts):
                logger.info(f"🔧 DEBUG WORKFLOW_CONTEXT {i+1}: ID={ctx['message_id']}, created={ctx['created_at']}")
                logger.info(f"🔧 DEBUG WORKFLOW_CONTEXT {i+1} PREVIEW: {ctx['content_preview']}")
            
            memory_context = {
                "smart_forms_generated": [],
                "oauth_completed_services": [],
                "user_inputs_provided": {},
                "selected_services": [],
                "workflow_steps": [],
                "default_auth_mapping": {}
            }
            
            # Buscar diferentes tipos de memoria en el historial
            for msg in reversed(history):
                if msg.get("role") == "system":
                    content = msg.get("content", "")
                    
                    if content.startswith("SMART_FORMS_MEMORY:"):
                        try:
                            context_json = content.replace("SMART_FORMS_MEMORY: ", "")
                            memory_context["smart_forms_generated"] = json.loads(context_json)
                        except:
                            pass
                    
                    elif content.startswith("OAUTH_COMPLETED:"):
                        try:
                            context_json = content.replace("OAUTH_COMPLETED: ", "")
                            memory_context["oauth_completed_services"] = json.loads(context_json)
                        except:
                            pass
                    
                    elif content.startswith("USER_INPUTS_MEMORY:"):
                        try:
                            context_json = content.replace("USER_INPUTS_MEMORY: ", "")
                            memory_context["user_inputs_provided"] = json.loads(context_json)
                        except:
                            pass
                    
                    elif content.startswith("WORKFLOW_CONTEXT:"):
                        try:
                            logger.info(f"🔧 DEBUG FOUND WORKFLOW_CONTEXT in message {msg.get('role')}")
                            context_json = content.replace("WORKFLOW_CONTEXT: ", "")
                            workflow_data = json.loads(context_json)
                            logger.info(f"🔧 DEBUG WORKFLOW_CONTEXT parsed: {list(workflow_data.keys())}")
                            
                            # Extract ALL workflow data (not just user_inputs)
                            if "user_inputs_provided" in workflow_data:
                                logger.info(f"🔧 DEBUG FOUND user_inputs_provided: {workflow_data['user_inputs_provided']}")
                                memory_context["user_inputs_provided"].update(workflow_data["user_inputs_provided"])
                            
                            # 🔧 CRITICAL FIX: Extract workflow_steps with default_auth from COMPLETE workflow object
                            steps_to_extract = []
                            
                            # workflow_data can be either:
                            # 1. Direct array: [{"step1"}, {"step2"}] 
                            # 2. Workflow object: {"status": "...", "steps": [...], "workflow_type": "..."}
                            if isinstance(workflow_data, list):
                                # Direct array of steps
                                steps_to_extract = workflow_data
                                logger.info(f"🔧 WORKFLOW FORMAT: Direct array with {len(steps_to_extract)} steps")
                            elif isinstance(workflow_data, dict):
                                # 🔧 FIELD NAME CONSISTENCY: Check both "steps" and "workflow_steps" for compatibility
                                if "steps" in workflow_data:
                                    steps_to_extract = workflow_data["steps"]
                                    logger.info(f"🔧 WORKFLOW FORMAT: Object format with 'steps' field, {len(steps_to_extract)} steps")
                                elif "workflow_steps" in workflow_data:
                                    steps_to_extract = workflow_data["workflow_steps"]
                                    logger.info(f"🔧 WORKFLOW FORMAT: Object format with 'workflow_steps' field, {len(steps_to_extract)} steps")
                                else:
                                    logger.warning(f"🔧 WORKFLOW FORMAT: Dict but no 'steps' or 'workflow_steps' key, keys: {list(workflow_data.keys())}")
                                    
                                if steps_to_extract:
                                    logger.info(f"🔧 WORKFLOW METADATA: status={workflow_data.get('status')}, type={workflow_data.get('workflow_type')}")
                            
                            if steps_to_extract:
                                logger.info(f"🔧 DEBUG FOUND steps: {len(steps_to_extract)} steps")
                                logger.info(f"🔧 CRITICAL DEBUG: About to set workflow_steps in memory_context")
                                # 🔧 FIELD NAME CONSISTENCY: Set both "steps" and "workflow_steps" for compatibility
                                memory_context["steps"] = steps_to_extract
                                memory_context["workflow_steps"] = steps_to_extract
                                logger.info(f"🔧 CRITICAL DEBUG: steps set, length check: {len(memory_context['steps'])}")
                                logger.info(f"🔧 CRITICAL DEBUG: workflow_steps set, length check: {len(memory_context['workflow_steps'])}")
                                
                                # Create default_auth mapping for easy access
                                default_auth_mapping = {}
                                for idx, step in enumerate(steps_to_extract):
                                    if isinstance(step, dict):
                                        node_name = step.get("node_name")
                                        default_auth = step.get("default_auth")
                                        step_id = step.get("id", f"step_{idx}")
                                        
                                        logger.info(f"🔧 STEP DEBUG {idx+1}: node={node_name}, auth={default_auth}, id={step_id}")
                                        
                                        if node_name and default_auth:
                                            default_auth_mapping[node_name] = default_auth
                                            logger.info(f"🔧 MAPPING: {node_name} -> {default_auth}")
                                        elif default_auth:
                                            # Fallback to step ID if no node_name
                                            default_auth_mapping[step_id] = default_auth
                                            logger.info(f"🔧 MAPPING FALLBACK: {step_id} -> {default_auth}")
                                
                                memory_context["default_auth_mapping"] = default_auth_mapping
                                logger.info(f"🔧 MEMORY COMPLETE: Loaded {len(steps_to_extract)} workflow steps with auth mapping: {default_auth_mapping}")
                            else:
                                logger.warning(f"🔧 MEMORY: No steps found in workflow_data")
                            
                        except Exception as e:
                            logger.warning(f"🔧 WORKFLOW_CONTEXT parse error: {e}")
                            pass
                    
                    elif content.startswith("SELECTED_SERVICES:"):
                        try:
                            context_json = content.replace("SELECTED_SERVICES: ", "")
                            memory_context["selected_services"] = json.loads(context_json)
                        except:
                            pass
                    
            
            logger.info(f"🔧 DEBUG LOAD_MEMORY_CONTEXT RESULT: user_inputs_provided = {memory_context['user_inputs_provided']}")
            logger.debug(f"🧠 MEMORY: Recuperado contexto de memoria para chat {chat_id}")
            return memory_context
            
        except Exception as e:
            logger.error(f"🧠 ERROR: No se pudo cargar memory context: {e}")
            return {
                "smart_forms_generated": [],
                "oauth_completed_services": [],
                "user_inputs_provided": {},
                "selected_services": [],
                "workflow_steps": [],
                "default_auth_mapping": {}
            }

    async def load_conversation_history(self, db_session: AsyncSession, chat_id: str) -> List[Dict[str, Any]]:
        """
        Recupera todo el historial de conversación de la memoria persistente
        """
        try:
            # Convertir chat_id a UUID si es string
            chat_uuid = UUID(chat_id) if isinstance(chat_id, str) else chat_id
            
            # Obtener mensajes usando el Repository
            messages = await self.repo.get_messages_by_session(db_session, chat_uuid)
            
            # Convertir a formato que espera el LLM
            history = []
            for msg in messages:
                history.append({
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.created_at.isoformat() if msg.created_at else None,
                    "message_id": str(msg.message_id) if hasattr(msg, 'message_id') else None  # 🔧 FIX: Add message_id for updates
                })
            
            logger.debug(f"🧠 MEMORIA: Recuperados {len(history)} mensajes del chat {chat_id}")
            return history
            
        except Exception as e:
            logger.error(f"🧠 ERROR MEMORIA: No se pudo cargar historial: {e}")
            return []
    
    async def _save_message(
        self, 
        db_session: AsyncSession, 
        chat_id: str, 
        user_id: int, 
        role: str, 
        content: str
    ):
        """
        Guarda un mensaje en la memoria persistente usando Repository pattern
        """
        try:
            logger.info(f"🧠 MEMORIA: _save_message called - chat_id: {chat_id}, user_id: {user_id}, role: {role}")
            logger.info(f"🔄 MEMORY TRANSACTION: db.is_active: {db_session.is_active}, in_transaction: {db_session.in_transaction()}")
            
            # Convertir chat_id a UUID si es string
            chat_uuid = UUID(chat_id) if isinstance(chat_id, str) else chat_id
            logger.info(f"🧠 MEMORIA: chat_uuid converted: {chat_uuid}")
            
            # 1. Verificar que existe la sesión usando Repository
            logger.info(f"🧠 MEMORIA: Getting chat session...")
            session = await self.repo.get_chat_session(db_session, chat_uuid)
            logger.info(f"🧠 MEMORIA: Existing session: {session}")
            
            if not session:
                # Crear sesión usando Repository (hace flush)
                logger.info(f"🧠 MEMORIA: Creating new chat session...")
                session = await self.repo.create_chat_session(db_session, chat_uuid, user_id)
                logger.info(f"🧠 MEMORIA: Created session: {session}")
            
            # 2. Crear mensaje usando Repository (hace flush)
            logger.info(f"🧠 MEMORIA: Creating message...")
            message = await self.repo.create_message(db_session, chat_uuid, role, content)
            logger.info(f"🧠 MEMORIA: Created message: {message}")
            
            # 3. Service hace flush pero no commit - deja que el caller haga commit
            logger.info(f"🧠 MEMORIA: Flushing session...")
            logger.info(f"🔄 MEMORY PRE-FLUSH: db.in_transaction: {db_session.in_transaction()}")
            await db_session.flush()
            logger.info(f"🧠 MEMORIA: Session flushed successfully")
            logger.info(f"🔄 MEMORY POST-FLUSH: db.in_transaction: {db_session.in_transaction()}")
            
            logger.info(f"🧠 MEMORIA: Successfully saved message {role}: {content[:100]}...")
            
        except Exception as e:
            logger.error(f"🧠 ERROR MEMORIA: Failed to save message: {e}", exc_info=True)
            logger.error(f"🔄 MEMORY ERROR STATE: db.is_active: {db_session.is_active}, in_transaction: {db_session.in_transaction()}")
            logger.error(f"🧠 ERROR MEMORIA: Rolling back session...")
            await db_session.rollback()
            logger.error(f"🧠 ERROR MEMORIA: Session rolled back")
            logger.error(f"🔄 MEMORY POST-ROLLBACK: db.in_transaction: {db_session.in_transaction()}")
            raise


# Singleton instance
_conversation_memory_service = None

def get_conversation_memory_service() -> ConversationMemoryService:
    """
    Obtiene la instancia singleton del ConversationMemoryService
    """
    global _conversation_memory_service
    if _conversation_memory_service is None:
        _conversation_memory_service = ConversationMemoryService()
    return _conversation_memory_service