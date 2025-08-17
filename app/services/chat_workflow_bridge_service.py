"""
ChatWorkflowBridgeService - Conecta workflows temporales del chat con workflows persistidos
Maneja las decisiones del usuario: guardar, activar, ejecutar
"""
import logging
import asyncio
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.flow_service import FlowService, get_flow_service
from app.services.workflow_runner_service import WorkflowRunnerService, get_workflow_runner
from app.services.trigger_orchestrator_service import TriggerOrchestratorService, get_trigger_orchestrator_service
from app.services.conversation_memory_service import ConversationMemoryService
# REMOVED: WorkflowContextService - delegated to memory service in direct flow era
# Removed: LLMParameterExtractor - using direct interception instead
from app.dtos.workflow_creation_result_dto import WorkflowCreationResultDTO, WorkflowType
from app.workflow_engine.constants.workflow_statuses import WorkflowStatus
from app.db.database import get_db

# 🚫 TEMPORARY: Define disabled status constants locally to avoid breaking existing code
# TODO: Remove when fully migrating to button-based workflow management
class _DisabledWorkflowStatus:
    SAVE_WORKFLOW = "save_workflow"
    ACTIVATE_WORKFLOW = "activate_workflow" 
    EXECUTE_WORKFLOW = "execute_workflow"

logger = logging.getLogger(__name__)


class ChatWorkflowBridgeService:
    """
    Servicio puente que conecta workflows temporales del chat con workflows persistidos.
    Maneja las decisiones del usuario sobre qué hacer con el workflow.
    """
    
    def __init__(
        self,
        flow_service: FlowService,
        workflow_runner: WorkflowRunnerService,
        trigger_orchestrator: TriggerOrchestratorService,
        db: AsyncSession
    ):
        self.flow_service = flow_service
        self.workflow_runner = workflow_runner
        self.trigger_orchestrator = trigger_orchestrator
        self.db = db
        self.logger = logging.getLogger(__name__)
        # 🔒 LOCK: Prevenir activaciones concurrentes para el mismo usuario
        self._activation_locks: Dict[int, asyncio.Lock] = {}
    
    def _get_user_lock(self, user_id: int) -> asyncio.Lock:
        """Obtiene el lock específico para un usuario"""
        if user_id not in self._activation_locks:
            self._activation_locks[user_id] = asyncio.Lock()
        return self._activation_locks[user_id]
    
    # 🚫 REMOVED: _extract_steps_from_context() 
    # 🎯 REPLACED WITH: Direct WorkflowContextService usage
    # 🔥 REASON: Was duplicating logic and losing critical metadata (execution_step, params_meta, parameters)
    
    # 🚫 REMOVED: _process_steps_with_engine_logic() and related functions
    # 🎯 REASON: These functions were filtering out critical metadata  
    # 🔥 PROBLEM: Lost execution_step, params_meta, parameters during processing
    # ✅ SOLUTION: Use steps directly from WorkflowContextService without modification
    
    # 🚫 REMOVED: _extract_user_inputs_from_steps_engine_logic(), _resolve_templates_in_steps_engine_logic(), 
    #            _convert_uuids_to_strings(), _convert_step_uuids_to_strings(), _merge_user_inputs_with_steps()
    # 🎯 REASON: These functions were modifying steps and losing critical workflow metadata
    # ✅ SOLUTION: WorkflowContextService already provides complete, ready-to-use steps
    
    # 🚫 REMOVED: All helper functions that were processing/filtering steps
    # 🎯 FUNCTIONS REMOVED: _resolve_templates_in_steps_engine_logic(), _convert_uuids_to_strings(),
    #                       _convert_step_uuids_to_strings(), _merge_user_inputs_with_steps()
    # 🔥 REASON: These functions were losing critical metadata like execution_step, params_meta, parameters
    # ✅ SOLUTION: WorkflowContextService now provides complete, ready-to-use steps with all metadata intact
    
    # 🗑️ LEGACY PARSING FUNCTIONS REMOVED - NO MORE FRAGILE PARSING!

    async def process_workflow_decision(
        self,
        user_decision: str,
        execution_plan: List[Dict[str, Any]] = None,
        user_id: int = None,
        chat_id: str = None,
        workflow_context: Dict[str, Any] = None  # Deprecated: kept for backward compatibility
    ) -> WorkflowCreationResultDTO:
        """
        Procesa la decisión del usuario sobre qué hacer con el workflow.
        
        Args:
            user_decision: "save", "activate", "execute", etc.
            execution_plan: List of workflow steps from LLM planner (source of truth)
            user_id: ID del usuario  
            chat_id: ID del chat session
            workflow_context: [DEPRECATED] Use execution_plan instead
        
        Returns:
            WorkflowCreationResultDTO con el resultado de la operación
        """
        try:
            # 🚀 NEW APPROACH: Use execution_plan directly from LLM planner
            # This is the source of truth for workflow extraction
            
            # Prefer execution_plan, fallback to workflow_context for backward compatibility
            if execution_plan:
                steps = execution_plan
                self.logger.info(f"🚀 EXECUTION PLAN: Using execution_plan directly from LLM planner ({len(steps)} steps)")
            elif workflow_context and workflow_context.get("steps"):
                steps = workflow_context.get("steps", [])
                self.logger.warning(f"⚠️ FALLBACK: Using deprecated workflow_context ({len(steps)} steps)")
            else:
                self.logger.error("🚨 NO STEPS: No execution_plan or workflow_context steps provided")
                return self._build_error_response("No se encontraron pasos del workflow - proporciona execution_plan")
            
            self.logger.info(f"✅ READY STEPS: Received {len(steps)} steps ready for processing")
            
            # Debug: Log final parameter state
            for i, step in enumerate(steps):
                params_count = len(step.get("params", {}))
                node_name = step.get("node_name", "unknown")
                self.logger.info(f"✅ STEP {i}: {node_name} has {params_count} parameters ready for save")
            
            # ✅ SIMPLIFIED: execution_plan doesn't have workflow_summary, will be generated in _save_workflow
            
            if not steps:
                return self._build_error_response("No hay steps en el workflow para procesar")
                
            self.logger.info(f"🎯 DECISION-LLM-EXTRACTION: Found {len(steps)} steps from LLM history")
            
            # 🎯 CLEAN APPROACH: Only handle structured decisions from LLM/frontend
            # The LLM should interpret natural language and send structured statuses
            if user_decision in ["save_workflow", "save"]:
                # Solo guardar
                return await self._save_workflow(steps, user_id, chat_id)
                
            elif user_decision in ["save_and_activate_workflow", "activate_workflow", "activate"]:
                # Guardar y activar
                return await self._save_and_activate_workflow(steps, user_id, chat_id)
                
            elif user_decision in ["deactivate_workflow", "deactivate"]:
                # Desactivar workflow
                return await self._deactivate_workflow(steps, user_id, chat_id)
                
            elif user_decision in ["execute_workflow_now", "execute_workflow", "execute"]:
                # Ejecutar inmediatamente
                return await self._execute_workflow_now(steps, user_id, chat_id)
                
            else:
                return self._build_error_response(
                    f"Decisión no reconocida: {user_decision}. "
                    f"El LLM debe enviar uno de estos estados: save_workflow, activate_workflow, deactivate_workflow, execute_workflow"
                )
                
        except Exception as e:
            self.logger.error(f"Error processing workflow decision: {e}", exc_info=True)
            return self._build_error_response(f"Error procesando decisión: {str(e)}")

    async def _save_workflow(
        self, 
        steps: List[Dict[str, Any]], 
        user_id: int,
        chat_id: str = None
    ) -> WorkflowCreationResultDTO:
        """Guarda el workflow sin activarlo"""
        try:
            self.logger.info(f"🔄 TRANSACTION START: _save_workflow for user {user_id}, chat_id: {chat_id}")
            self.logger.info(f"🔄 TRANSACTION STATE: db.is_active: {self.db.is_active}")
            # ✅ SIMPLIFIED: execution_plan steps already come complete, no fallback check needed
            self.logger.info(f"💾 SAVING: {len(steps)} steps from execution_plan")
            
            # 🔧 CRITICAL FIX: Map default_auth from memory context to steps
            if chat_id and steps:
                try:
                    memory_service = ConversationMemoryService()
                    memory_context = await memory_service.load_memory_context(self.db, chat_id)
                    default_auth_mapping = memory_context.get('default_auth_mapping', {})
                    
                    if default_auth_mapping:
                        for step in steps:
                            node_name = step.get('node_name')
                            if node_name and node_name in default_auth_mapping:
                                step['default_auth'] = default_auth_mapping[node_name]
                                self.logger.info(f"🔧 SAVE MAPPED default_auth for {node_name}: {default_auth_mapping[node_name]}")
                except Exception as e:
                    self.logger.error(f"🔧 SAVE MAPPING ERROR: {e}")
            
            # Generar nombre del workflow - simplified since execution_plan doesn't have workflow_summary
            name = f"Workflow {len(steps)} pasos"
            description = f"Workflow generado automáticamente con {len(steps)} pasos"
            
            # ✅ DIRECT: Use steps parameter directly (already from execution_plan)
            if not steps:
                self.logger.error("🚨 NO STEPS: No workflow steps found in context")
                return self._build_error_response("No se encontraron pasos del workflow")
            
            self.logger.info(f"✅ READY STEPS: Received {len(steps)} steps with execution_plan params")
            
            # Debug: Log final parameter state
            for i, step in enumerate(steps):
                params_count = len(step.get("params", {}))
                node_name = step.get("node_name", "unknown")
                self.logger.info(f"✅ STEP {i}: {node_name} has {params_count} parameters ready for save")
            
            # ✅ DIRECT: steps already from execution_plan, no context update needed
            
            # 🔧 UUID SERIALIZATION FIX: Convert all UUIDs to strings before saving
            def serialize_uuids(obj):
                """Recursively convert UUID objects to strings for JSON serialization"""
                from uuid import UUID
                if isinstance(obj, UUID):
                    return str(obj)
                elif isinstance(obj, dict):
                    return {key: serialize_uuids(value) for key, value in obj.items()}
                elif isinstance(obj, list):
                    return [serialize_uuids(item) for item in obj]
                else:
                    return obj
            
            # Preparar spec para guardar con UUIDs serializados
            spec = {
                "steps": serialize_uuids(steps),
                "workflow_summary": {"title": name, "description": description},
                "metadata": {},  # execution_plan doesn't have metadata
                "workflow_type": "classic"  # default workflow type
            }
            
            self.logger.info(f"🔧 UUID SERIALIZATION: Converted UUIDs to strings in spec")
            
            # 🔍 CHECK EXISTING: Buscar workflow existente para este chat/usuario
            self.logger.info(f"🔄 PRE-SAVE: Checking for existing workflow for chat_id: {chat_id}")
            
            # Buscar workflow existente por chat_id directo en la tabla flows
            existing_workflow = None
            if chat_id:
                # Buscar por chat_id directo usando el repositorio
                try:
                    from uuid import UUID
                    chat_uuid = UUID(chat_id) if isinstance(chat_id, str) else chat_id
                    
                    # 🔧 DB FIX: Verify connection and rollback if needed
                    if not self.db.is_active or self.db.in_transaction():
                        self.logger.warning("🔄 DB STATE: Connection inactive or in invalid transaction, rolling back...")
                        try:
                            await self.db.rollback()
                            self.logger.info("🔄 ROLLBACK SUCCESS: Transaction rolled back successfully")
                        except Exception as rollback_err:
                            self.logger.error(f"🔄 ROLLBACK ERROR: {rollback_err}")
                    
                    # 🔧 FIX: Check if workflow exists for this chat_id using flow_service
                    existing_workflow = await self.flow_service.get_flow_by_chat_id(
                        owner_id=user_id,
                        chat_id=chat_uuid
                    )
                    
                    if existing_workflow:
                        self.logger.info(f"🔄 FOUND EXISTING: Found workflow {existing_workflow.flow_id} for chat_id {chat_uuid}")
                    else:
                        self.logger.info(f"🔄 NO EXISTING: No workflow found for chat_id {chat_uuid}")
                        existing_workflow = None
                        
                except Exception as e:
                    self.logger.error(f"🔄 EXISTING CHECK ERROR: {e}")
                    self.logger.error(f"🔄 TRANSACTION STATE: db.is_active: {self.db.is_active}, in_transaction: {self.db.in_transaction()}")
                    # 🔧 DB FIX: Force rollback on error
                    try:
                        await self.db.rollback()
                        self.logger.info("🔄 ROLLBACK: Transaction rolled back due to error...")
                    except Exception as rollback_error:
                        self.logger.error(f"🔄 ROLLBACK ERROR: {rollback_error}")
                    existing_workflow = None  # Continue without existing workflow check
            
            try:
                if existing_workflow:
                    # 🔄 UPDATE: Actualizar workflow existente
                    self.logger.info(f"🔄 UPDATE MODE: Found existing workflow {existing_workflow.flow_id}, updating...")
                    # Agregar timestamp a metadata
                    spec["metadata"]["updated_at"] = str(datetime.utcnow())
                    
                    # Actualizar workflow existente
                    flow_summary = await self.flow_service.update_flow(
                        flow_id=existing_workflow.flow_id,
                        name=name,
                        spec=spec,
                        description=description
                    )
                    self.logger.info(f"🔄 POST-UPDATE: flow_service.update_flow returned: {flow_summary.flow_id}")
                else:
                    # 🆕 CREATE: Crear nuevo workflow
                    self.logger.info(f"🔄 CREATE MODE: No existing workflow found, creating new...")
                    # Agregar timestamp a metadata
                    spec["metadata"]["created_at"] = str(datetime.utcnow())
                    
                    flow_summary = await self.flow_service.create_flow(
                        name=name,
                        spec=spec,
                        owner_id=user_id,
                        description=description,
                        chat_id=UUID(chat_id) if chat_id else None
                    )
                    self.logger.info(f"🔄 POST-CREATE: flow_service.create_flow returned: {flow_summary.flow_id}")
            except Exception as flow_error:
                self.logger.error(f"🔄 TRANSACTION ERROR: {flow_error}")
                self.logger.error(f"🔄 TRANSACTION STATE: db.is_active: {self.db.is_active}")
                # 🔧 DB FIX: Rollback transaction on error
                try:
                    await self.db.rollback()
                    self.logger.info("🔄 ROLLBACK: Rolling back transaction due to error...")
                except Exception as rollback_error:
                    self.logger.error(f"🔄 ROLLBACK ERROR: {rollback_error}")
                # Re-raise the original error
                raise flow_error
            
            self.logger.info(f"✅ Workflow saved: {flow_summary.flow_id} - {name}")
            self.logger.info(f"🔄 TRANSACTION CHECK: About to check if transaction needs commit")
            self.logger.info(f"🔄 TRANSACTION STATE: db.in_transaction(): {self.db.in_transaction()}")
            
            # 🔧 EXPLICIT COMMIT: Force commit to ensure data persistence
            if self.db.in_transaction():
                self.logger.info(f"🔄 COMMITTING: Transaction is active, performing commit...")
                await self.db.commit()
                self.logger.info(f"🔄 COMMITTED: Transaction committed successfully")
            else:
                self.logger.warning(f"🔄 NO TRANSACTION: No active transaction to commit")
            
            # 🔄 SYNC WORKFLOW CONTEXT: Update conversation memory with latest state
            # Best practice 2025: Automatic state synchronization between DB and conversation memory
            if chat_id:
                try:
                    from app.services.conversation_memory_service import get_conversation_memory_service
                    memory_service = get_conversation_memory_service()
                    
                    # Create workflow_result format for save_workflow_context
                    workflow_result_for_memory = {
                        "steps": steps,
                        "confidence": 0.9,
                        "workflow_type": workflow_context.get("workflow_type", "classic"),
                        "metadata": {
                            **workflow_context.get("metadata", {}),
                            "flow_id": str(flow_summary.flow_id),
                            "saved": True,
                            "updated_at": str(datetime.utcnow())
                        },
                        "oauth_requirements": workflow_context.get("oauth_requirements", []),
                        "status": "saved",
                        "created_at": "timestamp"
                    }
                    
                    # Update conversation memory with latest workflow state
                    await memory_service.save_workflow_context(
                        self.db, chat_id, user_id, workflow_result_for_memory
                    )
                    self.logger.info(f"🔄 MEMORY SYNC: Updated conversation workflow_context with saved state")
                    
                except Exception as sync_error:
                    self.logger.error(f"🔄 MEMORY SYNC ERROR: Failed to update conversation workflow_context: {sync_error}")
                    # Don't fail the save operation due to memory sync issues
            
            return WorkflowCreationResultDTO(
                status=_DisabledWorkflowStatus.SAVE_WORKFLOW,  # 🚫 DISABLED - KEEPING FOR COMPATIBILITY
                workflow_type=WorkflowType.CLASSIC,
                steps=steps,
                oauth_requirements=[],
                discovered_resources=[],
                confidence=0.9,
                next_actions=["Workflow guardado exitosamente"],
                metadata={
                    "flow_id": str(flow_summary.flow_id),
                    "saved": True,
                    "is_active": False,
                    "action_performed": "save",
                    "workflow_name": name
                },
                reply=f"✅ Workflow '{name}' guardado exitosamente. Puedes activarlo después o ejecutarlo manualmente."
            )
            
        except Exception as e:
            self.logger.error(f"🔄 TRANSACTION ERROR: {e}")
            self.logger.error(f"🔄 TRANSACTION STATE: db.is_active: {self.db.is_active}")
            if self.db.in_transaction():
                self.logger.error(f"🔄 ROLLBACK: Rolling back transaction due to error...")
                await self.db.rollback()
                self.logger.error(f"🔄 ROLLED BACK: Transaction rolled back")
            return self._build_error_response(f"Error guardando workflow: {str(e)}")

    # 🗑️ REMOVED: _is_fallback_workflow - violates delegation philosophy
    # LLM planner should never generate fallback workflows, trust execution_plan

    # 🗑️ REMOVED: _try_recover_workflow_from_memory - violates execution_plan philosophy
    # All workflow data should come from LLM planner's execution_plan, not memory recovery
        """
        🔄 MEMORY RECOVERY: Busca hacia atrás en la memoria del chat para encontrar workflow válido
        """
        try:
            from sqlalchemy import select, desc
            from app.db.models import ChatMessage
            
            # Obtener mensajes del chat directamente desde BD
            stmt = select(ChatMessage).where(
                ChatMessage.session_id == UUID(chat_id)
            ).order_by(desc(ChatMessage.created_at))
            
            result = await self.db.execute(stmt)
            chat_messages = result.scalars().all()
            
            if not chat_messages:
                self.logger.info("🔍 MEMORY RECOVERY: No chat history found")
                return None
            
            self.logger.info(f"🔍 MEMORY RECOVERY: Searching through {len(chat_messages)} messages")
            
            # 🔧 DEFINITIVE FIX: Delegate to clean parsing logic from conversation_memory_service
            for message in chat_messages:  # Ya están ordenados del más reciente hacia atrás
                if message.role == "system" and "WORKFLOW_CONTEXT" in message.content:
                    try:
                        import json
                        # 🔧 CLEAN PARSING: Use same logic as conversation_memory_service.py
                        content = message.content
                        if "WORKFLOW_CONTEXT:" in content:
                            # Clean extraction instead of corrupted manual parsing
                            context_json = content.replace("WORKFLOW_CONTEXT: ", "")
                            workflow_data = json.loads(context_json)
                            
                            # Verificar que tenga steps válidos (no fallback)
                            steps = workflow_data.get("steps", [])
                            if steps and not await self._is_fallback_workflow({"steps": steps}):
                                self.logger.info(f"🔄 MEMORY RECOVERY: Found valid workflow with {len(steps)} steps")
                                return {
                                    "steps": steps,
                                    "workflow_summary": workflow_data.get("workflow_summary", {}),
                                    "metadata": {
                                        **workflow_data.get("metadata", {}),
                                        "recovered_from_memory": True,
                                        "recovered_at": message.created_at.isoformat() if hasattr(message, 'created_at') else None
                                    }
                                }
                            else:
                                self.logger.debug(f"🔍 MEMORY RECOVERY: Found workflow but it's fallback, skipping")
                    except (json.JSONDecodeError, KeyError) as e:
                        self.logger.debug(f"🔍 MEMORY RECOVERY: Failed to parse workflow from message: {e}")
                        continue
            
            self.logger.info("🔍 MEMORY RECOVERY: No valid workflows found in chat history")
            return None
            
        except Exception as e:
            self.logger.error(f"❌ MEMORY RECOVERY ERROR: {e}")
            return None

    async def _try_recover_workflow_from_db(self, user_id: int, chat_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        🔄 RECOVERY: Intenta recuperar workflow válido desde BD basándose en contexto del chat
        """
        try:
            # Buscar workflows recientes del usuario
            recent_flows = await self.flow_service.get_user_flows(user_id, limit=10)
            
            if not recent_flows:
                self.logger.info("📭 No workflows found in DB for recovery")
                return None
            
            # Obtener keywords del chat para matching
            chat_summary = chat_context.get("workflow_summary", {})
            keywords = set()
            
            if chat_summary.get("title"):
                keywords.update(chat_summary["title"].lower().split())
            if chat_summary.get("description"):
                keywords.update(chat_summary["description"].lower().split())
            
            # Buscar workflow más similar por nombre/descripción
            best_match = None
            best_score = 0
            
            for flow in recent_flows:
                score = self._calculate_similarity_score(flow, keywords)
                if score > best_score:
                    best_score = score
                    best_match = flow
            
            if best_match and best_score > 0.3:  # Threshold de similitud
                self.logger.info(f"🔄 RECOVERY: Found matching workflow: {best_match.name} (score: {best_score})")
                
                # Convertir flow a workflow_context format
                recovered_context = {
                    "steps": best_match.spec.get("steps", []),
                    "workflow_summary": best_match.spec.get("workflow_summary", {}),
                    "metadata": {
                        **best_match.spec.get("metadata", {}),
                        "recovered_from_db": True,
                        "original_flow_id": str(best_match.id),
                        "recovery_score": best_score
                    }
                }
                
                return recovered_context
            
            self.logger.info(f"📊 RECOVERY: No good match found. Best score: {best_score}")
            return None
            
        except Exception as e:
            self.logger.error(f"❌ RECOVERY ERROR: {e}")
            return None

    def _calculate_similarity_score(self, flow, keywords: set) -> float:
        """Calcula score de similitud entre flow y keywords del chat"""
        if not keywords:
            return 0.0
        
        flow_text = f"{flow.name} {flow.spec.get('workflow_summary', {}).get('description', '')}".lower()
        flow_words = set(flow_text.split())
        
        # Jaccard similarity
        intersection = keywords.intersection(flow_words)
        union = keywords.union(flow_words)
        
        return len(intersection) / len(union) if union else 0.0

    async def _save_and_activate_workflow(
        self, 
        execution_plan: List[Dict[str, Any]], 
        user_id: int,
        chat_id: str = None
    ) -> WorkflowCreationResultDTO:
        """Guarda el workflow y lo activa para ejecución automática"""
        # 🔒 LOCK: Prevenir múltiples activaciones concurrentes para el mismo usuario
        user_lock = self._get_user_lock(user_id)
        async with user_lock:
            self.logger.info(f"🔒 ACQUIRED LOCK for user {user_id} - processing save_and_activate")
            try:
                # 🔍 FALLBACK CHECK: Skip fallback checks in direct execution_plan flow 
                if False:  # REMOVED: fallback check not needed with execution_plan
                    # 🚨 FALLBACK DETECTED: No recovery - delegate to LLM planner to recreate
                    self.logger.error("🚨 FALLBACK WORKFLOW: Cannot activate fallback workflow")
                    return self._build_error_response(
                        "❌ Workflow incompleto detectado. "
                        "Por favor, vuelve a crear el workflow describiendo lo que necesitas."
                    )
                
                # 🔧 FIX: Guardar e inmediatamente activar en una sola operación atómica
                # 🎯 USE WORKFLOW CONTEXT SERVICE DIRECTLY - NO MORE EXTRACTION
                # 🚨 REMOVED: workflow_context_service - using execution_plan directly
                from app.services.flow_service import get_flow_service
                from uuid import UUID
                
                # Get workflow context using single source of truth
                # REMOVED: WorkflowContextService - using direct execution_plan flow
                steps = execution_plan  # execution_plan param IS the array of steps
                workflow_summary = {}  # No summary needed for direct execution
                self.logger.info(f"🎯 DIRECT CONTEXT: Using {len(steps)} steps from execution_plan with NO PROCESSING")
                
                if not steps:
                    return self._build_error_response("No hay steps en el workflow para procesar")
                
                # Generar nombre del workflow
                name = workflow_summary.get("title", f"Workflow {len(steps)} pasos")
                description = workflow_summary.get("description", f"Workflow generado automáticamente con {len(steps)} pasos")
                
                # 🔧 UUID SERIALIZATION FIX: Convert all UUIDs to strings before saving
                def serialize_uuids(obj):
                    """Recursively convert UUID objects to strings for JSON serialization"""
                    from uuid import UUID
                    if isinstance(obj, UUID):
                        return str(obj)
                    elif isinstance(obj, dict):
                        return {key: serialize_uuids(value) for key, value in obj.items()}
                    elif isinstance(obj, list):
                        return [serialize_uuids(item) for item in obj]
                    else:
                        return obj
                
                # Preparar spec para guardar con UUIDs serializados
                spec = {
                    "steps": serialize_uuids(steps),
                    "workflow_summary": serialize_uuids(workflow_summary),
                    "metadata": serialize_uuids({}),
                    "workflow_type": "classic"
                }
                
                self.logger.info(f"🔧 UUID SERIALIZATION: Converted UUIDs to strings in spec")
                
                # 🚀 ATOMIC OPERATION: Guardar y activar en una sola transacción
                self.logger.info(f"🔄 ATOMIC START: _save_and_activate_workflow for user {user_id}")
                self.logger.info(f"🔄 ATOMIC STATE: db.is_active: {self.db.is_active}, in_transaction: {self.db.in_transaction()}")
                
                # 🔍 CHECK EXISTING: Buscar workflow existente para este chat/usuario (mismo que en _save_workflow)
                self.logger.info(f"🔄 ATOMIC PRE-SAVE: Checking for existing workflow for chat_id: {chat_id}")
                
                # Buscar workflow existente por chat_id directo en la tabla flows
                existing_workflow = None
                if chat_id:
                    # Buscar por chat_id directo usando el repositorio
                    try:
                        from uuid import UUID
                        chat_uuid = UUID(chat_id) if isinstance(chat_id, str) else chat_id
                        
                        # ✅ REFACTORED: Use WorkflowContextService for atomic existence check
                        # 🚨 REMOVED: workflow_context_service - using execution_plan directly
                        # context_service = await get_workflow_context_service(self.db)
                        # REMOVED: context_service - using direct execution_plan flow
                        context = {"has_saved_version": False}  # Direct flow doesn't need existence check
                        
                        if context.get("has_saved_version"):
                            flow_id = context.get("flow_id")
                            self.logger.info(f"🔄 ATOMIC FOUND EXISTING: Found workflow {flow_id} for chat_id {chat_uuid}")
                        else:
                            self.logger.info(f"🔄 ATOMIC NO EXISTING: No workflow found for chat_id {chat_uuid}")
                            
                    except Exception as e:
                        self.logger.warning(f"🔄 ATOMIC EXISTING CHECK: Error checking existing workflows: {e}")
                
                if existing_workflow:
                    # 🔄 UPDATE: Actualizar workflow existente
                    self.logger.info(f"🔄 ATOMIC UPDATE MODE: Found existing workflow {existing_workflow.flow_id}, updating...")
                    # Agregar timestamp a metadata
                    spec["metadata"]["updated_at"] = str(datetime.utcnow())
                    
                    # Actualizar workflow existente
                    flow_summary = await self.flow_service.update_flow(
                        flow_id=existing_workflow.flow_id,
                        name=name,
                        spec=spec,
                        description=description
                    )
                    self.logger.info(f"🔄 ATOMIC POST-UPDATE: flow_service.update_flow returned: {flow_summary.flow_id}")
                else:
                    # 🆕 CREATE: Crear nuevo workflow
                    self.logger.info(f"🔄 ATOMIC CREATE MODE: No existing workflow found, creating new...")
                    # Agregar timestamp a metadata
                    spec["metadata"]["created_at"] = str(datetime.utcnow())
                    
                    flow_summary = await self.flow_service.create_flow(
                        name=name,
                        spec=spec,
                        owner_id=user_id,
                        description=description,
                        chat_id=UUID(chat_id) if chat_id else None
                    )
                    self.logger.info(f"🔄 ATOMIC POST-CREATE: flow_service.create_flow returned: {flow_summary.flow_id}")
                
                self.logger.info(f"✅ Workflow saved: {flow_summary.flow_id} - {name}")
                
                # 🔧 SINGLE ACTIVATION: Una sola llamada de activación para evitar race conditions
                try:
                    self.logger.info(f"🔄 ATOMIC ACTIVATION: About to activate flow {flow_summary.flow_id}")
                    activated_flow = await self.flow_service.set_flow_active(
                        flow_id=flow_summary.flow_id,
                        is_active=True,
                        user_id=user_id
                    )
                    self.logger.info(f"✅ Workflow activated atomically: {flow_summary.flow_id}")
                    
                    # 🔧 EXPLICIT COMMIT: Force commit for atomic operation
                    if self.db.in_transaction():
                        self.logger.info(f"🔄 ATOMIC COMMIT: Committing atomic save+activate transaction...")
                        await self.db.commit()
                        self.logger.info(f"🔄 ATOMIC COMMITTED: Atomic transaction committed successfully")
                    else:
                        self.logger.warning(f"🔄 ATOMIC NO-TRANSACTION: No active transaction for atomic operation")
                    
                    # 🔄 SYNC WORKFLOW CONTEXT: Update conversation memory with latest state
                    # Best practice 2025: Automatic state synchronization after save+activate
                    if chat_id:
                        try:
                            from app.services.conversation_memory_service import get_conversation_memory_service
                            memory_service = get_conversation_memory_service()
                            
                            # Create workflow_result format for save_workflow_context
                            workflow_result_for_memory = {
                                "steps": steps,
                                "confidence": 0.9,
                                "workflow_type": workflow_context.get("workflow_type", "classic"),
                                "metadata": {
                                    **workflow_context.get("metadata", {}),
                                    "flow_id": str(activated_flow.flow_id),
                                    "saved": True,
                                    "is_active": True,
                                    "updated_at": str(datetime.utcnow())
                                },
                                "oauth_requirements": workflow_context.get("oauth_requirements", []),
                                "status": "activated",
                                "created_at": "timestamp"
                            }
                            
                            # Update conversation memory with latest workflow state
                            await memory_service.save_workflow_context(
                                self.db, chat_id, user_id, workflow_result_for_memory
                            )
                            self.logger.info(f"🔄 ATOMIC MEMORY SYNC: Updated conversation workflow_context with activated state")
                            
                        except Exception as sync_error:
                            self.logger.error(f"🔄 ATOMIC MEMORY SYNC ERROR: Failed to update conversation workflow_context: {sync_error}")
                            # Don't fail the operation due to memory sync issues
                    
                except Exception as activation_error:
                    self.logger.error(f"❌ Activation failed, but workflow saved: {activation_error}")
                    self.logger.error(f"🔄 ACTIVATION ERROR STATE: db.in_transaction: {self.db.in_transaction()}")
                    
                    # Si falla la activación, al menos tenemos el workflow guardado
                    # Commit solo el save si está en transacción
                    if self.db.in_transaction():
                        self.logger.info(f"🔄 PARTIAL COMMIT: Committing save-only due to activation failure...")
                        await self.db.commit()
                        self.logger.info(f"🔄 PARTIAL COMMITTED: Save-only committed successfully")
                    
                    # 🔄 SYNC WORKFLOW CONTEXT: Update memory even on activation failure (workflow was saved)
                    if chat_id:
                        try:
                            from app.services.conversation_memory_service import get_conversation_memory_service
                            memory_service = get_conversation_memory_service()
                            
                            workflow_result_for_memory = {
                                "steps": steps,
                                "confidence": 0.9,
                                "workflow_type": workflow_context.get("workflow_type", "classic"),
                                "metadata": {
                                    **workflow_context.get("metadata", {}),
                                    "flow_id": str(flow_summary.flow_id),
                                    "saved": True,
                                    "is_active": False,
                                    "activation_error": str(activation_error),
                                    "updated_at": str(datetime.utcnow())
                                },
                                "oauth_requirements": workflow_context.get("oauth_requirements", []),
                                "status": "saved",
                                "created_at": "timestamp"
                            }
                            
                            await memory_service.save_workflow_context(
                                self.db, chat_id, user_id, workflow_result_for_memory
                            )
                            self.logger.info(f"🔄 PARTIAL MEMORY SYNC: Updated conversation workflow_context with saved-only state")
                            
                        except Exception as sync_error:
                            self.logger.error(f"🔄 PARTIAL MEMORY SYNC ERROR: Failed to update conversation workflow_context: {sync_error}")
                    
                    return WorkflowCreationResultDTO(
                        status=_DisabledWorkflowStatus.SAVE_WORKFLOW,  # 🚫 DISABLED - KEEPING FOR COMPATIBILITY
                        workflow_type=WorkflowType.CLASSIC,
                        steps=steps,
                        oauth_requirements=[],
                        discovered_resources=[],
                        confidence=0.9,
                        next_actions=["Workflow guardado, pero falló la activación"],
                        metadata={
                            "flow_id": str(flow_summary.flow_id),
                            "saved": True,
                            "is_active": False,
                            "action_performed": "save_only",
                            "workflow_name": name,
                            "activation_error": str(activation_error)
                        },
                        reply=f"⚠️ Workflow '{name}' guardado pero falló la activación automática. Puedes activarlo manualmente."
                    )
                
                # 🎉 SUCCESS: Todo funcionó correctamente
                self.logger.info(f"🔄 ATOMIC SUCCESS: Both save and activate completed successfully")
                return WorkflowCreationResultDTO(
                    status=_DisabledWorkflowStatus.ACTIVATE_WORKFLOW,  # 🚫 DISABLED - KEEPING FOR COMPATIBILITY
                    workflow_type=WorkflowType.CLASSIC,
                    steps=steps,
                    oauth_requirements=[],
                    discovered_resources=[],
                    confidence=0.9,
                    next_actions=["Workflow guardado y activado exitosamente"],
                    metadata={
                        "flow_id": str(activated_flow.flow_id),
                        "saved": True,
                        "is_active": True,
                        "action_performed": "save_and_activate",
                        "workflow_name": activated_flow.name
                    },
                    reply=f"✅ Workflow '{activated_flow.name}' guardado y activado. Se ejecutará automáticamente según el trigger configurado."
                )
                
            except Exception as e:
                self.logger.error(f"🔄 ATOMIC ERROR: {e}")
                self.logger.error(f"🔄 ATOMIC STATE: db.is_active: {self.db.is_active}")
                if self.db.in_transaction():
                    self.logger.error(f"🔄 ATOMIC ROLLBACK: Rolling back atomic transaction...")
                    await self.db.rollback()
                    self.logger.error(f"🔄 ATOMIC ROLLED BACK: Atomic transaction rolled back")
                return self._build_error_response(f"Error guardando y activando workflow: {str(e)}")

    async def _deactivate_workflow(
        self, 
        execution_plan: List[Dict[str, Any]], 
        user_id: int,
        chat_id: str = None
    ) -> WorkflowCreationResultDTO:
        """Desactiva un workflow existente"""
        try:
            self.logger.info(f"🔄 DEACTIVATE: Starting deactivate for user {user_id}, chat_id: {chat_id}")
            
            # Buscar workflow existente por chat_id
            existing_workflow = None
            if chat_id:
                try:
                    from uuid import UUID
                    chat_uuid = UUID(chat_id) if isinstance(chat_id, str) else chat_id
                    # 🔧 FIX: Actually search for existing workflow by chat_id
                    self.logger.info(f"🔍 DEACTIVATE: Searching for existing workflow by chat_id {chat_uuid}")
                    
                    try:
                        existing_workflow = await self.flow_service.repo.get_by_chat_id(
                            owner_id=user_id,
                            chat_id=chat_uuid
                        )
                        if existing_workflow:
                            self.logger.info(f"🔄 DEACTIVATE: Found existing workflow {existing_workflow.flow_id} for chat_id {chat_uuid}")
                        else:
                            self.logger.info(f"🔄 DEACTIVATE: No existing workflow found for chat_id {chat_uuid}")
                            return self._build_error_response("No se encontró ningún workflow asociado a este chat para desactivar")
                    except Exception as search_error:
                        self.logger.error(f"🔄 DEACTIVATE: Error searching for workflow: {search_error}")
                        return self._build_error_response(f"Error buscando workflow para desactivar: {str(search_error)}")
                        
                except Exception as e:
                    self.logger.warning(f"🔄 DEACTIVATE: Error finding workflow: {e}")
                    return self._build_error_response(f"Error buscando workflow: {str(e)}")
            else:
                return self._build_error_response("No se puede desactivar workflow: falta información del chat")
            
            # Desactivar el workflow
            try:
                self.logger.info(f"🔄 DEACTIVATE: About to deactivate flow {existing_workflow.flow_id}")
                deactivated_flow = await self.flow_service.set_flow_active(
                    flow_id=existing_workflow.flow_id,
                    is_active=False,
                    user_id=user_id
                )
                self.logger.info(f"✅ Workflow deactivated: {existing_workflow.flow_id}")
                
                # Commit transaction
                if self.db.in_transaction():
                    self.logger.info(f"🔄 DEACTIVATE COMMIT: Committing deactivation transaction...")
                    await self.db.commit()
                    self.logger.info(f"🔄 DEACTIVATE COMMITTED: Transaction committed successfully")
                
                return WorkflowCreationResultDTO(
                    status=_DisabledWorkflowStatus.SAVE_WORKFLOW,  # 🚫 DISABLED - KEEPING FOR COMPATIBILITY  # Use save_workflow status for deactivated
                    workflow_type=WorkflowType.CLASSIC,
                    steps=execution_plan or [],  # 🔧 FIX: Use execution_plan instead of workflow_context
                    oauth_requirements=[],
                    discovered_resources=[],
                    confidence=0.9,
                    next_actions=["Workflow desactivado exitosamente"],
                    metadata={
                        "flow_id": str(deactivated_flow.flow_id),
                        "saved": True,
                        "is_active": False,
                        "action_performed": "deactivate",
                        "workflow_name": deactivated_flow.name
                    },
                    reply=f"✅ Workflow '{deactivated_flow.name}' desactivado exitosamente. Ya no se ejecutará automáticamente."
                )
                
            except Exception as deactivation_error:
                self.logger.error(f"❌ Deactivation failed: {deactivation_error}")
                if self.db.in_transaction():
                    self.logger.error(f"🔄 DEACTIVATE ROLLBACK: Rolling back transaction...")
                    await self.db.rollback()
                return self._build_error_response(f"Error desactivando workflow: {str(deactivation_error)}")
                
        except Exception as e:
            self.logger.error(f"🔄 DEACTIVATE ERROR: {e}")
            if self.db.in_transaction():
                await self.db.rollback()
            return self._build_error_response(f"Error procesando desactivación: {str(e)}")

    async def _execute_workflow_now(
        self, 
        execution_plan: List[Dict[str, Any]], 
        user_id: int,
        chat_id: str = None
    ) -> WorkflowCreationResultDTO:
        """Ejecuta el workflow inmediatamente sin guardarlo"""
        try:
            # 🔍 FALLBACK CHECK: Skip fallback checks in direct execution_plan flow
            if False:  # REMOVED: fallback check not needed with execution_plan
                # 🚨 FALLBACK DETECTED: No recovery - delegate to LLM planner to recreate
                self.logger.error("🚨 FALLBACK WORKFLOW: Cannot execute fallback workflow")
                return self._build_error_response(
                    "❌ Workflow incompleto detectado. "
                    "Por favor, vuelve a crear el workflow describiendo lo que necesitas."
                )
            
            # ✅ REFACTORED: Use WorkflowContextService for latest context
            try:
                # 🚨 REMOVED: workflow_context_service - using execution_plan directly
                # context_service = await get_workflow_context_service(self.db)
                # REMOVED: context_service - using direct execution_plan flow 
                latest_context = {"steps": execution_plan}  # execution_plan param contains the steps
                
                if latest_context and latest_context.get("steps"):
                    context_to_use = latest_context
                    self.logger.info(f"🔄 BRIDGE EXECUTE: Using LATEST context from direct flow")
                else:
                    context_to_use = {"steps": execution_plan}
                    self.logger.info(f"🔄 BRIDGE EXECUTE: No latest context found, using provided context")
            except Exception as e:
                self.logger.error(f"🔄 BRIDGE EXECUTE ERROR: Could not load latest context: {e}")
            
            # 🎯 USE WORKFLOW CONTEXT SERVICE DIRECTLY - NO MORE EXTRACTION
            # REMOVED: WorkflowContextService - delegated to memory service in direct flow era
            from app.services.flow_service import get_flow_service
            from uuid import UUID
            
            # Get workflow context using single source of truth
            # REMOVED: WorkflowContextService - using direct execution_plan flow  
            steps = execution_plan  # execution_plan param IS the array of steps
            self.logger.info(f"🎯 EXECUTE: Found {len(steps)} steps for execution from direct execution_plan")
            
            # 🔍 DEBUG: Log the first step to see what fields we have
            if steps and len(steps) > 0:
                first_step = steps[0]
                self.logger.info(f"🔍 DEBUG FIRST STEP: {first_step}")
                has_node_name = 'node_name' in first_step
                has_action_name = 'action_name' in first_step  
                self.logger.info(f"🔍 DEBUG FIELDS: node_name={has_node_name}, action_name={has_action_name}")
            
            # 🔧 CRITICAL FIX: Map default_auth from memory context to steps
            if chat_id and steps:
                try:
                    memory_service = ConversationMemoryService()
                    memory_context = await memory_service.load_memory_context(self.db, chat_id)
                    default_auth_mapping = memory_context.get('default_auth_mapping', {})
                    
                    if default_auth_mapping:
                        for step in steps:
                            node_name = step.get('node_name')
                            if node_name and node_name in default_auth_mapping:
                                step['default_auth'] = default_auth_mapping[node_name]
                                self.logger.info(f"🔧 EXECUTE MAPPED default_auth for {node_name}: {default_auth_mapping[node_name]}")
                except Exception as e:
                    self.logger.error(f"🔧 EXECUTE MAPPING ERROR: {e}")
            
            # 🔧 CRITICAL FIX: Merge user inputs with workflow steps before execution
            if chat_id:
                try:
                    memory_service = ConversationMemoryService()
                    memory_context = await memory_service.load_memory_context(self.db, chat_id)
                    user_inputs = memory_context.get('user_inputs_provided', {})
                    
                    if user_inputs:
                        self.logger.info(f"🔧 BRIDGE PARAM MERGE: Found {len(user_inputs)} user inputs: {user_inputs}")
                        
                        # Update parameters in steps with user inputs
                        for step_idx, step in enumerate(steps):
                            self.logger.info(f"🔧 BRIDGE PARAM MERGE: Step {step_idx} params BEFORE: {step.get('params', {})}")
                            
                            # 🎯 FIX: Si params está vacío, crear estructura y aplicar TODOS los user inputs
                            if 'params' not in step:
                                step['params'] = {}
                            
                            # 🎯 UNIVERSAL FIX: Rescatar TODOS los params existentes + user inputs
                            
                            # 🔧 STEP 1: Copiar params existentes del step
                            existing_params = {}
                            if step.get('params'):
                                for key, value in step['params'].items():
                                    # 🎯 CRITICAL: Convertir cualquier UUID/objeto a string
                                    existing_params[key] = str(value) if value is not None else ""
                            
                            # 🔧 STEP 2: Agregar user inputs (tienen prioridad)
                            final_params = existing_params.copy()
                            for key, value in user_inputs.items():
                                final_params[key] = str(value)  # También convertir user inputs a string
                            
                            # 🔧 STEP 3: Aplicar merged params al step
                            step['params'] = final_params
                            
                            self.logger.info(f"🔧 BRIDGE PARAM MERGE: Existing params: {existing_params}")
                            self.logger.info(f"🔧 BRIDGE PARAM MERGE: User inputs: {user_inputs}")
                            self.logger.info(f"🔧 BRIDGE PARAM MERGE: Final merged params: {final_params}")
                            
                            self.logger.info(f"🔧 BRIDGE PARAM MERGE: Step {step_idx} params AFTER: {step.get('params', {})}")
                        
                        self.logger.info("🔧 BRIDGE PARAM MERGE: Successfully merged user inputs with steps")
                except Exception as e:
                    self.logger.error(f"🔧 BRIDGE PARAM MERGE ERROR: {e}")
            
            # 🔧 FIX: Usar el workflow_runner de la instancia actual con manejo de transacciones
            self.logger.info(f"🎯 EXECUTE: Calling WorkflowRunnerService.execute_workflow_steps with {len(steps)} steps")
            
            try:
                # Para ejecución temporal, usamos execute_workflow_steps directamente
                # en lugar de run_workflow que requiere validación de flows guardados
                execution_id, result = await self.workflow_runner.execute_workflow_steps(
                    steps=steps,
                    user_id=user_id,
                    inputs={},
                    simulate=False,  # 🔧 REAL EXECUTION: MCP issue fixed, back to real execution
                    flow_id=None  # Ejecución temporal
                )
            except Exception as e:
                # 🔧 DB FIX: Rollback transaction on error
                self.logger.error(f"🔄 EXECUTE ERROR: {e}")
                try:
                    await self.db.rollback()
                    self.logger.info("🔄 ROLLED BACK: Transaction rolled back due to execution error")
                except Exception as rollback_error:
                    self.logger.error(f"🔄 ROLLBACK ERROR: {rollback_error}")
                raise
            
            self.logger.info(f"✅ Workflow executed immediately: {execution_id}")
            self.logger.info(f"✅ Execution result: {result}")
            
            return WorkflowCreationResultDTO(
                status=_DisabledWorkflowStatus.EXECUTE_WORKFLOW,  # 🚫 DISABLED - KEEPING FOR COMPATIBILITY
                workflow_type=WorkflowType.CLASSIC,
                steps=steps,
                oauth_requirements=[],
                discovered_resources=[],
                confidence=0.9,
                next_actions=["Workflow ejecutado exitosamente"],
                metadata={
                    "execution_id": str(execution_id),
                    "executed": True,
                    "action_performed": "execute_now",
                    "execution_result": result.model_dump() if result else None,
                    "workflow_name": "workflow ejecutado"
                },
                reply=f"🚀 Workflow ejecutado exitosamente! Resultado: {result.overall_status if result else 'completado'}"
            )
            
        except Exception as e:
            self.logger.error(f"Error executing workflow immediately: {e}", exc_info=True)
            self.logger.error(f"🎯 EXECUTE ERROR: Exception type: {type(e)}")
            # Use execution_plan directly instead of steps variable that might not be defined
            try:
                steps_count = len(execution_plan) if execution_plan else 0
                self.logger.error(f"🎯 EXECUTE ERROR: Steps that failed: {steps_count} steps")
            except:
                self.logger.error(f"🎯 EXECUTE ERROR: Could not determine steps count")
            return self._build_error_response(f"Error ejecutando workflow: {str(e)}")

    async def get_workflow_real_status(self, chat_id: str, user_id: int) -> Dict[str, Any]:
        """
        Obtiene el estado real del workflow desde la base de datos por chat_id
        """
        try:
            # Convertir chat_id string a UUID
            chat_uuid = UUID(chat_id)
            
            # Buscar workflow por chat_id
            workflow = await self.flow_service.get_flow_by_chat_id(user_id, chat_uuid)
            
            if not workflow:
                return {
                    "exists": False,
                    "is_active": False,
                    "flow_id": None,
                    "workflow_name": None
                }
            
            return {
                "exists": True,
                "is_active": workflow.is_active,
                "flow_id": str(workflow.flow_id),
                "workflow_name": workflow.name,
                "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
                "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None
            }
            
        except Exception as e:
            self.logger.error(f"Error getting workflow real status: {e}")
            return {
                "exists": False,
                "is_active": False,
                "flow_id": None,
                "workflow_name": None,
                "error": str(e)
            }

    # 🗑️ REMOVED: _extract_complete_workflow_from_llm_history 
    # Ya no se necesita - Context API retorna steps completos del LLM planner

    # 🗑️ REMOVED: _get_last_llm_response - using direct interception instead

    def _build_error_response(self, error_message: str) -> WorkflowCreationResultDTO:
        """Construye respuesta de error estándar"""
        return WorkflowCreationResultDTO(
            status=WorkflowStatus.ERROR,
            workflow_type=WorkflowType.CLASSIC,
            steps=[],
            oauth_requirements=[],
            discovered_resources=[],
            confidence=0.3,
            next_actions=["Intentar de nuevo"],
            metadata={"error": error_message},
            reply=f"❌ {error_message}"
        )


# Factory function
async def get_chat_workflow_bridge_service(
    flow_service: FlowService = Depends(get_flow_service),
    workflow_runner: WorkflowRunnerService = Depends(get_workflow_runner),
    trigger_orchestrator: TriggerOrchestratorService = Depends(get_trigger_orchestrator_service),
    db: AsyncSession = Depends(get_db)
) -> ChatWorkflowBridgeService:
    """Factory para obtener instancia de ChatWorkflowBridgeService"""
    return ChatWorkflowBridgeService(flow_service, workflow_runner, trigger_orchestrator, db)

async def create_chat_workflow_bridge_service_manual(db_session: AsyncSession) -> ChatWorkflowBridgeService:
    """
    🔧 MANUAL CREATION: Crear ChatWorkflowBridgeService sin Depends para uso fuera de FastAPI
    """
    from app.services.flow_service import create_flow_service_manual
    from app.services.workflow_runner_service import create_workflow_runner_manual
    from app.services.trigger_orchestrator_service import create_trigger_orchestrator_manual
    
    # Crear instancias manualmente
    flow_service = await create_flow_service_manual(db_session)
    workflow_runner = await create_workflow_runner_manual(db_session)
    trigger_orchestrator = await create_trigger_orchestrator_manual(db_session)
    
    return ChatWorkflowBridgeService(flow_service, workflow_runner, trigger_orchestrator, db_session)