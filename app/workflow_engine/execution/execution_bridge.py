"""
Execution Bridge - Convierte diseños de workflow a ejecución real
Extrae la lógica de bridge del workflow engine principal
"""
from typing import List, Dict, Any, Optional
from uuid import uuid4
from sqlalchemy.orm import Session
from ..core.interfaces import WorkflowCreationResult
from ..utils.workflow_logger import WorkflowLogger


class ExecutionBridge:
    """
    Puente entre diseño de workflow (Kyra) y ejecución real (WorkflowRunner)
    """
    
    def __init__(self, node_repo=None, action_repo=None, param_repo=None):
        self.logger = WorkflowLogger(__name__)
        # Opcional: repositorios inyectados para validación
        self.node_repo = node_repo
        self.action_repo = action_repo
        self.param_repo = param_repo
    
    async def execute_workflow_from_design(
        self,
        workflow_result: WorkflowCreationResult,
        user_id: int,
        db_session: Session,
        simulate: bool = False
    ) -> Dict[str, Any]:
        """
        Bridge principal: convierte diseño de WorkflowEngine a ejecución real
        
        Args:
            workflow_result: Resultado del WorkflowEngine (diseño de Kyra)
            user_id: ID del usuario
            db_session: Sesión de base de datos
            simulate: Si True, ejecuta en modo dry-run
            
        Returns:
            Resultado de ejecución real via WorkflowRunnerService
        """
        try:
            self.logger.logger.info(f"Converting workflow design to executable format (simulate={simulate})")
            
            # 1. Validar steps contra handlers reales
            validation_result = await self._validate_steps_against_handlers(
                workflow_result.steps, db_session
            )
            
            if not validation_result["is_valid"]:
                return {
                    "success": False,
                    "error": "Validation failed",
                    "validation_errors": validation_result["validation_errors"],
                    "steps_completed": 0
                }
            
            # 2. Convertir a formato ejecutable
            executable_steps = await self._convert_to_executable_format(
                validation_result["validated_steps"]
            )
            
            # 3. Configurar dependencias
            configured_steps = self._configure_step_dependencies(executable_steps)
            
            # 4. Ejecutar con WorkflowRunner
            execution_result = await self._execute_with_runner(
                configured_steps, user_id, simulate
            )
            
            return execution_result
            
        except Exception as e:
            self.logger.log_error(e, "workflow execution from design")
            return {
                "success": False,
                "error": str(e),
                "steps_completed": 0
            }
    
    async def _validate_steps_against_handlers(
        self,
        workflow_steps: List[Dict[str, Any]],
        db_session: Session
    ) -> Dict[str, Any]:
        """
        Valida que los steps generados por Kyra coincidan con handlers reales
        Centraliza lógica de WorkflowEngine._validate_llm_response_against_handlers
        """
        try:
            # ✅ REFACTORED: Usar repositorios inyectados o crear manualmente si no están disponibles
            if self.node_repo and self.action_repo and self.param_repo:
                node_repo = self.node_repo
                action_repo = self.action_repo
                param_repo = self.param_repo
            else:
                # Fallback para compatibilidad
                from app.repositories.node_repository import NodeRepository
                from app.repositories.action_repository import ActionRepository
                from app.repositories.parameter_repository import ParameterRepository
                
                node_repo = NodeRepository(db_session)
                action_repo = ActionRepository(db_session)
                param_repo = ParameterRepository(db_session)
            
            validation_errors = []
            validated_steps = []
            
            for step_idx, step in enumerate(workflow_steps):
                step_errors = []
                
                # 1. VALIDAR QUE EL NODO EXISTE
                node_id = step.get("node_id")
                if not node_id:
                    step_errors.append(f"Step {step_idx}: node_id es requerido")
                    continue
                
                node = await node_repo.get_by_id(node_id)
                if not node:
                    step_errors.append(f"Step {step_idx}: Nodo '{node_id}' no existe")
                    continue
                
                # 2. VALIDAR QUE LA ACCIÓN EXISTE
                action_id = step.get("action_id")
                if not action_id:
                    step_errors.append(f"Step {step_idx}: action_id es requerido")
                    continue
                
                action = await action_repo.get_by_id(action_id)
                if not action or action.node_id != node.node_id:
                    step_errors.append(f"Step {step_idx}: Acción '{action_id}' no existe para nodo '{node_id}'")
                    continue
                
                # 3. VALIDAR PARÁMETROS
                validation_errors_params = await self._validate_step_parameters(
                    step, action, param_repo, step_idx
                )
                step_errors.extend(validation_errors_params)
                
                # 4. CREAR STEP VALIDADO SI NO HAY ERRORES
                if not step_errors:
                    validated_step = await self._create_validated_step(step, node, action, param_repo)
                    validated_steps.append(validated_step)
                else:
                    validation_errors.extend(step_errors)
            
            return {
                "is_valid": len(validation_errors) == 0,
                "validation_errors": validation_errors,
                "validated_steps": validated_steps,
                "total_steps": len(workflow_steps),
                "valid_steps": len(validated_steps)
            }
            
        except Exception as e:
            self.logger.log_error(e, "step validation against handlers")
            return {
                "is_valid": False,
                "validation_errors": [f"Error interno de validación: {str(e)}"],
                "validated_steps": [],
                "total_steps": len(workflow_steps),
                "valid_steps": 0
            }
    
    async def _validate_step_parameters(
        self,
        step: Dict[str, Any],
        action,
        param_repo,
        step_idx: int
    ) -> List[str]:
        """Valida parámetros de un step específico"""
        step_errors = []
        
        llm_params = step.get("parameters", {})
        required_params = await param_repo.list_parameters(action.action_id)
        
        missing_required = []
        invalid_params = []
        
        for param in required_params:
            param_name = param.name
            param_value = llm_params.get(param_name)
            
            # Validar parámetros requeridos
            if param.required and (param_value is None or param_value == ""):
                missing_required.append(param_name)
            
            # Validar tipos básicos
            if param_value is not None and param.param_type:
                param_type = getattr(param.param_type, "value", str(param.param_type))
                type_error = self._validate_parameter_type(param_name, param_value, param_type)
                if type_error:
                    invalid_params.append(type_error)
        
        if missing_required:
            step_errors.append(f"Step {step_idx}: Parámetros requeridos faltantes: {', '.join(missing_required)}")
        
        if invalid_params:
            step_errors.append(f"Step {step_idx}: Parámetros inválidos: {', '.join(invalid_params)}")
        
        return step_errors
    
    def _validate_parameter_type(self, param_name: str, param_value: Any, param_type: str) -> Optional[str]:
        """Valida el tipo de un parámetro específico"""
        if param_type == "number" and not isinstance(param_value, (int, float)):
            try:
                float(param_value)  # Intentar convertir
            except (ValueError, TypeError):
                return f"{param_name} debe ser numérico"
        
        elif param_type == "boolean" and not isinstance(param_value, bool):
            if str(param_value).lower() not in ["true", "false", "1", "0"]:
                return f"{param_name} debe ser booleano"
        
        return None
    
    async def _create_validated_step(self, step: Dict[str, Any], node, action, param_repo) -> Dict[str, Any]:
        """Crea step validado con metadata completa"""
        required_params = await param_repo.list_parameters(action.action_id)
        
        return {
            **step,
            "node_id": str(node.node_id),
            "action_id": str(action.action_id),
            "parameters_metadata": [
                {
                    "name": p.name,
                    "description": p.description or "",
                    "required": p.required,
                    "type": getattr(p.param_type, "value", str(p.param_type)),
                    "param_id": str(p.param_id)
                } for p in required_params
            ]
        }
    
    async def _convert_to_executable_format(
        self,
        validated_steps: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convierte steps validados a formato ejecutable
        """
        executable_steps = []
        
        for step_data in validated_steps:
            step_type = step_data.get("step_type", "action")
            step_id = str(uuid4())
            
            if step_type == "branch":
                # Crear branch step
                executable_step = {
                    "id": step_id,
                    "type": "branch",
                    "condition": step_data.get("condition", "true"),
                    "next_on_true": step_data.get("next_on_true"),
                    "next_on_false": step_data.get("next_on_false"),
                    "execution_step": step_data.get("execution_step")
                }
            else:
                # Crear action step
                executable_step = {
                    "id": step_id,
                    "type": "action",
                    "node_id": step_data.get("node_id"),
                    "action_id": step_data.get("action_id"),
                    "node_name": step_data.get("node_name"),
                    "action_name": step_data.get("action_name"),
                    "parameters": step_data.get("parameters", {}),
                    "execution_step": step_data.get("execution_step"),
                    "depends_on": step_data.get("depends_on", []),
                    "default_auth": step_data.get("default_auth")
                }
            
            executable_steps.append(executable_step)
        
        return executable_steps
    
    def _configure_step_dependencies(
        self,
        executable_steps: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Configura dependencias entre steps
        Centraliza lógica de WorkflowEngine._configure_step_dependencies
        """
        try:
            # Crear mapeo de execution_step a step_id
            step_mapping = {}
            for step in executable_steps:
                exec_step = step.get("execution_step")
                if exec_step is not None:
                    step_mapping[exec_step] = step["id"]
            
            # Configurar dependencias usando step_ids reales
            for step in executable_steps:
                depends_on_steps = step.get("depends_on", [])
                if depends_on_steps:
                    # Convertir números de step a step_ids
                    dependency_ids = []
                    for dep_step in depends_on_steps:
                        if dep_step in step_mapping:
                            dependency_ids.append(step_mapping[dep_step])
                        else:
                            self.logger.log_warning(f"Dependency step {dep_step} not found for step {step['id']}")
                    
                    step["dependencies"] = dependency_ids
                else:
                    step["dependencies"] = []
            
            return executable_steps
            
        except Exception as e:
            self.logger.log_error(e, "step dependencies configuration")
            return executable_steps
    
    async def _execute_with_runner(
        self,
        configured_steps: List[Dict[str, Any]],
        user_id: int,
        simulate: bool
    ) -> Dict[str, Any]:
        """
        Ejecuta steps usando WorkflowRunnerService
        """
        try:
            from app.services.workflow_runner_service import WorkflowRunnerService
            
            runner = WorkflowRunnerService()
            
            # Preparar metadata de ejecución
            execution_metadata = {
                "user_id": user_id,
                "simulate": simulate,
                "total_steps": len(configured_steps),
                "execution_type": "workflow_engine_bridge"
            }
            
            # Ejecutar workflow
            if simulate:
                # Modo dry-run
                result = await runner.simulate_workflow(
                    steps=configured_steps,
                    user_id=user_id,
                    metadata=execution_metadata
                )
            else:
                # Ejecución real
                result = await runner.execute_workflow(
                    steps=configured_steps,
                    user_id=user_id,
                    metadata=execution_metadata
                )
            
            return result
            
        except Exception as e:
            self.logger.log_error(e, "workflow execution with runner")
            return {
                "success": False,
                "error": f"Error executing with runner: {str(e)}",
                "steps_completed": 0
            }
    
    def get_execution_summary(
        self,
        workflow_result: WorkflowCreationResult,
        execution_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Genera resumen de ejecución para logging/debugging
        """
        return {
            "design_summary": {
                "workflow_type": workflow_result.workflow_type.value,
                "total_steps_designed": len(workflow_result.steps),
                "oauth_requirements": len(workflow_result.oauth_requirements),
                "confidence": workflow_result.confidence.value
            },
            "execution_summary": {
                "success": execution_result.get("success", False),
                "steps_completed": execution_result.get("steps_completed", 0),
                "execution_time": execution_result.get("execution_time"),
                "errors": len(execution_result.get("errors", []))
            },
            "bridge_metrics": {
                "conversion_success": execution_result.get("success", False),
                "validation_passed": execution_result.get("validation_passed", True),
                "steps_converted": execution_result.get("steps_completed", 0)
            }
        }