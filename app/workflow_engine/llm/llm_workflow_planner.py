"""
LLM Workflow Planner - Kyra planifica workflows con CAG completo
CENTRALIZADO: Combina lógica de NodeSelectionService + LLMWorkflowPlanner
Extrae la lógica LLM del workflow engine principal - sin scores artificiales
"""
import json
import logging
import hashlib
import asyncio
import uuid
from collections import Counter
from typing import List, Dict, Any, Optional, TypedDict, Union
from uuid import UUID
from redis.asyncio import Redis
from ..utils.workflow_logger import WorkflowLogger
from app.core.config import settings
from app.db.models import UsageMode
from app.exceptions.api_exceptions import WorkflowProcessingException
from app.exceptions.llm_exceptions import JSONParsingException, LLMConnectionException


# Constantes migradas de NodeSelectionService
# SearchService legacy constants removed - using CAG approach
RETRY_COUNT = 3
RETRY_DELAY = 1  # segundos

# Tipos específicos migrados
class ConnectorNode(TypedDict):
    node_id: str
    node_name: Optional[str]
    usage_mode: Optional[str]
    actions: List[Dict[str, Any]]

class LLMWorkflowPlanner:
    """
    UNIFIED: Kyra planifica workflows con contexto CAG completo
    Combina funcionalidades de NodeSelection + WorkflowPlanning
    - Busca conectores candidatos
    - Selecciona nodos apropiados  
    - Planifica workflow completo con triggers
    Sin scores artificiales - Kyra decide con metadata rico
    """
    
    def __init__(self, connector_client=None, redis_client=None, cache_ttl=None):
        self.logger = WorkflowLogger(__name__)
        
        # Dependencies for workflow planning
        self.connector_client = connector_client
        self.redis = redis_client
        self.cache_ttl = cache_ttl or getattr(settings, "NODES_CACHE_TTL", 300)
        
        # ✅ SINGLETON: No almacenar referencia - siempre usar get_llm_service()
        # Esto garantiza que SIEMPRE se use la misma instancia singleton
        self.logger.logger.info("✅ LLMWorkflowPlanner initialized to use LLM singleton")
        
        # PRESERVAR IDENTIDAD DE KYRA: guardar historia y contexto
        self.conversation_history = []
        self.current_plan = None
        self.workflow_context = {}
        # El system prompt ahora está directamente en _build_unified_prompt()
        self.base_system_prompt = None  # No longer needed
    
    # DEPRECATED: continue_after_oauth method removed
    # Unified workflow planning for all scenarios
    # ===============================
    # MÉTODOS MIGRADOS DE NodeSelectionService
    # ===============================
    
    def _make_cache_key(self, user_intent: str, history: List[Dict[str, Any]]) -> str:
        """Genera una clave única para el cache."""
        payload = json.dumps({"intent": user_intent, "history": history}, sort_keys=True, ensure_ascii=False, default=str)
        digest = hashlib.sha256(payload.encode()).hexdigest()
        return f"unified_planner:{digest}"

    def _create_node_dict(self, connector: Any) -> ConnectorNode:
        """
        Convierte un conector en un diccionario estandarizado.
        """
        actions = []
        for a in getattr(connector, "actions", []) or []:
            if isinstance(a, dict):
                if "is_trigger" not in a:
                    a = {**a, "is_trigger": False}
                actions.append(a)
            else:
                actions.append(
                    {
                        "action_id": getattr(a, "action_id", None),
                        "node_id": getattr(a, "node_id", None),
                        "name": getattr(a, "name", None),
                        "description": getattr(a, "description", None),
                        "is_trigger": getattr(a, "is_trigger", False),
                    }
                )

        return {
            "node_id": connector.node_id,
            "node_name": connector.name or getattr(connector, "node_name", None),
            "default_auth": getattr(connector, "default_auth", None),
            "usage_mode": getattr(connector, "usage_mode", UsageMode.step).value,
            "actions": actions,
        }

    async def find_candidate_connectors(
        self,
        user_intent: str,
    ) -> List[ConnectorNode]:
        """
        MIGRADO: Encuentra conectores candidatos basados en la intención del usuario.
        """
        if not user_intent or not user_intent.strip():
            self.logger.log_warning("Intención de usuario vacía o inválida")
            return []

        try:
            if not self.connector_client:
                raise WorkflowProcessingException("ConnectorClient no disponible")
                
            connectors = [
                c
                for c in await self.connector_client.fetch_connectors()
                if getattr(c, "usage_mode", UsageMode.step) not in (UsageMode.tool, UsageMode.function)
            ]

            # CAG approach: return all connectors with rich metadata for LLM selection
            # The LLM is intelligent enough to select relevant connectors from the full context
            return [self._create_node_dict(c) for c in connectors]
        except Exception as e:
            self.logger.log_error(e, "Error obteniendo conectores")
            raise WorkflowProcessingException(f"Error obteniendo conectores: {e}")
    
    # ===============================
    # MÉTODO PRINCIPAL UNIFICADO
    # ===============================
    
    async def unified_workflow_planning(
        self,
        user_message: str,
        history: List[Dict[str, Any]] = None,
        cag_context: List[Dict[str, Any]] = None,
        workflow_type: str = None,
        selected_services: List[str] = None,
        discovery_results: List[Dict[str, Any]] = None,
        previous_workflow: Dict[str, Any] = None,
        smart_forms_generated: List[Dict[str, Any]] = None,
        oauth_completed_services: List[str] = None,
        user_inputs_provided: Dict[str, Any] = None,
        smart_forms_enabled: bool = False,
        oauth_already_satisfied: bool = False  # ✅ NEW: Tell LLM OAuth is satisfied from previous sessions
    ) -> List[Dict[str, Any]]:
        """
        MÉTODO UNIFICADO LIMPIO: Planning directo sin intent analysis
        
        Args:
            user_message: Intención del usuario
            history: Historial de conversación (para cache)
            cag_context: CAG completo opcional (si no se provee, se buscan candidatos)
            workflow_type: Tipo de workflow (classic/agent)
            
        Returns:
            Plan de ejecución secuencial con parámetros
        """
        try:
            # 1. OBTENER NODOS CANDIDATOS
            if cag_context is not None and len(cag_context) > 0:
                # Usar CAG completo provisto
                self.logger.logger.info(f"🔥 LLM PLANNER: Using full CAG context with {len(cag_context)} nodes for Kyra")
                nodes_for_kyra = self._prepare_cag_context_for_llm(cag_context)
                self.logger.logger.info(f"🔥 LLM PLANNER: Prepared {len(nodes_for_kyra)} nodes for Kyra's decision")
            elif cag_context is not None and len(cag_context) == 0:
                # ✅ NUEVO: CAG on-demand - LLM decidirá si necesita nodos
                self.logger.logger.info("🔧 ON-DEMAND CAG: LLM will request nodes via get_available_nodes() if needed")
                nodes_for_kyra = []
                
                # 🎯 SMART FILTER BY SELECTED SERVICES if provided
                if selected_services:
                    original_count = len(nodes_for_kyra)
                    
                    # Incluir nodos seleccionados + nodos relacionados que podrían ser necesarios
                    filtered_nodes = []
                    selected_node_names = set()
                    
                    # Primero agregar nodos explícitamente seleccionados
                    for node in nodes_for_kyra:
                        if any(service_id in [node.get("node_id"), node.get("name"), node.get("provider")] 
                               for service_id in selected_services):
                            filtered_nodes.append(node)
                            selected_node_names.add(node.get("name", "").lower())
                    
                    
                    nodes_for_kyra = filtered_nodes
                    self.logger.logger.info(f"🎯 SMART FILTERED NODES: Reduced from {original_count} to {len(nodes_for_kyra)} based on selected_services: {selected_services}")
                    
                    # 🔍 DETAILED LOGGING: ¿Qué nodos específicos ve Kyra?
                    self.logger.logger.info("🔍 KYRA'S AVAILABLE NODES:")
                    for i, node in enumerate(nodes_for_kyra):
                        self.logger.logger.info(f"  [{i+1}] {node.get('name', 'Unknown')} (provider: {node.get('provider', 'unknown')}, type: {node.get('type', 'unknown')})")
                        actions = node.get('actions', [])
                        if actions:
                            self.logger.logger.info(f"      Actions: {[action.get('action_name', 'unknown') for action in actions[:3]]}")  # Solo primeras 3
            else:
                # Buscar candidatos usando lógica migrada de NodeSelectionService
                self.logger.logger.info(f"🔥 LLM PLANNER: Finding candidate connectors for: {user_message[:100]}...")
                # 🎯 FIX: En flujos de continuación, no buscar candidatos - usar workflow context
                if previous_workflow and previous_workflow.get("steps"):
                    self.logger.logger.info(f"🔄 CONTINUATION FLOW: Using previous workflow context, skipping candidate search")
                    nodes_for_kyra = []  # Empty - LLM will use previous_workflow context instead
                else:
                    self.logger.logger.info(f"🔥 LLM PLANNER: Finding candidate connectors for: {user_message[:100]}...")
                    candidates = await self.find_candidate_connectors(user_message)
                    nodes_for_kyra = [self._convert_candidate_to_cag_format(c) for c in candidates]
                    self.logger.logger.info(f"🔥 LLM PLANNER: Found {len(candidates)} candidates, converted to {len(nodes_for_kyra)} nodes for Kyra")
            
            # 2. CACHE CHECK
            cache_key = None
            if self.redis and history:
                cache_key = self._make_cache_key(user_message, history)
                try:
                    cached = await self.redis.get(cache_key)
                    if cached:
                        self.logger.logger.info(f"Unified planner cache HIT {cache_key}")
                        return json.loads(cached)
                except Exception as e:
                    self.logger.log_warning(f"Error leyendo cache Redis: {e}")

            # 3. PROMPT UNIFICADO (sin intent analysis)
            # Use provided workflow_type or default to "classic" as last resort
            effective_workflow_type = workflow_type if workflow_type is not None else "classic"
            prompt = self._build_unified_prompt(
                user_message, nodes_for_kyra, history, effective_workflow_type, 
                selected_services, discovery_results, previous_workflow,
                smart_forms_generated, oauth_completed_services, user_inputs_provided,
                smart_forms_enabled, oauth_already_satisfied
            )
            
            # 4. LLAMADA LLM CON REINTENTOS
            self.logger.logger.info(f"🧠 SENDING TO KYRA: {len(nodes_for_kyra)} node candidates for decision")
            self.logger.logger.info(f"🧠 Node candidates by provider: {dict(Counter(node.get('provider', 'unknown') for node in nodes_for_kyra))}")
            self.logger.logger.info(f"🧠 Node candidates by type: {dict(Counter(node.get('type', 'unknown') for node in nodes_for_kyra))}")
            
            # 🔍 DEBUG CRÍTICO: Mostrar los primeros 3 nodos completos
            self.logger.logger.info("🔍 FIRST 3 NODES BEING SENT TO LLM:")
            for i, node in enumerate(nodes_for_kyra[:3]):
                self.logger.logger.info(f"  Node {i+1}: {json.dumps(node, indent=2, default=str)}")
            
            self.logger.logger.info(f"✅ {len(nodes_for_kyra)} nodes being sent to LLM from CAG context")
            
            llm_response = await self._call_llm_with_retry(prompt)
            
            self.logger.logger.info(f"🧠 KYRA RESPONDED: Processing response type: {type(llm_response)}")
            
            # 🔍 DETAILED LOGGING: ¿Qué decidió Kyra específicamente?
            response_status = llm_response.get("status", "unknown") if isinstance(llm_response, dict) else "non-dict"
            self.logger.logger.info(f"🧠 KYRA'S DECISION STATUS: {response_status}")
            
            if isinstance(llm_response, dict):
                if "steps" in llm_response:
                    steps = llm_response.get("steps", [])
                    self.logger.logger.info(f"🧠 KYRA PLANNED {len(steps)} STEPS:")
                    for i, step in enumerate(steps):
                        self.logger.logger.info(f"  Step {i+1}: {step.get('node_name', 'unknown')} -> {step.get('action_name', 'unknown')}")
                
                if "service_groups" in llm_response:
                    groups = llm_response.get("service_groups", [])
                    self.logger.logger.info(f"🧠 KYRA REQUESTS CLARIFICATION: {len(groups)} service groups")
                    for group in groups:
                        self.logger.logger.info(f"  Category: {group.get('category', 'unknown')} - Options: {len(group.get('options', []))}")
            
            # 🔍 DETAILED LOGGING: Log the raw LLM response for debugging
            self.logger.logger.info(f"🔍 RAW LLM RESPONSE: {json.dumps(llm_response, indent=2, default=str)}")
            
            # 5. PROCESAR RESPUESTA COMPLETA (incluye metadata de Kyra)
            if isinstance(llm_response, dict):
                status = llm_response.get("status", "unknown")
                
                # 🔥 NEW: Handle clarification requests from Kyra
                if status == "clarification_needed" and "service_groups" in llm_response:
                    self.logger.logger.info("🧠 KYRA REQUESTS CLARIFICATION - returning for Smart Forms")
                    return {
                        "status": "clarification_needed",
                        "similar_services_found": llm_response.get("similar_services_found", True),
                        "service_groups": llm_response.get("service_groups", []),
                        "next_steps": llm_response.get("next_steps", ""),
                        "steps": None,  # No steps yet, waiting for clarification
                        "confidence": 0.5,  # Medium confidence while waiting
                        "workflow_type": effective_workflow_type,
                        "metadata": {}
                    }
                
                
                # 🔥 NEW: Handle workflow ready for user review
                elif status == "workflow_ready_for_review":
                    self.logger.logger.info("📋 KYRA PRESENTS WORKFLOW FOR REVIEW - returning for user feedback")
                    
                    # 🎯 DIRECT APPROACH: Use execution_plan directly as steps (with metadata enhancement)
                    execution_plan = llm_response.get("execution_plan", [])
                    if execution_plan:
                        self.logger.logger.info(f"🎯 DIRECT STEPS: Using execution_plan directly as steps ({len(execution_plan)} steps)")
                        
                        # 🚀 ENHANCE: Add missing metadata to execution_plan steps
                        steps = []
                        for i, exec_step in enumerate(execution_plan):
                            # Start with execution_plan step (already has params)
                            enhanced_step = exec_step.copy()
                            
                            # 🔧 ADD MISSING METADATA: Only what's needed for flows
                            if "id" not in enhanced_step:
                                enhanced_step["id"] = str(uuid.uuid4())
                            if "next" not in enhanced_step:
                                enhanced_step["next"] = None
                            if "retries" not in enhanced_step:
                                enhanced_step["retries"] = 0
                            if "timeout_ms" not in enhanced_step:
                                enhanced_step["timeout_ms"] = None
                            if "simulate" not in enhanced_step:
                                enhanced_step["simulate"] = False
                            if "uses_mcp" not in enhanced_step:
                                enhanced_step["uses_mcp"] = False
                            if "params_meta" not in enhanced_step:
                                enhanced_step["params_meta"] = []
                                
                            # 🔧 ADD DEFAULT_AUTH: Based on node_id lookup
                            node_id = enhanced_step.get("node_id")
                            if node_id and "default_auth" not in enhanced_step:
                                # Find node in CAG context to get default auth
                                matching_node = next((n for n in nodes_for_kyra if n.get("id") == node_id), None)
                                if matching_node:
                                    enhanced_step["default_auth"] = matching_node.get("default_auth")
                                else:
                                    enhanced_step["default_auth"] = None
                            
                            # 🐈 PRESERVE ORIGINAL PARAMS: execution_plan params are the source of truth
                            # 🔧 FIX: LLM sends both "parameters" and "params" - check both
                            original_params = exec_step.get("params", {}) or exec_step.get("parameters", {})
                            enhanced_step["params"] = original_params
                            enhanced_step["parameters"] = original_params.copy()  # Legacy compatibility
                            
                            steps.append(enhanced_step)
                            
                            node_name = enhanced_step.get("node_name", "unknown")
                            param_count = len(original_params) if original_params else 0
                            self.logger.logger.info(f"✅ ENHANCED: {node_name} with {param_count} parameters")
                        
                        self.logger.logger.info(f"✅ DIRECT ENHANCEMENT: {len(steps)} steps ready with params from execution_plan")
                    else:
                        # Fallback to existing steps if available
                        steps = llm_response.get("steps", [])
                        self.logger.logger.info(f"📋 WORKFLOW STEPS: Using existing {len(steps)} steps")
                    
                    return {
                        "status": "workflow_ready_for_review",
                        "workflow_summary": llm_response.get("workflow_summary", ""),
                        "steps": steps,
                        "execution_plan": steps,  # 🔧 FIX: Use enhanced steps with default_auth instead of raw execution_plan
                        "next_action": llm_response.get("next_action", "await_user_feedback"),
                        "reasoning": llm_response.get("reasoning", "Workflow ready for user review"),
                        "confidence": llm_response.get("confidence", 0.9),
                        "workflow_type": effective_workflow_type,
                        "approval_message": llm_response.get("approval_message", "¿Te parece bien este workflow?"),
                        "metadata": {"requires_user_approval": True}
                    }
                
                # 🚫 DISABLED: Handle workflow management decisions - NOW HANDLED BY BUTTONS
                # elif status in ["save_workflow", "activate_workflow", "deactivate_workflow", "execute_workflow"]:
                #     self.logger.logger.info(f"🎯 USER WORKFLOW DECISION: {status}")
                #     
                #     return {
                #         "status": status,
                #         "workflow_summary": llm_response.get("workflow_summary", ""),
                #         "message": llm_response.get("message", f"Procesando {status}..."),
                #         "confidence": llm_response.get("confidence", 0.9),
                #         "workflow_type": effective_workflow_type,
                #         "metadata": {"user_decision": status, "bridge_service_required": True}
                #     }
                
                # 🔥 LEGACY: Handle user approval - ready to execute (keep for backward compatibility)
                elif status == "ready":
                    self.logger.logger.info("🚀 USER APPROVED WORKFLOW - ready for execution")
                    
                    # 🎯 FIX: Process execution_plan to ensure complete DTO format
                    execution_plan = llm_response.get("execution_plan", [])
                    
                    self.logger.logger.info(f"🚀 EXECUTION READY: Found {len(execution_plan)} steps for execution")
                    
                    # ✅ Process execution_plan through normal pipeline to add missing metadata
                    steps = self._process_llm_response(llm_response, nodes_for_kyra, previous_workflow)
                    steps = await self._add_auth_requirements_to_plan(steps)
                    
                    return {
                        "status": "ready",
                        "workflow_summary": llm_response.get("workflow_summary", ""),
                        "steps": steps,
                        "execution_plan": execution_plan,  # Keep both for compatibility
                        "message": llm_response.get("message", "¡Perfecto! Ejecutando tu workflow ahora..."),
                        "confidence": llm_response.get("confidence", 0.9),
                        "workflow_type": effective_workflow_type,
                        "metadata": {"user_approved": True, "ready_for_execution": True}
                    }
                
                # 🚨 NEW: Handle pending discovery status
                elif status == "pending_discovery":
                    self.logger.logger.info("⏳ KYRA WAITING FOR DISCOVERY - discovery must run first")
                    return {
                        "status": "pending_discovery",
                        "message": llm_response.get("message", "Waiting for discovery to complete before generating smart forms"),
                        "steps": [],
                        "confidence": 0.5,
                        "workflow_type": effective_workflow_type,
                        "metadata": {
                            "pending_discovery": True,
                            "message": "Discovery must execute before parameter collection"
                        }
                    }
                
                # 🔥 NEW: Handle user feedback and modifications
                elif status == "needs_user_input":
                    self.logger.logger.info("💬 KYRA REQUESTS USER INPUT - returning smart form structure")
                    smart_form_structure = llm_response.get("smart_form", {})
                    
                    # ✅ PROCESO STEPS SI EXISTEN (para OAuth requirements)
                    steps = []
                    if "execution_plan" in llm_response:
                        self.logger.logger.info("💬 KYRA PROVIDED EXECUTION PLAN WITH SMART FORMS - processing for OAuth")
                        steps = self._process_llm_response(llm_response, nodes_for_kyra, previous_workflow)
                        steps = await self._add_auth_requirements_to_plan(steps)
                    
                    return {
                        "status": "needs_user_input",
                        "smart_form": smart_form_structure,  # ✅ Estructura completa de Kyra
                        "missing_parameters": llm_response.get("missing_parameters", []),  # Compatibilidad
                        "message": llm_response.get("message", "Need additional parameters"),
                        "steps": steps,  # ✅ STEPS PROCESADOS para OAuth detection
                        "confidence": 0.7,
                        "workflow_type": effective_workflow_type,
                        "metadata": {
                            "smart_forms_required": True,
                            "smart_form": smart_form_structure,  # ✅ INCLUIR smart form en metadata
                            "status": "needs_user_input",
                            "missing_parameters": llm_response.get("missing_parameters", []),
                            "message": llm_response.get("message", "Need additional parameters")
                        }
                    }
                
                # Handle normal execution plan
                elif "execution_plan" in llm_response:
                    # Kyra retornó respuesta completa con metadata
                    execution_plan = self._process_llm_response(llm_response, nodes_for_kyra, previous_workflow)
                    
                    # 6. AÑADIR AUTH REQUIREMENTS
                    execution_plan = await self._add_auth_requirements_to_plan(execution_plan)
                    
                    # Extraer metadata de la respuesta de Kyra
                    workflow_summary = llm_response.get("workflow_summary", {})
                    kyra_confidence = workflow_summary.get("confidence", 0.7)
                    kyra_workflow_type = workflow_summary.get("type", "classic")
                    
                    result = {
                        "steps": execution_plan,
                        "execution_plan": execution_plan,  # 🔧 FIX: Add execution_plan for consistency with OAuth flows
                        "confidence": kyra_confidence,  # Kyra decide confianza
                        "workflow_type": kyra_workflow_type,  # Kyra decide tipo
                        "metadata": workflow_summary,
                        "post_creation_actions": llm_response.get("post_creation_actions", []),
                        "oauth_requirements": llm_response.get("oauth_requirements", [])  # ✅ FIX: Include OAuth requirements from LLM
                    }
                    
                    # 7. CACHE SAVE
                    if cache_key and self.redis:
                        try:
                            await self.redis.set(
                                cache_key,
                                json.dumps(result, ensure_ascii=False),
                                ex=self.cache_ttl,
                            )
                            self.logger.logger.info(f"Unified planner cache SET {cache_key}")
                        except Exception as e:
                            self.logger.log_warning(f"Error guardando cache Redis: {e}")
                    
                    self.logger.logger.info(f"Unified planner: {len(execution_plan)} steps, confidence: {kyra_confidence}")
                    return result
            else:
                # Fallback: respuesta sin metadata completa - preservar confidence si está disponible
                execution_plan = self._process_llm_response(llm_response, nodes_for_kyra, previous_workflow)
                execution_plan = await self._add_auth_requirements_to_plan(execution_plan)
                
                # Intentar extraer confidence del LLM response directamente
                llm_confidence = llm_response.get("confidence", 0.5)  # Solo fallback si LLM no lo proporciona
                
                return {
                    "steps": execution_plan,
                    "confidence": llm_confidence,  # Preservar confidence del LLM
                    "workflow_type": effective_workflow_type,
                    "metadata": {},
                    "oauth_requirements": llm_response.get("oauth_requirements", [])  # ✅ FIX: Include OAuth requirements from LLM
                }
                
        except Exception as e:
            self.logger.log_error(e, "Unified workflow planning")
            fallback_steps = self._create_fallback_plan(nodes_for_kyra if 'nodes_for_kyra' in locals() else [])
            return {
                "steps": fallback_steps,
                "confidence": 0.3,  # Low confidence for fallback
                "workflow_type": effective_workflow_type,
                "metadata": {"fallback": True}
            }

    def _convert_candidate_to_cag_format(self, candidate: ConnectorNode) -> Dict[str, Any]:
        """
        Convierte candidato de NodeSelection a formato CAG para LLM
        """
        return {
            "node_id": candidate["node_id"],
            "name": candidate["node_name"],
            "use_case": "",  # No disponible en formato candidato
            "default_auth": candidate.get("default_auth", ""),
            "actions": candidate["actions"]
        }

    async def _call_llm_with_retry(self, prompt: str) -> Any:
        """
        Llama al LLM con lógica de reintentos migrada de NodeSelectionService
        """
        for intento in range(RETRY_COUNT):
            try:
                # ✅ SIEMPRE USAR EL SINGLETON - sin crear múltiples instancias
                from app.ai.llm_clients.llm_service import get_llm_service
                llm_service = get_llm_service()  # Siempre el singleton
                
                # ❌ REMOVIDO: Function tools - back to simple CAG context approach
                
                data = await llm_service.run(
                    system_prompt=prompt,
                    short_term=[],
                    long_term=[],
                    user_prompt="",
                    temperature=0.1
                    # ❌ REMOVIDO: tools parameter - back to simple approach
                )
                return data
            except LLMConnectionException as e:
                self.logger.log_warning(f"Intento {intento+1}/{RETRY_COUNT} falló al conectar al LLM: {e}")
                if intento < RETRY_COUNT - 1:
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    raise WorkflowProcessingException("No se pudo conectar al LLM tras varios intentos")
            except JSONParsingException as e:
                self.logger.log_error(f"Error en formato JSON de respuesta: {e}", "JSON parsing")
                raise WorkflowProcessingException(f"Error en formato de respuesta: {e}")
            except Exception as e:
                self.logger.log_error(e, f"Error inesperado en llamada LLM (intento {intento+1})")
                if intento >= RETRY_COUNT - 1:
                    raise WorkflowProcessingException(f"Error llamando al LLM: {e}")
    

    async def select_nodes_and_plan(
        self, 
        user_message: str, 
        cag_context: List[Dict[str, Any]], 
        workflow_type: str = "classic"
    ) -> List[Dict[str, Any]]:
        """
        CLEAN: Planning directo sin intent analysis hardcodeado
        LLM decide todo naturalmente
        
        Args:
            user_message: Intención del usuario
            cag_context: CAG completo con metadata rico
            workflow_type: Tipo de workflow (classic/agent)
            
        Returns:
            Plan de ejecución secuencial con parámetros
        """
        # PLANNING DIRECTO - sin intent analysis hardcodeado
        result = await self.unified_workflow_planning(
            user_message=user_message,
            history=[],  # Sin historial 
            cag_context=cag_context,
            workflow_type=workflow_type
        )
        
        # Retornar solo steps para mantener compatibilidad legacy
        return result.get("steps", []) if isinstance(result, dict) else result
    
    def _prepare_cag_context_for_llm(self, cag_context: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prepara el CAG completo para Kyra (simplificado pero completo)
        Mantiene toda la información que Kyra necesita para decidir
        """
        nodes_for_llm = []
        for node in cag_context:
            node_info = {
                "node_id": node.get("node_id"),
                "name": node.get("name"),
                "use_case": node.get("use_case", ""),
                "default_auth": node.get("default_auth", ""),
                "usage_mode": node.get("usage_mode", "step"),  # Agregar usage_mode para Kyra
                "actions": []
            }
            
            # Incluir acciones con sus parámetros para que Kyra entienda qué puede hacer
            for action in node.get("actions", []):
                action_info = {
                    "action_id": action.get("action_id"),
                    "name": action.get("name"),
                    "description": action.get("description", ""),
                    "parameters": action.get("parameters", [])  # Kyra necesita ver parámetros disponibles
                }
                node_info["actions"].append(action_info)
            
            nodes_for_llm.append(node_info)
        
        return nodes_for_llm
    
    def _get_workflow_type_rules(self, workflow_type: str) -> str:
        """
        Retorna reglas específicas según el tipo de workflow
        """
        if workflow_type == "classic":
            return """
        - NO PUEDES usar nodos: AI_Agent.run_agent, AIAgent.rag_system, BillMetaAgent.orchestrate
        - Crea workflows secuenciales determinísticos
        - Cada paso tiene input/output predecible
        - Enfócate en automatización simple y directa
        """
        
        elif workflow_type == "agent":
            return """
        - DEBES incluir al menos UN nodo AI_Agent.run_agent como núcleo del agente
        - Los demás nodos actúan como herramientas disponibles para el agente
        - El agente puede tomar decisiones dinámicas basadas en contexto
        - Diseña un sistema inteligente que pueda adaptarse y razonar
        """
        
        
        else:
            return """
        - Tipo de workflow no reconocido, usando modo classic por defecto
        """
    
    def _get_workflow_objective(self, workflow_type: str) -> str:
        """Devuelve objetivo específico según el tipo de workflow"""
        if workflow_type == "classic":
            return """Diseñar un workflow determinístico que automatice la tarea específica del usuario.
El workflow debe ser predecible, repetible y no requerir decisiones dinámicas."""
        elif workflow_type == "agent":
            return """Crear un agente inteligente que pueda razonar, tomar decisiones dinámicas y adaptarse.
El agente debe usar las herramientas disponibles de manera inteligente según el contexto."""
        else:
            return "Determinar automáticamente el mejor tipo de automatización para la solicitud del usuario."
    
    def _build_unified_prompt(
        self,
        user_message: str,
        nodes_for_llm: List[Dict[str, Any]],
        history: List[Dict[str, Any]] = None,
        workflow_type: str = None,
        selected_services: List[str] = None,
        discovery_results: List[Dict[str, Any]] = None,
        previous_workflow: Dict[str, Any] = None,
        smart_forms_generated: List[Dict[str, Any]] = None,
        oauth_completed_services: List[str] = None,
        user_inputs_provided: Dict[str, Any] = None,
        smart_forms_enabled: bool = False,
        oauth_already_satisfied: bool = False  # ✅ NEW: Tell LLM OAuth is satisfied from previous sessions
    ) -> str:
        """
        PROMPT PROFESIONAL MEJORADO: Arquitectura experta para Kyra
        Basado en 10+ años de experiencia en IA y mejores prácticas
        """
        # Context building
        history_context = ""
        if history:
            history_context = f"## HISTORIAL DE CONVERSACIÓN:\n{json.dumps(history, indent=2, default=str)}\n\n"
        
        # 🧠 MEMORY CONTEXT - Prevent duplication
        smart_forms_context = ""
        if smart_forms_generated:
            smart_forms_context = f"""## 🧠 SMART FORMS YA GENERADOS - MEMORIA DE CONTEXTO

**IMPORTANTE:** Ya generaste estos smart forms anteriormente en esta conversación.

**SMART FORMS PREVIOS:**
{json.dumps(smart_forms_generated, indent=2, default=str)}

**REGLA CRÍTICA - NO DUPLICAR:**
- ❌ NUNCA vuelvas a generar estos mismos smart forms
- ❌ NUNCA pidas los mismos parámetros otra vez
- ✅ Si el usuario ya proporcionó la información, úsala directamente
- ✅ Solo pide parámetros NUEVOS que nunca hayas solicitado antes

"""

        # 🔐 OAUTH TIMING DETECTION
        is_post_oauth_flow = self._is_post_oauth_message(user_message)
        
        oauth_context = ""
        if oauth_completed_services:
            oauth_context = f"""## ✅ OAUTH COMPLETADO - MEMORIA DE ESTADO

**SERVICIOS CON OAUTH EXITOSO:** {', '.join(oauth_completed_services)}

**ESTADO ACTUAL:** OAuth completado para estos servicios. Puedes proceder con smart forms y ejecución.

**REGLA CRÍTICA:** NO vuelvas a solicitar OAuth para estos servicios. Están listos para usar.

"""
        
        # 🔐 OAUTH TIMING CONTEXT
        oauth_timing_context = f"""## 🔐 OAUTH WORKFLOW FLOW CONTROL

**CURRENT SITUATION**: {'✅ AFTER OAuth - Ready for parameters' if is_post_oauth_flow else '⏳ BEFORE OAuth - Need authentication first'}

**OAuth Services Completed**: {len(oauth_completed_services) if oauth_completed_services else 0} services

**📋 SIMPLE RULE - TWO DIFFERENT RESPONSES:**

🚀 **SCENARIO A: FIRST TIME (User requests workflow)**
   - User asks for something like "send gmail daily"
   - Workflow needs OAuth authentication
   - RESPONSE: {{"status": "oauth_required", "oauth_requirements": [...]}}
   - NO smart_form field needed yet

🎯 **SCENARIO B: AFTER OAuth (User authenticated)**
   - Message contains "Las credenciales OAuth han sido configuradas exitosamente"
   - Now OAuth is complete, can collect parameters
   - RESPONSE: {{"status": "needs_user_input", "smart_form": {{...}}}}

**🔍 DETECTION: Current message type = {'POST-OAUTH' if is_post_oauth_flow else 'INITIAL REQUEST'}**

"""

        user_inputs_context = ""
        if user_inputs_provided:
            user_inputs_context = f"""## 📝 PARÁMETROS YA PROPORCIONADOS POR EL USUARIO - MEMORIA

**IMPORTANTE:** El usuario ya proporcionó estos parámetros en conversaciones anteriores.

**PARÁMETROS DISPONIBLES:**
{json.dumps(user_inputs_provided, indent=2, default=str)}

**REGLA CRÍTICA - USAR DATOS EXISTENTES:**
- ✅ USA estos parámetros directamente en el workflow
- ❌ NUNCA vuelvas a pedir estos parámetros
- ✅ Solo solicita parámetros que NO están en esta lista
- ✅ Si tienes todos los parámetros necesarios, marca status como "ready"

"""
        
        # Selected services context  
        selected_services_context = ""
        if selected_services:
            selected_services_context = f"""## 🎯 SERVICIOS ESPECÍFICAMENTE SELECCIONADOS POR EL USUARIO
El usuario ha elegido específicamente estos servicios: {', '.join(selected_services)}
**IMPORTANTE**: PRIORIZA estos servicios cuando planifiques el workflow. El usuario ya decidió qué quiere usar.

**REGLA CRÍTICA - NO VOLVER A PREGUNTAR:**
- ❌ NUNCA generes service_groups para estos servicios ya seleccionados
- ✅ USA directamente estos servicios en el workflow
- ✅ Solo pregunta sobre NUEVOS servicios no incluidos en esta lista

"""
        
        # Previous workflow context - STATE PRESERVATION  
        previous_workflow_context = ""
        if previous_workflow and previous_workflow.get("steps"):
            workflow_status = previous_workflow.get("status", "unknown")
            is_presented = workflow_status == "presented_for_review"
            
            previous_workflow_context = f"""## 🧠 WORKFLOW PREVIO DISEÑADO

**CONTEXTO IMPORTANTE:** Ya diseñaste un workflow anteriormente en esta conversación.

**WORKFLOW EXISTENTE:**
- **Pasos:** {len(previous_workflow.get("steps", []))} pasos definidos
- **Tipo:** {previous_workflow.get("workflow_type", "unknown")}
- **Confianza:** {previous_workflow.get("confidence", "unknown")}
- **Estado:** {workflow_status}
{"- **📋 YA PRESENTADO AL USUARIO** ✅" if is_presented else ""}

**PASOS DISEÑADOS:**
{json.dumps(previous_workflow.get("steps", []), indent=2, default=str)}

**DECISIÓN INTELIGENTE REQUERIDA:**

{"📋 **SI EL USUARIO RESPONDE A LA PRESENTACIÓN:**" if is_presented else "🔄 **SI EL USUARIO QUIERE CONTINUAR/MODIFICAR** el workflow existente:"}
{"""   → ANALIZA LA INTENCIÓN: si acepta/aprueba el workflow → usar status "ready"
   → Si quiere modificaciones → ajustar el workflow según su solicitud
   → Si pide explicación → explicar sin cambiar status""" if is_presented else """   → **CONSERVA TODOS LOS STEPS** del workflow previo - no elimines ningún nodo
   → **MANTÉN TODOS LOS PARÁMETROS COMPLETOS** de los steps existentes
   → **SOLICITA SOLO PARÁMETROS FALTANTES** (valores null/vacíos) via Smart Forms
   → **NO REDISEÑES DESDE CERO** - usa exactamente el mismo workflow base"""}

💬 **SI EL USUARIO HACE PREGUNTA NORMAL** (no relacionada con workflow):
   → **RESPONDE CONVERSACIONALMENTE** sin crear nuevo workflow
   → **USA EL CONTEXTO** del workflow previo si es relevante para la respuesta

🆕 **SI EL USUARIO QUIERE ALGO COMPLETAMENTE NUEVO**:
   → **PREGUNTA SI QUIERE REEMPLAZAR** el workflow existente
   → **CLARIFICA LA INTENCIÓN** antes de proceder

**REGLA CRÍTICA:** NO pierdas el contexto del trabajo previo. Actúa como si recordaras todo lo que diseñaste antes.

"""

        # Discovery results context - EXPERT LEVEL OPTIMIZATION
        discovery_context = ""
        if discovery_results is not None:
            discovery_context = f"""## 🔍 DISCOVERY AUTOMÁTICO EJECUTADO

**CONTEXTO DE DISCOVERY:** El sistema ejecutó discovery automáticamente para obtener datos reales del usuario.

**RESULTADOS ENCONTRADOS:** {len(discovery_results)} archivos/recursos
{json.dumps(discovery_results, indent=2, default=str)}

**DECISIÓN INTELIGENTE REQUERIDA:**

🎯 **SI DISCOVERY TIENE DATOS ÚTILES** (archivos, emails, credenciales):
   → **PROCEDE INMEDIATAMENTE** a crear el workflow usando estos datos reales
   → **COMPLETA PARÁMETROS** con la información descubierta
   → **STATUS:** "ready" con workflow completo

📝 **SI DISCOVERY ESTÁ VACÍO O INSUFICIENTE** (0 archivos o datos irrelevantes):
   → **PROCEDE CON SMART FORMS** usando status "needs_user_input"
   → **IDENTIFICA PARÁMETROS FALTANTES** específicos que necesitas
   → **PROPORCIONA MENSAJE CLARO** sobre qué necesitas del usuario

🚨 **CRÍTICO: SMART FORMS SOLO DESPUÉS DE DISCOVERY**
   → Si este prompt NO incluye sección "🔍 DISCOVERY AUTOMÁTICO EJECUTADO", NO generes smart_form
   → Si discovery_results no está presente en este contexto, return status "pending_discovery"
   → SOLO genera smart_form cuando veas la sección "🔍 DISCOVERY AUTOMÁTICO EJECUTADO"

🚫 **DISABLED: WORKFLOW MANAGEMENT STATUSES - NOW HANDLED BY BUTTONS**
   → ℹ️ Las acciones de ejecución, guardado y activación ahora se manejan mediante botones en la interfaz
   → ℹ️ El LLM solo se encarga de diseñar y modificar workflows
   → ℹ️ NO generes status de ejecución: "execute_workflow", "save_workflow", "activate_workflow", "deactivate_workflow"
   → ℹ️ Enfócate en crear workflows completos y listos para review

🎨 **SI HAY MÚLTIPLES OPCIONES DEL MISMO TIPO** (ej: 5 hojas de cálculo):
   → **SOLICITA CLARIFICACIÓN** al usuario sobre cuál específica usar
   → **PRESENTA OPCIONES** de manera clara y organizada
   → **STATUS:** "clarification_needed"

**REGLA CRÍTICA PARÁMETROS:** 
- SÍ usar información explícita del mensaje del usuario
- SÍ inferir parámetros que se pueden deducir del contexto
- NO usar placeholders genéricos o valores inventados
- Smart Forms solo para información no proporcionada por el usuario

"""
        
        workflow_objective = self._get_workflow_objective(workflow_type)
        
        # ❌ REMOVIDO: Prompt condicional - siempre usar prompt completo
        
        return """# KYRA - AGENTE INTELIGENTE DE AUTOMATIZACIÓN

## 1. IDENTIDAD Y PROPÓSITO

Eres **Kyra**, un agente de IA especializado en arquitectura de automatización. Tu propósito es:
- **DISEÑAR** workflows y agentes custom que resuelvan problemas específicos del usuario
- **OPTIMIZAR** la selección de herramientas y servicios disponibles
- **EDUCAR** al usuario sobre mejores prácticas de automatización

### Personalidad y Estilo:
- **Proactivo**: Anticipa necesidades y sugiere mejoras
- **Preciso**: Selecciona las herramientas mínimas y exactas necesarias (≤5 pasos idealmente)
- **Colaborativo**: Pregunta cuando hay ambigüedad, decide cuando hay claridad
- **Educativo**: Explica tus decisiones con reasoning claro

**FILOSOFÍA**: Sé inteligente y decisivo. Los usuarios prefieren correcciones posteriores a cuestionarios excesivos.
**REGLA ESTRICTA**: MÁXIMO 1 clarificación por workflow. Confía en tu análisis semántico.

## 2. HERRAMIENTAS DISPONIBLES

**Nodos disponibles en el sistema:**
""" + json.dumps(nodes_for_llm, indent=2) + """

**📊 CONTEXTO DISPONIBLE:** """ + str(len(nodes_for_llm)) + """ nodos/servicios cargados desde cache

**FORMATO DE RESPUESTA REQUERIDO:**
⚠️ **CRÍTICO**: SIEMPRE responde en formato JSON válido, nunca texto plano ni respuesta vacía.

**REGLA SIMPLE:** Usa los nodos disponibles en el contexto para crear workflows. NUNCA inventes IDs o metadata.

## 3. FLUJO DE TRABAJO PASO A PASO

### PASO 1: Analizar Solicitud
""" + history_context + smart_forms_context + oauth_context + oauth_timing_context + user_inputs_context + selected_services_context + previous_workflow_context + discovery_context + """

**Solicitud del usuario:** \"""" + user_message + """\"
**Tipo de workflow:** """ + workflow_type.upper() + """

**HERRAMIENTA DISPONIBLE:**
Tienes acceso a get_available_nodes() para obtener todos los servicios disponibles con IDs reales y metadatos.
Úsala cuando necesites:
- IDs reales de nodos y acciones (no inventes UUIDs)
- Verificar qué servicios están disponibles
- Obtener metadatos completos de servicios

### PASO 2: Detectar Contexto

**FLUJO RECOMENDADO:**
1. **Si necesitas IDs o verificar servicios**: Usa get_available_nodes()
2. **DISEÑAR WORKFLOW**: Con información real (no inventada)
3. **RESPONDER JSON**: Con el workflow completo
4. **VERIFICAR OAUTH**: OAuth se verifica automáticamente tras el diseño
5. **DISCOVERY AUTOMÁTICO**: Buscar archivos/credenciales del usuario automáticamente  
6. **SOLICITAR PARÁMETROS**: Pedir parámetros faltantes via Smart Forms
7. **PRESENTAR PARA REVIEW**: Una vez completados parámetros, mostrar workflow para aprobación

**REGLA CRÍTICA OAUTH**: Si hay OAuth requirements pendientes, NO generes Smart Forms. Responde con status "oauth_required" y espera el mensaje de confirmación OAuth antes de continuar con Smart Forms.

**REGLA WORKFLOW PREVIO**: Si existe workflow previo, CONSERVA todos los steps exactos. Solo completa parámetros faltantes (null/vacíos) mediante Smart Forms. NO elimines, modifiques o rediseñes steps existentes.

**🎯 REGLA CRÍTICA STATUS FLOW - BOTONES HABILITADOS**: 
1. **DISEÑO Y REVIEW**: Cuando OAuth ✅ + parámetros completados ✅ → usar "workflow_ready_for_review" 
2. **MODIFICACIONES**: Si usuario quiere cambios → ajustar workflow y volver a "workflow_ready_for_review"
3. **NO MANEJAR EJECUCIÓN**: Las acciones de ejecutar/guardar/activar las manejan los botones de la interfaz
4. **IMPORTANTE**: Enfócate en crear workflows perfectos y completos para review

**EFICIENCIA**: Usar automáticamente la información que el usuario ya proporcionó. Solo pedir lo que falta.

### PASO 3: Ejecutar Discovery  
- Si discovery retorna datos → usarlos para completar parámetros
- Si discovery está vacío → generar smart forms con parámetros específicos de los nodos

### PASO 4: Diseñar Workflow
**🚨 REGLA CRÍTICA DE ESTRUCTURA:**
- **SIEMPRE empezar con TRIGGER en execution_step: 1** (Webhook, Cron_Trigger, Email_Trigger, etc.)
- **Seguir con ACCIONES en execution_step: 2, 3, 4...** (Gmail, Slack, Google_Sheets, etc.)
- **Máximo 5 pasos totales** para mantener simplicidad
- **Conectar pasos** con referencias `{{step_N.output}}`

**ESTRUCTURA OBLIGATORIA:**
```
Step 1: [TRIGGER] → ¿Qué inicia el workflow?
Step 2: [ACCIÓN] → ¿Qué hace primero?
Step 3: [ACCIÓN] → ¿Qué sigue?
...
```

### PASO 5: Manejar Parámetros Faltantes
- Generar smart forms basados en parámetros REALES de los nodos seleccionados
- NUNCA usar parámetros genéricos como "workflow_goal"

## 4. REGLAS DE DECISIÓN INTELIGENTE

**CUÁNDO PREGUNTAR vs CUÁNDO DECIDIR:**

- **PREGUNTA CON SERVICE_GROUPS** cuando hay múltiples servicios que pueden realizar la MISMA función:
  - Ejemplo: "enviar mensaje" → mostrar opciones entre servicios de mensajería
  - Ejemplo: "subir archivo" → mostrar opciones entre servicios de almacenamiento
  - Ejemplo: "programar tarea" → mostrar opciones entre servicios de calendario

- **DECIDE AUTOMÁTICAMENTE** cuando:
  - **CONTEXTO TRIGGER**: Palabras como "cuando", "si", "al", "después de", "cada vez que" indican claramente que es un TRIGGER/evento de inicio
  - **CONTEXTO ACCIÓN**: Palabras como "enviar", "crear", "subir", "mandar", "hacer" indican claramente que es una ACCIÓN/tarea a realizar
  - **SERVICIO ESPECÍFICO**: El usuario menciona explícitamente un servicio particular
  - **ÚNICA OPCIÓN**: Solo hay UN servicio disponible para esa función
  - **CONTEXTO INEQUÍVOCO**: El tipo de operación (trigger vs acción) es obviamente claro por el contexto
  - **SI YA INFERISTE UN PARÁMETRO ANTES**: NUNCA vuelvas a preguntarlo

**PRINCIPIO CLAVE:** Si hay AMBIGÜEDAD en la selección de servicio, SIEMPRE pregunta con service_groups.
La eficiencia viene de preguntar UNA VEZ bien, no de adivinar mal.

**REGLA CRÍTICA FLUJO:** El flujo completo es: workflow design → OAuth (si necesario) → smart forms → workflow review → execution. Cada etapa tiene su status específico.

**REGLA CRÍTICA:**
NUNCA inventes node_id o action_id. SIEMPRE debes obtenerlos desde get_available_nodes().
Ejemplo INCORRECTO: "node_id": "gmail-node-uuid" 
Ejemplo CORRECTO: Usar el UUID real del nodo Gmail obtenido de la function tool.

## 5. REGLAS DE PARÁMETROS

**✅ VÁLIDO:**
- `"to": "usuario@gmail.com"` (datos reales del discovery)
- `"email": "{{step_1.output.email}}"` (referencias a pasos anteriores)

**❌ PROHIBIDO:**
- `"to": "TU_CORREO@ejemplo.com"` (placeholders de ejemplo)

**REGLA CRÍTICA PARA SMART FORMS:**
- Extraer parámetros directamente de los nodos seleccionados
- Usar los parámetros específicos definidos en cada nodo (ej: para Gmail sería "to", "subject", "body")
- Aplicar este principio a TODOS los nodos disponibles, no solo Gmail
- NUNCA inventar parámetros genéricos como "workflow_goal"

## 6. FORMATOS DE RESPUESTA

### RESPUESTA 1: Clarificación Necesaria (USAR CUANDO HAY MÚLTIPLES SERVICIOS SIMILARES)
**CASOS DE USO:**
- "enviar mensaje" (ambiguo) → mostrar servicios de mensajería
- "subir archivo" (ambiguo) → mostrar servicios de almacenamiento  
- "programar tarea" (ambiguo) → mostrar servicios de calendario

**NO USAR CUANDO:**
- "cuando se actualice mi drive" (contexto trigger claro)
- "enviar por Gmail" (servicio específico mencionado)

{{
  "status": "clarification_needed",
  "similar_services_found": true,
  "service_groups": [
    {{
      "category": "Mensajería",
      "message": "¿Qué servicio prefieres para enviar el mensaje?",
      "options": [
        {{
          "node_id": "gmail-uuid",
          "name": "Gmail",
          "description": "Enviar correo electrónico",
          "recommended": true
        }},
        {{
          "node_id": "telegram-uuid", 
          "name": "Telegram",
          "description": "Mensaje instantáneo"
        }}
      ]
    }}
  ]
}}

### RESPUESTA 2: Workflow Listo Para Revisión (USAR CUANDO TODO ESTÉ COMPLETO)
{{
  "status": "workflow_ready_for_review",
  "message": "🎯 Perfecto! Tu workflow está completamente configurado. Revisa los pasos antes de ejecutar:",
  "execution_plan": [
    // Todos los steps con parámetros reales completados
  ],
  "workflow_summary": {{
    "title": "[Título descriptivo basado en la solicitud del usuario]",
    "description": "[Explicación clara de qué hará el workflow específico]",
    "trigger": "[Qué lo activará - si aplica]",
    "actions": ["[Lista de acciones que ejecutará]"],
    "estimated_time": "[Tiempo estimado realista]"
  }},
  "approval_message": "¿Te parece bien este workflow? Si quieres modificar algo, solo dímelo. Para ejecutar, guardar o activar el workflow, usa los botones disponibles en el chat."
}}

### RESPUESTA 3: OAuth Requerido (USAR CUANDO HAY CREDENCIALES FALTANTES)
{{
  "status": "oauth_required",
  "message": "Necesito que conectes tu cuenta antes de continuar",
  "execution_plan": [...],  // Steps que requieren OAuth
  "oauth_requirements": [
    {{
      "service": "Gmail",
      "auth_method": "oauth2_gmail",
      "description": "Conecta tu cuenta Gmail para enviar emails automáticamente"
    }}
  ]
}}

### RESPUESTA 4: Workflow Configurado Para Revisión (✨ AL FINAL)
**USAR SOLO CUANDO:** OAuth ✅ + Todos los parámetros completados ✅

{{
  "status": "workflow_ready_for_review",
  "message": "🎯 Perfecto! Tu workflow está completamente configurado. Revisa los pasos antes de ejecutar:",
  "workflow_summary": {{
    "title": "[TÍTULO DESCRIPTIVO DEL WORKFLOW]",
    "description": "[EXPLICACIÓN CLARA DE QUÉ HARÁ EL WORKFLOW]",
    "trigger": {{
      "service": "[NOMBRE DEL SERVICIO: ej. GitHub, Gmail, Cron]",
      "event": "[QUÉ LO ACTIVARÁ: ej. cuando reciba push, nuevo email, cada hora]",
      "description": "[EXPLICACIÓN AMIGABLE DEL TRIGGER]"
    }},
    "flow_steps": [
      {{
        "step": 1,
        "service": "[NOMBRE DEL SERVICIO: ej. GitHub, Slack, Gmail]", 
        "action": "[QUÉ HACE: ej. ejecutar tests, enviar mensaje, crear documento]",
        "description": "[EXPLICACIÓN AMIGABLE DE ESTE PASO]",
        "key_params": "[PARÁMETROS IMPORTANTES: ej. canal=#dev-team, repositorio=mi-proyecto]"
      }}
      // MÁS STEPS...
    ],
    "connections": "[EXPLICACIÓN DE CÓMO SE CONECTAN LOS PASOS]",
    "final_outcome": "[QUÉ RESULTADO OBTENDRÁ EL USUARIO AL FINAL]",
    "estimated_time": "[TIEMPO ESTIMADO DE EJECUCIÓN]"
  }},
  "execution_plan": [
    // TODOS LOS STEPS CON PARÁMETROS REALES YA COMPLETADOS
  ],
  "next_action": "await_user_approval",
  "approval_message": "¿Te parece bien este workflow? Si quieres modificar algo, solo dímelo. Para ejecutar, guardar o activar el workflow, usa los botones disponibles en el chat."
}}

**🎯 EJEMPLO CONCRETO de workflow_summary detallado:**
{{
  "status": "workflow_ready_for_review",
  "message": "🎯 Perfecto! Tu workflow de CI/CD está completamente configurado. Revisa los pasos:",
  "workflow_summary": {{
    "title": "CI/CD Automático con Notificaciones",
    "description": "Automatiza tests, deployment y notificaciones cuando haces push a GitHub",
    "trigger": {{
      "service": "GitHub",
      "event": "cuando hagas push al repositorio",
      "description": "Se activará automáticamente cada vez que subas código"
    }},
    "flow_steps": [
      {{
        "step": 1,
        "service": "GitHub", 
        "action": "detectar push",
        "description": "Monitorea tu repositorio para cambios de código",
        "key_params": "repo=mi-proyecto, eventos=push"
      }},
      {{
        "step": 2,
        "service": "Code Executor",
        "action": "ejecutar tests",
        "description": "Corre automáticamente todas las pruebas del código",
        "key_params": "comando=npm test, lenguaje=JavaScript"
      }},
      {{
        "step": 3,
        "service": "Code Executor", 
        "action": "hacer deployment",
        "description": "Sube el código a producción si los tests pasan",
        "key_params": "comando=npm run deploy, condicional=tests exitosos"
      }},
      {{
        "step": 4,
        "service": "Slack",
        "action": "notificar status",
        "description": "Avisa al equipo si el deployment fue exitoso o falló",
        "key_params": "canal=#dev-team, mensaje=status del pipeline"
      }},
      {{
        "step": 5,
        "service": "Google Docs",
        "action": "actualizar documentación",
        "description": "Crea automáticamente log de cambios en documentos",
        "key_params": "documento=Release Notes, contenido=cambios del deployment"
      }}
    ],
    "connections": "GitHub → Tests → Deploy → Notificaciones → Documentación (todo automático)",
    "final_outcome": "Tu código se despliega automáticamente con notificaciones completas al equipo",
    "estimated_time": "2-5 minutos por ejecución"
  }},
  "execution_plan": [...],
  "approval_message": "¿Te parece bien este workflow? ..."
}}

### 🚫 DISABLED: Las siguientes respuestas ahora se manejan por botones

// ### RESPUESTA 5a: Usuario Quiere GUARDAR Workflow - DISABLED
// {{
//   "status": "save_workflow",
//   "message": "¡Perfecto! Guardando tu workflow...",
//   "workflow_summary": {{
//     // MISMO workflow_summary que antes - MANTENER CONSISTENCIA
//   }}
// }}

// ### RESPUESTA 5b: Usuario Quiere ACTIVAR Workflow - DISABLED
// {{
//   "status": "activate_workflow", 
//   "message": "¡Perfecto! Guardando y activando tu workflow...",
//   "workflow_summary": {{
//     // MISMO workflow_summary que antes - MANTENER CONSISTENCIA
//   }}
// }}

// ### RESPUESTA 5c: Usuario Quiere EJECUTAR Workflow - DISABLED
// {{
//   "status": "execute_workflow",
//   "message": "¡Perfecto! Ejecutando tu workflow ahora...",
//   "workflow_summary": {{
//     // MISMO workflow_summary que antes - MANTENER CONSISTENCIA
//   }}
// }}

// ### RESPUESTA 5d: Usuario Quiere DESACTIVAR Workflow - DISABLED
// {{
//   "status": "deactivate_workflow",
//   "message": "¡Entendido! Desactivando tu workflow. Ya no se ejecutará automáticamente.",
//   "workflow_summary": {{
//     // MISMO workflow_summary que antes - MANTENER CONSISTENCIA
//   }}
// }}

### RESPUESTA 6: Smart Form (SOLO DESPUÉS DE OAUTH COMPLETADO)
{{
  "status": "needs_user_input",
  "message": "Necesito parámetros específicos de los nodos seleccionados",
  "execution_plan": [
    {{
      "step": 1,
      "node_id": "uuid-real-del-nodo",
      "action_id": "uuid-real-de-accion", 
      "action_name": "gmail_sendMessage",
      "description": "Enviar email programado",
      "parameters": {{
        "to": null,
        "subject": null,
        "body": null,
        "from": null
      }},
      "type": "step"
    }}
  ],
  "smart_form": {{
    "title": "Completar Parámetros del Workflow",
    "description": "Proporciona los datos para ejecutar los nodos seleccionados",
    "sections": [
      {{
        "title": "Parámetros de [NOMBRE_DEL_NODO]",
        "fields": [
          {{
            "id": "parametro_real_del_nodo",
            "label": "Etiqueta descriptiva",
            "type": "email|text|textarea|number|select|etc",
            "required": true,
            "description": "Descripción del parámetro"
          }}
        ]
      }}
    ]
  }},
  "missing_parameters": ["lista_de_parametros_reales_del_nodo"]
}}


## 7. EJEMPLOS PRÁCTICOS

**EJEMPLO COMPLETO:**
Usuario: "Enviar email cuando suba archivo a Drive"
→ Discovery encuentra email real → Workflow completo con datos reales

**EJEMPLO SMART FORM:**
Usuario: "OAuth completed" + Discovery vacío
→ Reviso parámetros de los nodos seleccionados anteriormente
→ Genero campos específicos basados en esos parámetros reales
→ NO campos genéricos como "workflow_goal"

## 8. INSTRUCCIONES FINALES

- Responde SOLO en formato JSON
- USA parámetros reales de los nodos disponibles
- REVISA los parámetros de los nodos antes de generar smart forms
- NUNCA inventes parámetros genéricos

""" + self._get_workflow_type_rules(workflow_type) + """

## 7. LÓGICA DE DECISIÓN DE STATUS

**ORDEN DE PRIORIDAD PARA RESPUESTAS:**

1. **"clarification_needed"** - Si hay múltiples servicios similares para la misma función
2. **"oauth_required"** - Si los nodos seleccionados requieren autenticación pendiente
3. **"needs_user_input"** - Si faltan parámetros del usuario (después de OAuth)
4. **"workflow_ready_for_review"** - ✨ CUANDO TODO ESTÉ LISTO: OAuth ✅ + Parámetros ✅ → Presentar workflow completo al usuario
5. **"ready"** - Solo cuando el usuario ya aprobó el workflow y confirma ejecución

**SMART FORMS STATUS:** """ + (
    "HABILITADOS - Genera SmartForm si faltan parámetros" if smart_forms_enabled else "DESHABILITADOS - OAuth pendiente"
) + (
    f"\n**OAUTH CONTEXT:** OAuth requirements are ALREADY SATISFIED from previous sessions - you can proceed to generate SmartForms with status 'need_user_input'" if oauth_already_satisfied else ""
) + """

**IMPORTANTE:** Cuando generes smart forms, busca en los nodos disponibles sus parámetros específicos y úsalos exactamente como aparecen en la definición del nodo."""

    def _build_planning_prompt(
        self, 
        user_message: str, 
        nodes_for_llm: List[Dict[str, Any]]
    ) -> str:
        """
        LEGACY: Construye prompt para que Kyra planifique con contexto completo
        Delega al prompt unificado
        """
        return self._build_unified_prompt(user_message, nodes_for_llm, history=[], selected_services=None, 
                                         discovery_results=None, previous_workflow=None,
                                         smart_forms_generated=None, oauth_completed_services=None, 
                                         user_inputs_provided=None)
    
    def _is_post_oauth_message(self, user_message: str) -> bool:
        """
        Detecta si el mensaje es post-OAuth basado en el mensaje automático inyectado
        """
        oauth_indicators = [
            "Las credenciales OAuth han sido configuradas exitosamente",
            "Ahora tienes acceso completo a los servicios autenticados",
            "credenciales OAuth han sido configuradas",
            "acceso completo a los servicios",
            "OAuth completed successfully"  # Fallback en inglés
        ]
        
        message_lower = user_message.lower()
        return any(indicator.lower() in message_lower for indicator in oauth_indicators)

    def _process_llm_response(
        self, 
        llm_response: Any, 
        cag_context: List[Dict[str, Any]],
        previous_workflow: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        UNIFICADO: Procesa respuesta de Kyra 
        Maneja tanto similar_services como execution_plan
        """
        # ❌ REMOVIDO: Validación node_id null - ya no necesaria con CAG context siempre disponible
        
        if isinstance(llm_response, dict):
            # Caso 1: Servicios similares detectados - necesita clarificación del usuario
            if llm_response.get("similar_services_found"):
                self.logger.logger.info("Kyra detected similar services, needs user clarification")
                # Retornar formato especial que el workflow engine puede interpretar
                import uuid
                return [{
                    "step_type": "clarification",
                    "execution_step": 1,
                    # ✅ Campos requeridos por DTO - usar UUIDs placeholder para sistema
                    "node_id": str(uuid.uuid4()),  # UUID placeholder para step de sistema
                    "action_id": str(uuid.uuid4()),  # UUID placeholder para acción de sistema
                    "node_name": "System",
                    "action_name": "request_clarification",
                    "params": {
                        "similar_services": llm_response.get("service_groups", []),
                        "message": llm_response.get("message", "")
                    },
                    "params_meta": [],
                    # Campos específicos de clarificación
                    "similar_services": llm_response.get("service_groups", []),
                    "description": "Clarificación de servicios necesaria",
                    "reasoning": "Múltiples servicios similares detectados"
                }]
            
            # Caso 2: Plan de ejecución completo
            elif "execution_plan" in llm_response:
                execution_plan = llm_response["execution_plan"]
                
                # 🔍 DETAILED LOGGING: Log the raw LLM response for debugging
                self.logger.logger.info(f"🔍 RAW LLM RESPONSE: {json.dumps(llm_response, indent=2, default=str)}")
                
                # 🔍 DETAILED LOGGING: Log execution plan details
                self.logger.logger.info(f"🔍 EXECUTION PLAN RECEIVED: {len(execution_plan)} steps")
                for i, step in enumerate(execution_plan):
                    node_id = step.get("node_id")
                    action_id = step.get("action_id")
                    action_name = step.get("action_name", "unknown")
                    description = step.get("description", "")
                    self.logger.logger.info(f"🔍 Step {i+1}: node_id={node_id}, action_id={action_id}, action_name={action_name}")
                    self.logger.logger.info(f"🔍 Step {i+1} description: {description}")
                    step_params = step.get("parameters") or step.get("params", {})
                    if step_params:
                        self.logger.logger.info(f"🔍 Step {i+1} parameters: {json.dumps(step_params, indent=2)}")
                    
                    # Log node details from CAG context if available
                    if node_id and cag_context:
                        node_details = next((node for node in cag_context if node.get("node_id") == node_id), None)
                        if node_details:
                            self.logger.logger.info(f"🔍 Step {i+1} CAG match: {node_details.get('name', 'unknown')} (Provider: {node_details.get('provider', 'unknown')}, Type: {node_details.get('type', 'unknown')})")
                        else:
                            self.logger.logger.warning(f"⚠️ Step {i+1} node_id {node_id} NOT FOUND in CAG context!")
                
                # Validar y ordenar por step
                execution_plan.sort(key=lambda x: x.get("step", 0))
                
                # Procesar steps completos con parámetros
                selected_nodes = []
                for step in execution_plan:
                    step_type = step.get("type", "step")
                    
                    if step_type == "branch":
                        # Crear step de branch/condicional
                        branch_step = {
                            "step_type": "branch",
                            "execution_step": step.get("execution_step") or step.get("step"),
                            "condition": step.get("condition", "true"),
                            "next_on_true": step.get("next_on_true"),
                            "next_on_false": step.get("next_on_false"),
                            "description": step.get("description", "Conditional branch"),
                            "reasoning": step.get("reasoning", "Conditional logic")
                        }
                        selected_nodes.append(branch_step)
                    else:
                        # Crear step normal con parámetros completos
                        complete_step = self._create_action_step(step, cag_context, previous_workflow)
                        if complete_step:
                            selected_nodes.append(complete_step)
                
                # 🔍 DETAILED LOGGING: Final execution plan summary
                self.logger.logger.info(f"🔍 EXECUTION PLAN PROCESSING COMPLETE: {len(selected_nodes)} steps created")
                node_names = [step.get('node_name', 'unknown') for step in selected_nodes if step.get('step_type') == 'action']
                action_names = [step.get('action_name', 'unknown') for step in selected_nodes if step.get('step_type') == 'action']
                self.logger.logger.info(f"🔍 SELECTED NODES: {node_names}")
                self.logger.logger.info(f"🔍 SELECTED ACTIONS: {action_names}")
                
                return selected_nodes
        else:
            self.logger.log_warning("Kyra didn't return valid execution plan, using fallback")
            return self._create_fallback_plan(cag_context)
    
    def _create_action_step(
        self, 
        step: Dict[str, Any], 
        cag_context: List[Dict[str, Any]],
        previous_workflow: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Crea step de acción completo con metadata del CAG o previous_workflow
        PRIORIDAD: previous_workflow > cag_context > defaults
        Incluye tanto campos de traza como campos de ejecución
        """
        import uuid
        
        node_id = step.get("node_id")
        action_id = step.get("action_id")
        
        # 🔍 DETAILED LOGGING: Log step creation details
        self.logger.logger.info(f"🔍 CREATING ACTION STEP: node_id={node_id}, action_id={action_id}")
        self.logger.logger.info(f"🔍 RAW STEP DATA: {json.dumps(step, indent=2, default=str)}")
        
        # 🔍 EXHAUSTIVE TRACE: Log complete parameter state from LLM
        # 🔧 FIX: LLM sends both "parameters" and "params" - check both
        llm_params = step.get("parameters", {}) or step.get("params", {})
        llm_params_meta = step.get("params_meta", [])
        self.logger.logger.info(f"🔍 LLM PARAMS RECEIVED: {json.dumps(llm_params, indent=2, default=str)}")
        self.logger.logger.info(f"🔍 LLM PARAMS_META RECEIVED: {len(llm_params_meta)} metadata items")
        for idx, param_meta in enumerate(llm_params_meta):
            param_name = param_meta.get("name", "unknown")
            param_value = llm_params.get(param_name, "NOT_FOUND")
            self.logger.logger.info(f"🔍   Meta {idx+1}: {param_name} = '{param_value}' (type: {param_meta.get('type', 'unknown')})")
        
        # Validar que node_id y action_id no sean None
        if not node_id or not action_id:
            self.logger.log_warning(f"Step has invalid node_id ({node_id}) or action_id ({action_id}), using placeholders")
            node_id = node_id or str(uuid.uuid4())
            action_id = action_id or str(uuid.uuid4())
        
        # 🎯 PRIORITY: Use RAW STEP DATA from LLM if available (contains correct node_name)
        raw_node_name = step.get("node_name")
        raw_action_name = step.get("action_name")
        
        if raw_node_name and raw_node_name != "Unknown_Node":
            self.logger.logger.info(f"🎯 USING RAW STEP DATA: {raw_node_name} -> {raw_action_name}")
            # Create metadata from RAW STEP DATA
            node_metadata = {
                "name": raw_node_name,
                "use_case": step.get("use_case", ""),
                "default_auth": step.get("default_auth")
            }
            action_metadata = {
                "name": raw_action_name,
                "parameters": step.get("params_meta", [])
            }
        else:
            # Fallback: Encontrar el nodo en previous_workflow PRIMERO, luego en CAG context
            node_metadata = None
            action_metadata = None
        
        # 🧠 PRIORIDAD 1: Buscar en previous_workflow si está disponible (SOLO SI NO TENEMOS RAW DATA)
        if not node_metadata and previous_workflow and previous_workflow.get('steps'):
            self.logger.logger.info(f"🧠 CHECKING PREVIOUS_WORKFLOW: {len(previous_workflow.get('steps', []))} steps available")
            for prev_step in previous_workflow.get('steps', []):
                prev_node_id = prev_step.get('node_id')
                prev_action_id = prev_step.get('action_id')
                self.logger.logger.info(f"🧠 COMPARING: current({node_id}, {action_id}) vs previous({prev_node_id}, {prev_action_id})")
                
                if prev_node_id == node_id and prev_action_id == action_id:
                    # 🎯 MATCH FOUND: Always use RAW data over corrupted previous_workflow data
                    if raw_node_name and raw_node_name != "Unknown_Node":
                        self.logger.logger.info(f"🎯 UUID MATCH + RAW DATA: Using {raw_node_name} -> {raw_action_name} (ignoring corrupted previous_workflow)")
                        # Skip previous_workflow entirely when we have good RAW data
                        break
                    
                    # Validar que los metadatos están completos
                    node_name = prev_step.get('node_name')
                    action_name = prev_step.get('action_name')
                    
                    # 🔧 FIX: Accept any valid data, even if previous was corrupted to "Unknown_Node"
                    if node_name and action_name:
                        # Usar metadatos del workflow previo
                        node_metadata = {
                            "name": node_name,
                            "default_auth": prev_step.get('default_auth'),
                            "use_case": prev_step.get('use_case', '')
                        }
                        action_metadata = {
                            "name": action_name,
                            "parameters": prev_step.get('params_meta', [])
                        }
                        self.logger.logger.info(f"🧠 FOUND NODE IN PREVIOUS_WORKFLOW: {node_name} -> {action_name}")
                        break
                    else:
                        self.logger.log_warning(f"🧠 PREVIOUS_WORKFLOW step has incomplete metadata: node_name={node_name}, action_name={action_name}")
        
        # 🔧 UNIFICADO: ALWAYS search previous_workflow for default_auth even with RAW data
        previous_default_auth = None
        if node_metadata:
            self.logger.logger.info("🎯 USING RAW STEP DATA + enriching with previous_workflow default_auth")
            
            # Search for default_auth in previous_workflow even when using RAW data
            if previous_workflow and 'steps' in previous_workflow:
                for prev_step in previous_workflow['steps']:
                    prev_node_id = prev_step.get('node_id')
                    prev_action_id = prev_step.get('action_id') 
                    
                    # Match by IDs (most reliable)
                    if (str(prev_node_id) == str(node_id) and str(prev_action_id) == str(action_id)):
                        previous_default_auth = prev_step.get('default_auth')
                        if previous_default_auth:
                            self.logger.logger.info(f"🔧 UNIFICADO: Found previous default_auth={previous_default_auth} for {raw_node_name}")
                        break
        else:
            if previous_workflow:
                self.logger.logger.info(f"🧠 PREVIOUS_WORKFLOW provided but no steps: {previous_workflow.keys()}")
            else:
                self.logger.logger.info("🧠 NO PREVIOUS_WORKFLOW provided")
        
        # 🔍 PRIORIDAD 2: Si no encontrado en previous_workflow, buscar en CAG context
        if not node_metadata:
            # 🎯 PRIORITY: Search by RAW node_name first
            search_name = raw_node_name if raw_node_name and raw_node_name != "Unknown_Node" else node_id
            
            for node in cag_context:
                # Búsqueda por UUID exacto
                if node.get("node_id") == node_id:
                    node_metadata = node
                    self.logger.logger.info(f"🔍 FOUND NODE IN CAG BY ID: {node.get('name', 'unknown')} (provider: {node.get('provider', 'unknown')})")
                    break
                # 🎯 PRIORITY: Búsqueda por RAW node_name del LLM
                elif node.get("name") == search_name:
                    node_metadata = node
                    self.logger.logger.info(f"🎯 FOUND NODE IN CAG BY RAW NAME: {node.get('name', 'unknown')} -> {node.get('node_id')}")
                    break
                # ✅ FALLBACK: Búsqueda por nombre si UUID no funciona
                elif node.get("name") == node_id:
                    node_metadata = node
                    # Actualizar node_id con el UUID real
                    node_id = node.get("node_id")
                    self.logger.logger.info(f"🔍 FOUND NODE BY NAME: {node.get('name', 'unknown')} -> {node_id}")
                    break
                # ✅ FUZZY: Búsqueda más flexible
                elif node.get("name", "").replace("_", " ").lower() == search_name.replace("_", " ").lower():
                    node_metadata = node
                    node_id = node.get("node_id")
                    self.logger.logger.info(f"🔍 FOUND NODE BY FUZZY MATCH: {node.get('name', 'unknown')} -> {node_id}")
                    break
        
        # Buscar acción en el nodo encontrado (solo si no se encontró en previous_workflow)
        if node_metadata and not action_metadata:
            for action in node_metadata.get("actions", []):
                if action.get("action_id") == action_id:
                    action_metadata = action
                    self.logger.logger.info(f"🔍 FOUND ACTION IN NODE: {action.get('name', 'unknown')} (description: {action.get('description', 'no description')})")
                    break
                # ✅ FALLBACK: Búsqueda por nombre de acción
                elif action.get("name") == step.get("action_name"):
                    action_metadata = action
                    action_id = action.get("action_id")
                    self.logger.logger.info(f"🔍 FOUND ACTION BY NAME: {action.get('name', 'unknown')} -> {action_id}")
                    break
        
        
        if not node_metadata:
            # 🎯 LAST RESORT: Use RAW data if still no metadata found
            if raw_node_name and raw_node_name != "Unknown_Node":
                self.logger.logger.info(f"🎯 LAST RESORT: Using RAW node_name '{raw_node_name}' as fallback")
                node_metadata = {
                    "name": raw_node_name,
                    "default_auth": step.get("default_auth"),
                    "use_case": step.get("use_case", "")
                }
                if raw_action_name and not action_metadata:
                    action_metadata = {
                        "name": raw_action_name,
                        "parameters": step.get("params_meta", [])
                    }
            else:
                self.logger.log_warning(f"🔍 Node {node_id} not found in previous_workflow, CAG context, or metadata mapping - using defaults")
                # Crear metadata por defecto en lugar de retornar None
                node_metadata = {
                    "name": "Unknown_Node",
                    "default_auth": None,
                    "use_case": ""
                }
        else:
            # 🔍 DETAILED LOGGING: Log successful node resolution
            self.logger.logger.info(f"🔍 NODE RESOLUTION SUCCESS: {node_metadata.get('name')} -> {action_metadata.get('name') if action_metadata else 'unknown_action'}")
            
        # Crear step completo con campos de traza Y ejecución
        complete_step = {
            # === CAMPOS DE EJECUCIÓN (necesarios para motor real) ===
            "id": str(uuid.uuid4()),  # 🔥 REQUIRED: UUID para el workflow runner
            "step_type": "action",
            "execution_step": step.get("execution_step") or step.get("step"),
            "node_id": node_id,
            "action_id": action_id,
            "parameters": llm_params,  # Parámetros de Kyra (ya extraídos arriba)
            "params": llm_params,  # ✅ Campo requerido por DTO (alias)
            "params_meta": step.get("params_meta", []) or (action_metadata.get("parameters", []) if action_metadata else []),  # ✅ Priorizar params_meta del step
            "depends_on": step.get("depends_on", []),
            "default_auth": previous_default_auth or node_metadata.get("default_auth"),
            
            # === CAMPOS DE TRAZA (útiles para debugging/logging) ===
            # 🎯 PRIORITY: Use RAW STEP DATA over potentially corrupted metadata
            "node_name": raw_node_name or node_metadata.get("name") or "Unknown_Node",
            "action_name": raw_action_name or (action_metadata.get("name") if action_metadata else (step.get("action_name") or "unknown_action")),
            "description": step.get("description", ""),
            "reasoning": step.get("reasoning", ""),
            "use_case": node_metadata.get("use_case", ""),
            "parameters_metadata": action_metadata.get("parameters", []) if action_metadata else [],
            
            # === METADATA ADICIONAL ===
            "kyra_confidence": step.get("confidence", 0.8),
            "step_metadata": {
                "planned_by": "kyra",
                "selection_reasoning": step.get("reasoning", ""),
                "inferred_parameters": len([p for p, v in llm_params.items() if v is not None])
            }
        }
        
        # 🔍 DETAILED LOGGING: Log final step creation result
        self.logger.logger.info(f"🔍 STEP CREATED SUCCESSFULLY: {complete_step.get('node_name')} -> {complete_step.get('action_name')}")
        self.logger.logger.info(f"🔍 FINAL STEP SUMMARY: execution_step={complete_step.get('execution_step')}, parameters_count={len(complete_step.get('parameters', {}))}")
        
        # 🔍 EXHAUSTIVE TRACE: Log complete step state before returning
        final_params = complete_step.get("parameters", {})
        final_params_meta = complete_step.get("params_meta", [])
        final_default_auth = complete_step.get("default_auth")
        self.logger.logger.info(f"🔍 FINAL STEP PARAMS: {json.dumps(final_params, indent=2, default=str)}")
        self.logger.logger.info(f"🔍 FINAL STEP PARAMS_META: {len(final_params_meta)} metadata items")
        self.logger.logger.info(f"🔍 FINAL STEP DEFAULT_AUTH: {final_default_auth}")
        
        # 🔍 PARAMETER DIFF ANALYSIS: Compare input vs output
        missing_from_final = set(llm_params.keys()) - set(final_params.keys())
        added_to_final = set(final_params.keys()) - set(llm_params.keys())
        if missing_from_final:
            self.logger.logger.warning(f"🔍 PARAMS LOST: {missing_from_final}")
        if added_to_final:
            self.logger.logger.info(f"🔍 PARAMS ADDED: {added_to_final}")
        for param_name in set(llm_params.keys()) & set(final_params.keys()):
            llm_val = llm_params[param_name]
            final_val = final_params[param_name]
            if llm_val != final_val:
                self.logger.logger.warning(f"🔍 PARAM CHANGED: {param_name} = '{llm_val}' -> '{final_val}'")
        
        return complete_step
    
    def _create_fallback_plan(self, cag_context: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Plan de respaldo cuando Kyra no puede planificar
        """
        self.logger.log_warning("Creating fallback plan with first 2 nodes")
        
        import uuid
        fallback_nodes = []
        
        # Si no hay contexto CAG, crear step básico con UUIDs placeholder
        if not cag_context:
            fallback_step = {
                # Campos de ejecución
                "id": str(uuid.uuid4()),  # 🔥 REQUIRED: UUID para el workflow runner
                "step_type": "action",
                "execution_step": 1,
                "node_id": str(uuid.uuid4()),  # UUID placeholder
                "action_id": str(uuid.uuid4()),  # UUID placeholder
                "parameters": {},
                "params": {},  # ✅ Campo requerido por DTO
                "params_meta": [],  # ✅ Campo requerido por DTO (debe ser lista)
                "depends_on": [],
                "default_auth": None,
                
                # Campos de traza
                "node_name": "Fallback_Node",
                "action_name": "fallback_action",
                "description": "Fallback step - no CAG context available",
                "reasoning": "Fallback plan due to no available context",
                "use_case": "",
                
                # Metadata
                "kyra_confidence": 0.3,  # Baja confianza para fallback
                "step_metadata": {
                    "planned_by": "fallback",
                    "selection_reasoning": "No CAG context available",
                    "inferred_parameters": 0
                }
            }
            fallback_nodes.append(fallback_step)
            return fallback_nodes
        
        for i, node in enumerate(cag_context[:2]):  # Primeros 2 nodos
            # Asegurar que node_id y action_id no sean None
            node_id = node.get("node_id") or str(uuid.uuid4())
            actions = node.get("actions", [])
            action_id = (actions[0].get("action_id") if actions else None) or str(uuid.uuid4())
            
            fallback_step = {
                # Campos de ejecución
                "id": str(uuid.uuid4()),  # 🔥 REQUIRED: UUID para el workflow runner
                "step_type": "action",
                "execution_step": i + 1,
                "node_id": node_id,
                "action_id": action_id,
                "parameters": {},
                "params": {},  # ✅ Campo requerido por DTO
                "params_meta": [],  # ✅ Campo requerido por DTO (debe ser lista)
                "depends_on": [i] if i > 0 else [],
                "default_auth": node.get("default_auth"),
                
                # Campos de traza
                "node_name": node.get("name") or "Unknown_Node",
                "action_name": (actions[0].get("name") if actions else None) or "default_action",
                "description": f"Fallback step {i + 1}",
                "reasoning": "Fallback plan due to LLM planning failure",
                "use_case": node.get("use_case", ""),
                
                # Metadata
                "kyra_confidence": 0.3,  # Baja confianza para fallback
                "step_metadata": {
                    "planned_by": "fallback",
                    "selection_reasoning": "LLM planning failed",
                    "inferred_parameters": 0
                }
            }
            fallback_nodes.append(fallback_step)
        
        return fallback_nodes
    
    async def _add_auth_requirements_to_plan(self, execution_plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        SIMPLIFIED: Sin auth_matcher_v2 - delegar a UnifiedOAuthManager
        """
        try:
            # SIMPLIFIED: Solo retornar el plan sin modificaciones
            # UnifiedOAuthManager se encarga de auth requirements
            return execution_plan
            
        except Exception as e:
            self.logger.log_error(e, "adding auth requirements to plan")
            # En caso de error, retornar plan sin auth info
            return execution_plan
    
    def get_plan_summary(self, execution_plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Genera resumen del plan para logging/debugging
        """
        summary = {
            "total_steps": len(execution_plan),
            "action_steps": len([s for s in execution_plan if s.get("step_type") == "action"]),
            "branch_steps": len([s for s in execution_plan if s.get("step_type") == "branch"]),
            "nodes_involved": list(set([s.get("node_id") for s in execution_plan if s.get("node_id")])),
            "avg_confidence": sum([s.get("kyra_confidence", 0) for s in execution_plan]) / len(execution_plan) if execution_plan else 0,
            "parameters_with_values": sum([s.get("step_metadata", {}).get("inferred_parameters", 0) for s in execution_plan]),
            "reasoning_summary": [s.get("reasoning", "") for s in execution_plan[:3]]  # Primeros 3 reasonings
        }
        
        return summary

    async def modify_workflow(
        self,
        user_message: str,
        current_workflow: Dict[str, Any],
        cag_context: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Modifica un workflow existente basado en feedback del usuario.
        
        Args:
            user_message: Instrucciones de modificación del usuario
            current_workflow: Workflow actual con steps, metadata, etc.
            cag_context: CAG completo para referencia de nodos disponibles
            
        Returns:
            Modified workflow con steps actualizados
        """
        try:
            self.logger.logger.info(f"Modificando workflow: {user_message}")
            
            modification_prompt = self._build_modification_prompt(
                user_message, current_workflow, cag_context
            )
            
            llm_response = await self._call_llm_with_retry(modification_prompt)
            
            if isinstance(llm_response, dict) and "result" in llm_response:
                response_text = llm_response["result"]
            else:
                response_text = str(llm_response)
            
            # Parse la respuesta del LLM
            try:
                # Intentar parsear como JSON directo
                parsed_response = json.loads(response_text)
            except json.JSONDecodeError:
                # Si no es JSON válido, extraer JSON del texto
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    parsed_response = json.loads(json_match.group())
                else:
                    raise WorkflowProcessingException("No se pudo parsear la respuesta de modificación")
            
            # Validar estructura de respuesta
            if not isinstance(parsed_response, dict) or "steps" not in parsed_response:
                raise WorkflowProcessingException("Respuesta de modificación inválida")
            
            # Agregar metadata de modificación
            modified_workflow = {
                "steps": parsed_response["steps"],
                "confidence": parsed_response.get("confidence", current_workflow.get("confidence", 0.8)),
                "workflow_type": current_workflow.get("workflow_type") or "classic",
                "metadata": {
                    **current_workflow.get("metadata", {}),
                    "modified": True,
                    "modification_request": user_message,
                    "original_steps_count": len(current_workflow.get("steps", [])),
                    "new_steps_count": len(parsed_response["steps"])
                }
            }
            
            self.logger.logger.info(
                f"Workflow modificado: {len(parsed_response['steps'])} steps"
            )
            
            return modified_workflow
            
        except Exception as e:
            self.logger.log_error(e, "Workflow modification")
            # Retornar workflow original en caso de error
            return current_workflow

    def _build_modification_prompt(
        self,
        user_message: str,
        current_workflow: Dict[str, Any],
        cag_context: List[Dict[str, Any]]
    ) -> str:
        """
        Usa el prompt unificado pero con contexto de modificación.
        """
        # Agregar contexto de modificación al mensaje del usuario
        enhanced_message = """
MODIFICACIÓN DE WORKFLOW EXISTENTE:

WORKFLOW ACTUAL:
""" + json.dumps(current_workflow.get("steps", []), indent=2, ensure_ascii=False) + """

INSTRUCCIONES DEL USUARIO:
""" + user_message + """

Por favor modifica el workflow según las instrucciones, manteniendo la coherencia y formato existente.
"""
        
        # Usar el prompt unificado existente
        return self._build_unified_prompt(enhanced_message, cag_context, history=[], selected_services=None,
                                         discovery_results=None, previous_workflow=None,
                                         smart_forms_generated=None, oauth_completed_services=None, 
                                         user_inputs_provided=None)


# ===============================
# FACTORY PARA PLANNER UNIFICADO  
# ===============================

async def get_unified_workflow_planner(
    connector_client=None, 
    redis_client=None,
    cache_ttl=None
) -> LLMWorkflowPlanner:
    """
    Factory para crear LLMWorkflowPlanner unificado con dependencias opcionales
    
    Si no se proveen dependencias, se obtienen automáticamente para funcionalidad completa
    """
    # Obtener dependencias automáticamente si no se proveen
    
    if not connector_client:
        try:
            from app.connectors.connector_client import get_connector_client
            connector_client = get_connector_client()
        except Exception as e:
            logging.getLogger(__name__).warning(f"No se pudo obtener ConnectorClient: {e}")
    
    if not redis_client:
        try:
            from app.ai.llm_clients.llm_service import get_redis
            redis_client = get_redis()
        except Exception as e:
            logging.getLogger(__name__).warning(f"No se pudo obtener Redis: {e}")
    
    return LLMWorkflowPlanner(
        connector_client=connector_client,
        redis_client=redis_client,
        cache_ttl=cache_ttl
    )