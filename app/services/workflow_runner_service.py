# app/services/workflow_runner_service.py

import logging
import time
import asyncio
import sys
from typing import List, Dict, Any, Tuple, Union
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.mcp.mcp_client import MCPClient

# Interface removed - using concrete class
from app.services.flow_execution_service import FlowExecutionService
from app.services.flow_validator_service import FlowValidatorService
from app.services.flow_execution_service import get_flow_execution_service
from app.services.flow_validator_service import get_flow_validator_service
from app.services.credential_service import CredentialService, get_credential_service
from app.connectors.factory import execute_node
from app.dtos.step_meta_dto import StepMetaDTO
from app.dtos.branch_step_dto import BranchStepDTO
from app.dtos.step_result_dto import StepResultDTO
from app.dtos.workflow_result_dto import WorkflowResultDTO

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class WorkflowRunnerService:
    """
    Servicio de ejecución de workflows con:
      - Lazy-start de MCP server
      - Dry-run (simulate=True)
      - Retries y back-off
      - Timeout por paso
      - Validación de pasos
    """

    def __init__(
        self,
        flow_exec_svc: FlowExecutionService,
        credential_service: CredentialService,
        validator: FlowValidatorService
    ):
        self.flow_exec_svc = flow_exec_svc
        self.credential_service = credential_service
        self._validator = validator
        self.logger = logging.getLogger(__name__)  # ✅ FIX: Add missing logger attribute
        self._mcp_client = MCPClient(
            command=sys.executable,
            args=["app/handlers/tools/mcp_tools.py"]
        )
        self._mcp_started = False

    async def _ensure_mcp_server_started(self):
        """
        Ensures MCP client can connect to the STDIO-based MCP server.
        MCP server spawns automatically when client connects via STDIO transport.
        """
        if not self._mcp_started:
            self._mcp_started = True
            try:
                # MCP server auto-spawns via STDIO when client connects
                # Test connection by listing available tools
                tools_result = await self._mcp_client.list_tools()
                tool_count = len(tools_result.tools) if hasattr(tools_result, 'tools') else 0
                logger.info(f"MCP STDIO connection established successfully. Found {tool_count} tools.")
            except Exception as e:
                logger.error(f"Failed to establish MCP STDIO connection: {e}")
                raise RuntimeError(f"No se pudo conectar al servidor MCP via STDIO: {e}")

    async def run_workflow(
        self,
        flow_id: UUID,
        steps: List[Dict[str, Any]],
        user_id: int,
        inputs: Dict[str, Any],
        simulate: bool = False
    ) -> Tuple[UUID, WorkflowResultDTO]:
        
        # 🔍 EXHAUSTIVE TRACE: Log complete workflow state at runner entry
        import json
        self.logger.info(f"🔍 WORKFLOW RUNNER ENTRY: flow_id={flow_id}, user_id={user_id}, simulate={simulate}")
        self.logger.info(f"🔍 WORKFLOW RUNNER STEPS COUNT: {len(steps)} steps received")
        self.logger.info(f"🔍 WORKFLOW RUNNER INPUTS: {json.dumps(inputs, indent=2, default=str)}")
        
        for idx, step in enumerate(steps):
            step_params = step.get("params", {})
            step_parameters = step.get("parameters", {})
            step_default_auth = step.get("default_auth")
            step_node_name = step.get("node_name", "unknown")
            step_action_name = step.get("action_name", "unknown")
            
            self.logger.info(f"🔍 RUNNER STEP {idx+1} ({step_node_name}.{step_action_name}):")
            self.logger.info(f"🔍   params: {json.dumps(step_params, indent=2, default=str)}")
            self.logger.info(f"🔍   parameters: {json.dumps(step_parameters, indent=2, default=str)}")  
            self.logger.info(f"🔍   default_auth: {step_default_auth}")
            self.logger.info(f"🔍   id: {step.get('id')}")
            self.logger.info(f"🔍   node_id: {step.get('node_id')}")
            self.logger.info(f"🔍   action_id: {step.get('action_id')}")
        
        # 🔧 Fix: Asegurar que start_id no sea None
        first_step = steps[0] if steps else {}
        start_id = first_step.get("id")
        if start_id is None:
            self.logger.error(f"❌ WORKFLOW VALIDATION: First step has no ID. Step: {first_step}")
            raise ValueError(f"El primer step del workflow no tiene ID válido. Step: {first_step}")
        
        await self._validator.validate_flow_spec({"start_id": start_id, "steps": steps})
        # Convertir a modelos y construir mapa por id
        step_models: Dict[UUID, Union[StepMetaDTO, BranchStepDTO]] = {}
        for step in steps:
            if step.get("type") == "branch":
                model = BranchStepDTO(**step)
            else:
                model = StepMetaDTO(**step)
            step_models[model.id] = model
        await self._validator.validate_steps([s for s in step_models.values() if isinstance(s, StepMetaDTO)])

        # Registrar inicio en BD
        exec_dto = await self.flow_exec_svc.start_execution(flow_id=flow_id, inputs=inputs)
        execution_id = exec_dto.execution_id
        logger.info(f"Workflow {flow_id} iniciado (execution_id={execution_id}), simulate={simulate}")

        results: List[StepResultDTO] = []
        outputs: Dict[UUID, Any] = {}
        current_id = steps[0].get("id")
        idx = 0
        while current_id is not None:
            step = step_models[current_id]
            if isinstance(step, BranchStepDTO):
                try:
                    cond = eval(step.condition, {}, outputs)
                except Exception:
                    cond = False
                logger.info(f"Branch {step.id} evaluada como {cond}")
                current_id = step.next_on_true if cond else step.next_on_false
                continue

            idx += 1
            logger.info(f"Paso {idx}: {step.node_name}.{step.action_name}")
            creds = {}
            if step.default_auth and not simulate:
                # ✅ AGNÓSTICO: Convertir default_auth a service_id
                service_id = await self._extract_service_id_from_default_auth(step.default_auth)
                if service_id:
                    # Use refactored CredentialService with service_id
                    raw_creds = await self.credential_service.get_credential(user_id, service_id)
                    if not raw_creds:
                        raise RuntimeError(f"Credenciales no disponibles para service_id '{service_id}' (default_auth: '{step.default_auth}')")
                    
                    # 🧹 CLEAN: Remove SQLAlchemy metadata before passing to handlers
                    creds = self._clean_credentials(raw_creds)

            attempt = 0
            exec_res: Dict[str, Any] = {}

            while True:
                start_call = time.perf_counter()

                try:
                    # Resolver templates en parámetros antes de ejecutar
                    from app.utils.template_engine import template_engine
                    context = template_engine.build_context_from_outputs(outputs)
                    resolved_params = template_engine.resolve_template_in_params(step.params, context)
                    
                    # 🔧 FIX 1: Ensure all UUIDs are converted to strings (SAME AS execute_workflow_steps)
                    def serialize_uuids_in_params(obj):
                        """Recursively convert UUID objects to strings for handler compatibility"""
                        from uuid import UUID
                        if isinstance(obj, UUID):
                            return str(obj)
                        elif isinstance(obj, dict):
                            return {k: serialize_uuids_in_params(v) for k, v in obj.items()}
                        elif isinstance(obj, list):
                            return [serialize_uuids_in_params(item) for item in obj]
                        return obj

                    resolved_params = serialize_uuids_in_params(resolved_params)
                    
                    # 🔧 VALIDATION: Check for empty parameters  
                    if not resolved_params or all(v is None or v == "" or v == {} for v in resolved_params.values()):
                        self.logger.warning(f"⚠️ EMPTY PARAMS: Step {step.node_name}.{step.action_name} has no valid parameters")
                        self.logger.debug(f"🔍 RAW PARAMS: {step.params}")
                        self.logger.debug(f"🔍 RESOLVED PARAMS: {resolved_params}")
                    
                    # Log parameter details for debugging
                    self.logger.debug(f"🔍 EXECUTION PARAMS: {resolved_params}")
                    self.logger.debug(f"🔍 PARAM TYPES: {[(k, type(v).__name__) for k, v in resolved_params.items()]}")
                    
                    # Ejecutar nodo (real o simulado)
                    exec_res = await execute_node(
                        step.node_name,
                        step.action_name,
                        resolved_params,
                        creds,
                        simulate=simulate
                    )
                    break

                except Exception as e:
                    duration_ms = int((time.perf_counter() - start_call) * 1000)
                    if attempt >= step.retries:
                        exec_res = {"status": "error", "output": None, "error": str(e), "duration_ms": duration_ms}
                        break
                    await asyncio.sleep(2 ** attempt)
                    attempt += 1

            step_dto = StepResultDTO(
                node_id=step.node_id,
                action_id=step.action_id,
                status=exec_res["status"],
                output=exec_res.get("output"),
                error=exec_res.get("error"),
                duration_ms=exec_res["duration_ms"],
            )
            results.append(step_dto)
            outputs[step.id] = step_dto.output
            if step_dto.status != "success":
                break
            current_id = step.next

        # Finalizar en BD
        overall_status = "success" if all(r.status == "success" for r in results) else "failure"
        outputs_map = {str(r.node_id): r.output for r in results}  # 🔧 Convert UUID to string for JSONB
        error_msg = None if overall_status == "success" else results[-1].error
        try:
            await self.flow_exec_svc.finish_execution(execution_id, overall_status, outputs_map, error_msg)
        except Exception as e:
            logger.error(f"Error finalizando en BD: {e}")

        return execution_id, WorkflowResultDTO(steps=results, overall_status=overall_status)
    
    async def execute_workflow_steps(
        self,
        steps: List[Dict[str, Any]],
        user_id: int,
        inputs: Dict[str, Any],
        simulate: bool = False,
        flow_id: UUID = None
    ) -> Tuple[UUID, WorkflowResultDTO]:
        """
        🔧 NEW METHOD: Ejecuta steps en formato workflow engine directamente
        sin validación de flows guardados. Para workflows temporales.
        
        Args:
            steps: Steps en formato workflow engine (Dict, no StepMetaDTO)
            user_id: ID del usuario
            inputs: Inputs del workflow
            simulate: Si es simulación
            flow_id: ID del flow (None para workflows temporales)
        
        Returns:
            Tuple con execution_id y resultado
        """
        if not steps:
            raise ValueError("No hay steps para ejecutar")
        
        # Para workflows temporales, generar UUID temporal
        if flow_id is None:
            from uuid import uuid4
            flow_id = uuid4()
        
        # 🔧 WORKFLOW ENGINE FORMAT: Validación mínima sin conversión a DTOs
        self.logger.info(f"🚀 EXECUTING WORKFLOW STEPS: {len(steps)} steps, simulate={simulate}")
        
        # 🔧 NO MCP NEEDED: Regular workflows use connectors, not MCP tools
        
        # Registrar inicio en BD - Para workflows temporales usar flow_id temporal
        exec_dto = await self.flow_exec_svc.start_execution(flow_id=flow_id, inputs=inputs)
        execution_id = exec_dto.execution_id
        logger.info(f"Temporary workflow {flow_id} iniciado (execution_id={execution_id}), simulate={simulate}")

        results: List[StepResultDTO] = []
        outputs: Dict[str, Any] = {}
        
        # 🔧 WORKFLOW ENGINE FORMAT: Ejecutar steps secuencialmente
        for idx, step_dict in enumerate(steps):
            step_id = step_dict.get("id", f"step_{idx}")
            node_name = step_dict.get("node_name", "unknown")
            action_name = step_dict.get("action_name", "unknown_action")
            params = step_dict.get("params", {})
            default_auth = step_dict.get("default_auth")
            retries = step_dict.get("retries", 0)
            node_id = step_dict.get("node_id", step_id)
            action_id = step_dict.get("action_id", step_id)
            
            # 🔍 END-TO-END TRACE: Log what arrives at runner
            self.logger.info(f"🔍 E2E TRACE RUNNER: Step {idx + 1} ({node_name}.{action_name}) default_auth = {default_auth}")
            self.logger.info(f"Paso {idx + 1}: {node_name}.{action_name}")
            
            # 🔧 CREDENTIALS: Obtener credenciales si son necesarias
            creds = {}
            if default_auth and not simulate:
                service_id = await self._extract_service_id_from_default_auth(default_auth)
                if service_id:
                    # Use refactored CredentialService with service_id
                    raw_creds = await self.credential_service.get_credential(user_id, service_id)
                    if not raw_creds:
                        raise RuntimeError(f"Credenciales no disponibles para service_id '{service_id}' (default_auth: '{default_auth}')")
                    
                    # 🧹 CLEAN: Remove SQLAlchemy metadata before passing to handlers
                    creds = self._clean_credentials(raw_creds)

            # 🔧 EXECUTION: Ejecutar step con retries
            attempt = 0
            exec_res: Dict[str, Any] = {}

            while True:
                start_call = time.perf_counter()

                try:
                    # Resolver templates en parámetros
                    from app.utils.template_engine import template_engine
                    context = template_engine.build_context_from_outputs(outputs)
                    resolved_params = template_engine.resolve_template_in_params(params, context)
                    
                    # 🔧 FIX 1: Ensure all UUIDs are converted to strings
                    def serialize_uuids_in_params(obj):
                        """Recursively convert UUID objects to strings for handler compatibility"""
                        from uuid import UUID
                        if isinstance(obj, UUID):
                            return str(obj)
                        elif isinstance(obj, dict):
                            return {k: serialize_uuids_in_params(v) for k, v in obj.items()}
                        elif isinstance(obj, list):
                            return [serialize_uuids_in_params(item) for item in obj]
                        return obj

                    resolved_params = serialize_uuids_in_params(resolved_params)
                    
                    # 🔧 VALIDATION: Check for empty parameters  
                    if not resolved_params or all(v is None or v == "" or v == {} for v in resolved_params.values()):
                        self.logger.warning(f"⚠️ EMPTY PARAMS: Step {node_name}.{action_name} has no valid parameters")
                        self.logger.debug(f"🔍 RAW PARAMS: {params}")
                        self.logger.debug(f"🔍 RESOLVED PARAMS: {resolved_params}")
                    
                    # Log parameter details for debugging
                    self.logger.debug(f"🔍 EXECUTION PARAMS: {resolved_params}")
                    self.logger.debug(f"🔍 PARAM TYPES: {[(k, type(v).__name__) for k, v in resolved_params.items()]}")
                    
                    # Ejecutar nodo
                    exec_res = await execute_node(
                        node_name,
                        action_name,
                        resolved_params,
                        creds,
                        simulate=simulate
                    )
                    break

                except Exception as e:
                    duration_ms = int((time.perf_counter() - start_call) * 1000)
                    if attempt >= retries:
                        exec_res = {"status": "error", "output": None, "error": str(e), "duration_ms": duration_ms}
                        break
                    await asyncio.sleep(2 ** attempt)
                    attempt += 1

            # 🔧 RESULTS: Guardar resultado
            step_dto = StepResultDTO(
                node_id=node_id,
                action_id=action_id,
                status=exec_res["status"],
                output=exec_res.get("output"),
                error=exec_res.get("error"),
                duration_ms=exec_res["duration_ms"],
            )
            results.append(step_dto)
            outputs[step_id] = step_dto.output
            
            # Si hay error, parar ejecución
            if step_dto.status != "success":
                self.logger.error(f"❌ Step {idx + 1} failed: {step_dto.error}")
                break

        # Finalizar en BD
        overall_status = "success" if all(r.status == "success" for r in results) else "failure"
        outputs_map = {str(r.node_id): r.output for r in results}  # 🔧 Convert UUID to string for JSONB
        error_msg = None if overall_status == "success" else results[-1].error if results else "No steps executed"
        
        try:
            await self.flow_exec_svc.finish_execution(execution_id, overall_status, outputs_map, error_msg)
        except Exception as e:
            logger.error(f"Error finalizando en BD: {e}")

        self.logger.info(f"✅ Workflow execution completed: {overall_status}, {len(results)} steps")
        return execution_id, WorkflowResultDTO(steps=results, overall_status=overall_status)
    
    async def _extract_service_id_from_default_auth(self, default_auth: str) -> str:
        """
        ✅ AGNÓSTICO: Convierte default_auth legacy a service_id
        
        Args:
            default_auth: String legacy como "oauth2_google_gmail"
            
        Returns:
            service_id como "gmail"
        """
        self.logger.info(f"🔍 EXTRACTING SERVICE_ID: Input default_auth='{default_auth}'")
        
        if not default_auth:
            self.logger.warning(f"🔍 EXTRACTING SERVICE_ID: Empty default_auth, returning empty string")
            return ""
        
        # Remove mechanism prefix if present
        for prefix in ["oauth2_", "api_key_", "bot_token_", "db_credentials_"]:
            if default_auth.startswith(prefix):
                extracted = default_auth[len(prefix):]
                self.logger.info(f"🔍 EXTRACTING SERVICE_ID: Found prefix '{prefix}', extracted='{extracted}'")
                return extracted
        
        # If no prefix, assume it's already the service_id
        self.logger.info(f"🔍 EXTRACTING SERVICE_ID: No prefix found, using as-is='{default_auth}'")
        return default_auth
    
    def _clean_credentials(self, raw_creds: Dict[str, Any]) -> Dict[str, Any]:
        """
        🧹 CLEAN: Extract only Google OAuth2 credential fields from raw credentials
        
        Args:
            raw_creds: Raw credentials dict from credential_service (contains DB fields)
            
        Returns:
            Clean credentials dict with only OAuth2 fields for Google APIs
        """
        if not raw_creds:
            return {}
        
        # 🔍 DEBUG: Log raw credential structure
        self.logger.info(f"🔍 RAW CREDENTIALS KEYS: {list(raw_creds.keys())}")
        self.logger.info(f"🔍 RAW access_token: {'present' if raw_creds.get('access_token') else 'missing'}")
        self.logger.info(f"🔍 RAW refresh_token: {'present' if raw_creds.get('refresh_token') else 'missing'}")
        self.logger.info(f"🔍 RAW client_id: {'present' if raw_creds.get('client_id') else 'missing'}")
        self.logger.info(f"🔍 RAW client_secret: {'present' if raw_creds.get('client_secret') else 'missing'}")
        
        # Extract OAuth2 fields for Google Credentials, including config fields
        config = raw_creds.get('config', {}) if isinstance(raw_creds.get('config'), dict) else {}
        self.logger.info(f"🔍 CONFIG KEYS: {list(config.keys()) if config else 'no config'}")
        if config:
            self.logger.info(f"🔍 CONFIG client_id: {'present' if config.get('client_id') else 'missing'}")
            self.logger.info(f"🔍 CONFIG client_secret: {'present' if config.get('client_secret') else 'missing'}")
            self.logger.info(f"🔍 CONFIG token_uri: {'present' if config.get('token_uri') else 'missing'}")
        
        oauth2_fields = {
            'token': raw_creds.get('access_token'),
            'refresh_token': raw_creds.get('refresh_token'),
            'id_token': raw_creds.get('id_token') or config.get('id_token'),
            'token_uri': config.get('token_uri', 'https://oauth2.googleapis.com/token'),
            'client_id': raw_creds.get('client_id') or config.get('client_id'),
            'client_secret': raw_creds.get('client_secret') or config.get('client_secret'),
            'scopes': raw_creds.get('scopes')
        }
        
        # Remove None values
        clean_creds = {k: v for k, v in oauth2_fields.items() if v is not None}
        
        self.logger.info(f"🧹 FINAL CLEAN CREDS KEYS: {list(clean_creds.keys())}")
        self.logger.debug(f"🧹 CLEANED CREDENTIALS: Extracted {len(clean_creds)} OAuth2 fields from {len(raw_creds)} raw fields")
        return clean_creds

async def get_workflow_runner(
    flow_exec_svc: FlowExecutionService = Depends(get_flow_execution_service),
    credential_service: CredentialService = Depends(get_credential_service),
    validator: FlowValidatorService = Depends(get_flow_validator_service),
) -> WorkflowRunnerService:
    return WorkflowRunnerService(flow_exec_svc, credential_service, validator)

async def create_workflow_runner_manual(db_session: AsyncSession) -> WorkflowRunnerService:
    """
    🔧 MANUAL CREATION: Crear WorkflowRunnerService sin Depends para uso fuera de FastAPI
    """
    from app.repositories.flow_execution_repository import FlowExecutionRepository
    from app.services.flow_execution_service import FlowExecutionService
    from app.services.credential_service import CredentialService
    from app.services.flow_validator_service import FlowValidatorService
    
    # Crear instancias manualmente con la sesión de BD real
    repo = FlowExecutionRepository(db_session)
    flow_exec_svc = FlowExecutionService(repo)
    
    # 🔧 FIX: CredentialService needs CredentialRepository, not AsyncSession
    from app.repositories.credential_repository import CredentialRepository
    credential_repo = CredentialRepository(db_session)
    credential_service = CredentialService(credential_repo)
    
    validator = FlowValidatorService()
    
    return WorkflowRunnerService(flow_exec_svc, credential_service, validator)

