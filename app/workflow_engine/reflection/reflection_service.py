"""
Reflection Service - Fuente de verdad única para lógica de reflexión
Centraliza toda la lógica distribuida: ReflectHandler, WorkflowEngine, ChatService, KyraAgentService
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from ..core.interfaces import WorkflowCreationResult
from ..utils.workflow_logger import WorkflowLogger


class ReflectionService:
    """
    Servicio centralizado para ciclo Plan → Act → Reflect → Iterate
    Fuente de verdad única que reemplaza lógica duplicada
    """
    
    def __init__(self, llm_service=None):
        self.logger = WorkflowLogger(__name__)
        self.reflect_interval = 3  # Reflexiona cada 3 pasos
        self.max_iterations = 2    # Máximo iteraciones por default - prevenir loops
        # ✅ FIX: Usar LLM service inyectado que ya tiene CAG context
        self.llm_service = llm_service
        if llm_service:
            self.logger.logger.info("✅ ReflectionService initialized with SHARED LLM instance (preserves CAG context)")
        else:
            self.logger.logger.warning("⚠️ ReflectionService initialized WITHOUT shared LLM - will create separate instance")
    
    async def execute_workflow_with_reflection(
        self,
        workflow_result: WorkflowCreationResult,
        user_message: str,
        user_id: int,
        session_id: UUID,
        max_iterations: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Loop principal: Plan → Act → Reflect → Iterate
        Centraliza lógica de ChatService._execute_workflow_with_reflection
        
        Returns:
            Resultado final con historial de reflexiones
        """
        max_iter = max_iterations or self.max_iterations
        execution_history = []
        
        self.logger.logger.info(f"Starting reflection loop: max_iterations={max_iter}")
        
        for iteration in range(max_iter):
            self.logger.logger.info(f"🔄 Iteration {iteration + 1}/{max_iter}")
            
            # 1. ACT - Ejecutar workflow steps (simular en primeras iteraciones para rapidez)
            # 🆕 Usar fake data en las primeras iteraciones, ejecutar real solo en la última
            should_simulate = iteration < max_iter - 1  # Simular todas excepto la última
            
            if should_simulate:
                self.logger.logger.info(f"🎭 Using simulation for iteration {iteration + 1} (fast iteration)")
            else:
                self.logger.logger.info(f"⚡ Using real execution for final iteration {iteration + 1}")
            
            execution_result = await self._execute_workflow_steps(
                workflow_result.steps, 
                user_id, 
                {"iteration": iteration + 1},
                simulate=should_simulate
            )
            
            execution_history.append({
                "iteration": iteration + 1,
                "execution_result": execution_result,
                "steps_executed": len(workflow_result.steps)
            })
            
            # 2. REFLECT - Evaluar resultados
            reflection_result = await self._reflect_on_execution(
                goal=user_message,
                execution_history=execution_history,
                current_result=execution_result
            )
            
            # 3. DECIDE - ¿Satisfactorio o continuar?
            is_satisfactory = self._is_result_satisfactory(reflection_result, execution_result)
            
            if is_satisfactory or iteration == max_iter - 1:
                self.logger.logger.info(f"✅ Workflow completed after {iteration + 1} iterations")
                return {
                    "final_result": execution_result,
                    "reflection_analysis": reflection_result,
                    "execution_history": execution_history,
                    "iterations": iteration + 1,
                    "status": "completed" if is_satisfactory else "max_iterations_reached"
                }
            
            # 4. RE-PLAN - Refinar workflow basado en reflexión
            try:
                refined_steps = await self._refine_workflow_from_reflection(
                    goal=user_message,
                    reflection_result=reflection_result,
                    execution_history=execution_history,
                    original_steps=workflow_result.steps  # ✅ Pasar steps originales para conservar UUIDs
                )
                
                # Actualizar workflow para siguiente iteración
                workflow_result.steps = refined_steps
                self.logger.logger.info(f"🔄 Workflow refined: {len(refined_steps)} steps for next iteration")
                
            except Exception as e:
                self.logger.log_error(e, f"workflow refinement iteration {iteration + 1}")
                break
        
        return {
            "final_result": execution_history[-1]["execution_result"] if execution_history else {},
            "execution_history": execution_history,
            "iterations": len(execution_history),
            "status": "max_iterations_reached"
        }
    
    async def execute_workflow_with_smart_iteration(
        self,
        workflow_result: WorkflowCreationResult,
        user_message: str,
        user_id: int,
        simulate_first: bool = True,
        max_iterations: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        🆕 NUEVO: Ejecución inteligente con fake data para iteración rápida
        
        Flujo optimizado:
        1. Simulación con fake data para validación rápida (si simulate_first=True)
        2. Reflexión e iteración basada en datos simulados
        3. Ejecución real solo en la iteración final o cuando sea satisfactorio
        
        Args:
            simulate_first: Si True, usa fake data en primeras iteraciones
            max_iterations: Máximo de iteraciones (default: self.max_iterations)
            
        Returns:
            Resultado con ejecución optimizada y detalles de simulación/real
        """
        try:
            max_iter = max_iterations or self.max_iterations
            execution_history = []
            
            self.logger.logger.info(
                f"🚀 Starting smart iteration: simulate_first={simulate_first}, max_iter={max_iter}"
            )
            
            for iteration in range(max_iter):
                self.logger.logger.info(f"🔄 Smart iteration {iteration + 1}/{max_iter}")
                
                # Decidir si simular o ejecutar real
                if simulate_first:
                    # Simular todas excepto la última, o hasta que sea satisfactorio
                    should_simulate = iteration < max_iter - 1
                else:
                    # Ejecución real desde el inicio
                    should_simulate = False
                
                mode = "🎭 Simulation" if should_simulate else "⚡ Real execution"
                self.logger.logger.info(f"   Mode: {mode}")
                
                # 1. ACT - Ejecutar workflow
                execution_result = await self._execute_workflow_steps(
                    workflow_result.steps,
                    user_id,
                    {
                        "iteration": iteration + 1,
                        "simulation_mode": should_simulate,
                        "smart_iteration": True
                    },
                    simulate=should_simulate
                )
                
                execution_history.append({
                    "iteration": iteration + 1,
                    "execution_result": execution_result,
                    "steps_executed": len(workflow_result.steps),
                    "mode": "simulation" if should_simulate else "real"
                })
                
                # 2. REFLECT - Evaluar resultados
                reflection_result = await self._reflect_on_execution(
                    goal=user_message,
                    execution_history=execution_history,
                    current_result=execution_result
                )
                
                # 3. DECIDE - ¿Satisfactorio?
                is_satisfactory = self._is_result_satisfactory(reflection_result, execution_result)
                
                # Si es satisfactorio y fue simulación, ejecutar una vez real
                if is_satisfactory and should_simulate and simulate_first:
                    self.logger.logger.info(
                        "✅ Simulation satisfactory, executing real version..."
                    )
                    
                    # Ejecutar versión real del workflow satisfactorio
                    real_execution = await self._execute_workflow_steps(
                        workflow_result.steps,
                        user_id,
                        {
                            "iteration": f"{iteration + 1}_final",
                            "simulation_mode": False,
                            "final_execution": True
                        },
                        simulate=False
                    )
                    
                    execution_history.append({
                        "iteration": f"{iteration + 1}_final",
                        "execution_result": real_execution,
                        "steps_executed": len(workflow_result.steps),
                        "mode": "real_final"
                    })
                    
                    return {
                        "final_result": real_execution,
                        "reflection_analysis": reflection_result,
                        "execution_history": execution_history,
                        "iterations": iteration + 1,
                        "status": "completed_with_real_execution",
                        "optimized": True
                    }
                
                elif is_satisfactory or iteration == max_iter - 1:
                    # Completado (real o última iteración)
                    self.logger.logger.info(f"✅ Workflow completed after {iteration + 1} iterations")
                    
                    return {
                        "final_result": execution_result,
                        "reflection_analysis": reflection_result,
                        "execution_history": execution_history,
                        "iterations": iteration + 1,
                        "status": "completed" if is_satisfactory else "max_iterations_reached",
                        "optimized": True
                    }
                
                # 4. RE-PLAN - Refinar workflow
                try:
                    refined_steps = await self._refine_workflow_from_reflection(
                        goal=user_message,
                        reflection_result=reflection_result,
                        execution_history=execution_history,
                        original_steps=steps  # ✅ Pasar steps originales para conservar UUIDs
                    )
                    
                    workflow_result.steps = refined_steps
                    self.logger.logger.info(f"🔄 Workflow refined for next iteration")
                    
                except Exception as e:
                    self.logger.log_error(e, f"smart iteration refinement {iteration + 1}")
                    break
            
            return {
                "final_result": execution_history[-1]["execution_result"] if execution_history else {},
                "execution_history": execution_history,
                "iterations": len(execution_history),
                "status": "max_iterations_reached",
                "optimized": True
            }
            
        except Exception as e:
            self.logger.log_error(e, "smart workflow iteration")
            return {
                "final_result": {},
                "execution_history": [],
                "iterations": 0,
                "status": "error",
                "error": str(e),
                "optimized": False
            }
    
    async def refine_workflow_with_feedback(
        self,
        original_result: WorkflowCreationResult,
        execution_feedback: Dict[str, Any],
        user_id: int,
        db_session: Session
    ) -> WorkflowCreationResult:
        """
        Refinamiento de workflow con feedback específico
        Centraliza lógica de WorkflowEngine.refine_workflow_with_reflection
        """
        try:
            # Analizar feedback de ejecución
            reflection_analysis = await self._analyze_execution_feedback(
                original_result, execution_feedback
            )
            
            # Re-planificar con insights de reflexión
            refined_steps = await self._replan_with_reflection_insights(
                original_result, reflection_analysis, user_id, db_session
            )
            
            # Crear nuevo resultado refinado
            refined_result = WorkflowCreationResult(
                status="success",
                workflow_type=original_result.workflow_type,
                steps=refined_steps,
                oauth_requirements=original_result.oauth_requirements,
                discovered_resources=original_result.discovered_resources,
                confidence=original_result.confidence,
                next_actions=["Ejecutar workflow refinado"],
                metadata={
                    **original_result.metadata,
                    "refined": True,
                    "reflection_analysis": reflection_analysis,
                    "original_steps_count": len(original_result.steps),
                    "refined_steps_count": len(refined_steps)
                }
            )
            
            return refined_result
            
        except Exception as e:
            self.logger.log_error(e, "workflow refinement with feedback")
            return original_result
    
    async def evaluate_workflow_execution(
        self,
        workflow_result: WorkflowCreationResult,
        execution_results: Dict[str, Any],
        user_id: int
    ) -> Dict[str, Any]:
        """
        Evaluación de ejecución de workflow
        Centraliza lógica de WorkflowEngine.evaluate_workflow_execution
        """
        try:
            evaluation = {
                "overall_success": execution_results.get("success", False),
                "steps_completed": execution_results.get("steps_completed", 0),
                "total_steps": len(workflow_result.steps),
                "execution_time": execution_results.get("execution_time"),
                "errors": execution_results.get("errors", []),
                "recommendations": []
            }
            
            # Análisis de éxito
            if evaluation["steps_completed"] == evaluation["total_steps"]:
                evaluation["completion_rate"] = 1.0
                evaluation["recommendations"].append("Workflow executed successfully")
            else:
                evaluation["completion_rate"] = evaluation["steps_completed"] / evaluation["total_steps"]
                evaluation["recommendations"].append("Consider workflow refinement")
            
            # Análisis de errores
            if evaluation["errors"]:
                evaluation["error_analysis"] = await self._analyze_execution_errors(evaluation["errors"])
                evaluation["recommendations"].extend(evaluation["error_analysis"].get("suggestions", []))
            
            return evaluation
            
        except Exception as e:
            self.logger.log_error(e, "workflow execution evaluation")
            return {"overall_success": False, "error": str(e)}
    
    async def reflect_with_interval(
        self,
        steps: List[Dict[str, Any]],
        current_step: int,
        goal: str,
        execution_context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Reflexión por intervalos como en KyraAgentService
        """
        if current_step % self.reflect_interval != 0:
            return None
        
        self.logger.logger.info(f"🤔 Interval reflection at step {current_step}")
        
        try:
            # ✅ FIX: Usar LLM service compartido o fallback
            llm_service = self.llm_service
            if not llm_service:
                from app.ai.llm_clients.llm_service import get_llm_service
                llm_service = get_llm_service()
                self.logger.logger.warning("⚠️ Using fallback LLM service - CAG context may be lost")
            
            # Prompt de reflexión
            prompt = f"""
            Goal: {goal}
            Current Step: {current_step}
            Steps Executed: {steps[:current_step]}
            
            Reflect on progress and suggest next step if needed.
            """
            
            reflection = await llm_service.run(
                system_prompt=prompt,
                short_term=execution_context.get("recent", []),
                long_term=execution_context.get("long_term", []),
                user_prompt="",
                temperature=0.0,
                mode="reflect"
            )
            
            return reflection
            
        except Exception as e:
            self.logger.log_error(e, "interval reflection")
            return None
    
    # Métodos privados que centralizan lógica existente
    
    async def _execute_workflow_steps(
        self, 
        steps: List[Dict[str, Any]], 
        user_id: int, 
        metadata: Dict[str, Any],
        simulate: bool = False
    ) -> Dict[str, Any]:
        """
        Ejecuta steps del workflow usando WorkflowRunner (real o simulado)
        Centraliza lógica de ChatService._execute_workflow_steps
        
        Args:
            simulate: Si True, usa fake data para iteración rápida
        """
        try:
            from app.services.workflow_runner_service import WorkflowRunnerService
            from app.services.flow_execution_service import FlowExecutionService
            from app.services.flow_validator_service import FlowValidatorService
            from app.services.credential_service import CredentialService
            from app.repositories.credential_repository import CredentialRepository
            from sqlalchemy.orm import sessionmaker
            from app.db.database import async_session
            
            # Crear dependencias para WorkflowRunnerService manualmente
            async with async_session() as db_session:
                credential_repo = CredentialRepository(db_session)
                credential_service = CredentialService(credential_repo)
                
                # ✅ FIX: FlowExecutionService needs repository parameter
                from app.repositories.flow_execution_repository import FlowExecutionRepository
                flow_exec_repo = FlowExecutionRepository(db_session)
                flow_exec_svc = FlowExecutionService(flow_exec_repo)
                
                validator = FlowValidatorService()
                
                # Crear WorkflowRunner con todas las dependencias
                runner = WorkflowRunnerService(flow_exec_svc, credential_service, validator)
            
            # Limpiar steps para ejecución (eliminar campos de traza)
            clean_steps = self._clean_steps_for_execution(steps)
            
            # 🆕 Simular en primeras iteraciones para rapidez
            if simulate:
                self.logger.logger.info("🎭 Executing workflow simulation with fake data")
                result = await self._simulate_workflow_execution(clean_steps, user_id, metadata)
            else:
                self.logger.logger.info("⚡ Executing workflow with real data")
                # Generate a temporary flow_id and convert metadata to inputs
                from uuid import uuid4
                temp_flow_id = uuid4()
                inputs = metadata if isinstance(metadata, dict) else {}
                
                execution_id, workflow_result = await runner.run_workflow(
                    flow_id=temp_flow_id,
                    steps=clean_steps,
                    user_id=user_id,
                    inputs=inputs,
                    simulate=False
                )
                
                # Convert WorkflowResultDTO back to the expected result format
                result = {
                    "success": workflow_result.overall_status == "success",
                    "steps_completed": len([s for s in workflow_result.steps if s.status == "success"]),
                    "total_steps": len(workflow_result.steps),
                    "errors": [s.error for s in workflow_result.steps if s.error],
                    "step_results": [
                        {
                            "step_id": f"step_{i+1}",
                            "node_id": s.node_id,
                            "action_id": s.action_id,
                            "status": s.status,
                            "output": s.output,
                            "error": s.error,
                            "duration_ms": s.duration_ms
                        }
                        for i, s in enumerate(workflow_result.steps)
                    ],
                    "execution_id": str(execution_id),
                    "metadata": metadata
                }
            
            return result
            
        except Exception as e:
            self.logger.log_error(e, "workflow steps execution")
            return {"success": False, "error": str(e), "steps_completed": 0}
    
    def _clean_steps_for_execution(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Limpia steps eliminando campos de traza que interfieren con ejecución
        """
        clean_steps = []
        
        for step in steps:
            # Mantener solo campos necesarios para ejecución
            # step puede ser StepMetaDTO (objeto) o dict
            if isinstance(step, dict):
                # Es un diccionario - acceso directo
                clean_step = {
                    "id": step.get("id") or step.get("execution_step"),  # ✅ Usar id si existe, sino execution_step
                    "step_type": step.get("step_type", "action"),
                    "execution_step": step.get("execution_step"),
                    "node_id": str(step.get("node_id", "")),
                    "action_id": str(step.get("action_id", "")),
                    "node_name": step.get("node_name") or step.get("node_id", ""),  # ✅ Requerido por StepMetaDTO
                    "action_name": step.get("action_name") or step.get("action_id", ""),  # ✅ Requerido por StepMetaDTO
                    "params": step.get("parameters", {}),  # ✅ Requerido por StepMetaDTO (alias de parameters)
                    "params_meta": step.get("params_meta", []),  # ✅ Requerido por StepMetaDTO (debe ser lista)
                    "parameters": step.get("parameters", {}),
                    "depends_on": step.get("depends_on", []),
                    "default_auth": step.get("default_auth")
                }
            else:
                # Es StepMetaDTO - usar atributos
                clean_step = {
                    "id": getattr(step, "id", None) or getattr(step, "execution_step", None),  # ✅ Incluir id
                    "step_type": "action",  # StepMetaDTO siempre es action
                    "execution_step": getattr(step, "execution_step", None),
                    "node_id": str(step.node_id),
                    "action_id": str(step.action_id),
                    "node_name": getattr(step, "node_name", str(step.node_id)),  # ✅ Requerido por StepMetaDTO
                    "action_name": getattr(step, "action_name", str(step.action_id)),  # ✅ Requerido por StepMetaDTO
                    "params": step.params,  # ✅ Requerido por StepMetaDTO
                    "params_meta": getattr(step, "params_meta", []),  # ✅ Requerido por StepMetaDTO (debe ser lista)
                    "parameters": step.params,
                    "depends_on": [],  # StepMetaDTO no tiene depends_on
                    "default_auth": step.default_auth
                }
            
            # ✅ Asegurar que el step tenga un ID válido
            if not clean_step.get("id"):
                from uuid import uuid4
                clean_step["id"] = str(uuid4())
            
            # Eliminar campos de traza (description, node_name, etc.)
            # Estos son útiles para debugging pero interfieren con motor real
            
            clean_steps.append(clean_step)
        
        return clean_steps
    
    async def _simulate_workflow_execution(
        self,
        steps: List[Dict[str, Any]], 
        user_id: int, 
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simula ejecución de workflow usando nuestro sistema de fake data
        Permite iteración rápida sin ejecutar acciones reales
        """
        try:
            from app.utils.template_engine import template_engine
            from app.connectors.factory import execute_node
            import time
            import random
            
            start_time = time.time()
            step_outputs = {}
            step_results = []
            errors = []
            
            self.logger.logger.info(f"🎭 Starting simulation of {len(steps)} steps")
            
            for i, step in enumerate(steps):
                try:
                    # Resolver templates con outputs de pasos anteriores
                    context = template_engine.build_context_from_outputs(step_outputs)
                    resolved_params = template_engine.resolve_template_in_params(
                        step.get("parameters", {}), 
                        context
                    )
                    
                    # Simular ejecución del step
                    node_name = step.get("node_id", "UnknownNode")
                    action_name = step.get("action_id", "unknown_action")
                    
                    fake_result = await execute_node(
                        node_name,
                        action_name,
                        resolved_params,
                        {},  # No credentials needed for simulation
                        simulate=True
                    )
                    
                    # Almacenar resultado para siguiente step
                    step_id = step.get("execution_step", f"step_{i+1}")
                    step_outputs[step_id] = fake_result
                    
                    step_results.append({
                        "step_id": step_id,
                        "node_name": node_name,
                        "action_name": action_name,
                        "status": fake_result.get("status", "success"),
                        "output": fake_result.get("output", {}),
                        "duration_ms": fake_result.get("duration_ms", random.randint(50, 500)),
                        "simulated": True
                    })
                    
                    self.logger.logger.debug(f"✅ Step {i+1} simulated: {node_name}.{action_name}")
                    
                except Exception as e:
                    error_msg = f"Error simulating step {i+1}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.logger.error(error_msg)
                    
                    step_results.append({
                        "step_id": f"step_{i+1}",
                        "status": "error",
                        "error": str(e),
                        "simulated": True
                    })
            
            execution_time = time.time() - start_time
            success_count = sum(1 for r in step_results if r.get("status") == "success")
            
            result = {
                "success": len(errors) == 0,
                "steps_completed": success_count,
                "total_steps": len(steps),
                "execution_time": execution_time,
                "errors": errors,
                "step_results": step_results,
                "step_outputs": step_outputs,
                "simulated": True,
                "metadata": {
                    **metadata,
                    "simulation_mode": True,
                    "fake_data_version": "1.0"
                }
            }
            
            self.logger.logger.info(
                f"🎭 Simulation completed: {success_count}/{len(steps)} steps successful in {execution_time:.2f}s"
            )
            
            return result
            
        except Exception as e:
            self.logger.log_error(e, "workflow simulation")
            return {
                "success": False, 
                "error": f"Simulation failed: {str(e)}", 
                "steps_completed": 0,
                "simulated": True
            }
    
    async def _reflect_on_execution(
        self,
        goal: str,
        execution_history: List[Dict[str, Any]],
        current_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Reflexión sobre ejecución usando ReflectHandler
        Centraliza lógica de ChatService._reflect_on_execution
        """
        try:
            from app.handlers.reflect import ReflectHandler
            
            # Preparar recent_steps para ReflectHandler
            recent_steps = []
            for entry in execution_history[-3:]:  # Últimos 3 pasos
                recent_steps.append({
                    "iteration": entry["iteration"],
                    "result": entry["execution_result"],
                    "steps_count": entry["steps_executed"]
                })
            
            # Crear ReflectHandler con creds vacías (no necesita credenciales reales para reflection)
            from app.handlers.reflect import ReflectHandler
            reflect_handler = ReflectHandler(creds={})
            reflection = await reflect_handler.execute(
                params={
                    "goal": goal,
                    "recent_steps": recent_steps
                },
                creds={}
            )
            
            return reflection
            
        except Exception as e:
            self.logger.log_error(e, "execution reflection")
            return {"critique": "Error in reflection", "next_step": None}
    
    def _is_result_satisfactory(
        self, 
        reflection_result: Dict[str, Any], 
        execution_result: Dict[str, Any]
    ) -> bool:
        """
        Evalúa si el resultado es satisfactorio
        Centraliza lógica de ChatService._is_result_satisfactory
        """
        # Criterio 1: Ejecución exitosa
        if not execution_result.get("success", False):
            return False
        
        # Criterio 2: Sin errores críticos
        errors = execution_result.get("errors", [])
        critical_errors = [e for e in errors if e.get("level") == "critical"]
        if critical_errors:
            return False
        
        # Criterio 3: Reflexión positiva
        critique = reflection_result.get("critique", "").lower()
        negative_indicators = ["failed", "error", "incomplete", "needs improvement"]
        if any(indicator in critique for indicator in negative_indicators):
            return False
        
        return True
    
    async def _refine_workflow_from_reflection(
        self,
        goal: str,
        reflection_result: Dict[str, Any],
        execution_history: List[Dict[str, Any]],
        original_steps: List[Dict[str, Any]] = None  # ✅ Recibir steps originales
    ) -> List[Dict[str, Any]]:
        """
        Refina workflow basado en reflexión
        Centraliza lógica de ChatService._refine_workflow_from_reflection
        """
        try:
            # ✅ FIX: Usar LLM service compartido que preserva CAG context
            llm_service = self.llm_service
            if not llm_service:
                from app.ai.llm_clients.llm_service import get_llm_service
                llm_service = get_llm_service()
                self.logger.logger.warning("⚠️ Using fallback LLM service for refinement - CAG context may be lost")
            
            # ✅ Conservar steps originales si no hay cambios específicos
            if not original_steps or len(original_steps) == 0:
                self.logger.logger.warning("⚠️ No original steps provided for refinement - returning empty workflow")
                return []
            
            # Prompt de refinamiento que CONSERVA UUIDs originales
            original_steps_json = json.dumps(original_steps, indent=2)
            prompt = f"""
Eres un experto en refinamiento de workflows. Tu tarea es CONSERVAR los UUIDs originales y solo mejorar parámetros si es necesario.

## WORKFLOW ORIGINAL:
{original_steps_json}

## CONTEXTO:
**Objetivo:** {goal}
**Reflexión:** {reflection_result.get("critique", "")}
**Siguiente paso sugerido:** {reflection_result.get("next_step", "")}
**Historial de ejecución:** {execution_history}

## INSTRUCCIONES CRÍTICAS:
1. **CONSERVA EXACTAMENTE** todos los node_id y action_id del workflow original
2. Solo mejora parameters si la reflexión lo sugiere específicamente
3. Si no hay problemas críticos, devuelve el workflow original sin cambios

**IMPORTANTE: Responde ÚNICAMENTE con JSON válido:**

{{
  "status": "ready",
  "execution_plan": [/* conserva los steps originales con sus UUIDs exactos */]
}}

NUNCA cambies los UUIDs. Solo mejora parámetros si es absolutamente necesario.
            """
            
            refined_plan = await llm_service.run(
                system_prompt=prompt,
                short_term=[],
                long_term=[],
                user_prompt="Refine the workflow",
                temperature=0.1
            )
            
            # Procesar plan refinado (lógica similar a LLMWorkflowPlanner)
            if isinstance(refined_plan, dict) and "execution_plan" in refined_plan:
                return refined_plan["execution_plan"]
            
            return []
            
        except Exception as e:
            self.logger.log_error(e, "workflow refinement from reflection")
            return []
    
    async def _analyze_execution_feedback(
        self,
        original_result: WorkflowCreationResult,
        execution_feedback: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analiza feedback de ejecución
        Centraliza lógica de WorkflowEngine._analyze_execution_feedback
        """
        analysis = {
            "original_steps_count": len(original_result.steps),
            "execution_success": execution_feedback.get("success", False),
            "errors": execution_feedback.get("errors", []),
            "performance_metrics": execution_feedback.get("metrics", {}),
            "recommendations": []
        }
        
        # Análisis de errores
        if analysis["errors"]:
            analysis["error_patterns"] = self._categorize_errors(analysis["errors"])
            analysis["recommendations"].extend(self._get_error_recommendations(analysis["error_patterns"]))
        
        return analysis
    
    async def _replan_with_reflection_insights(
        self,
        original_result: WorkflowCreationResult,
        reflection_analysis: Dict[str, Any],
        user_id: int,
        db_session: Session
    ) -> List[Dict[str, Any]]:
        """
        Re-planifica con insights de reflexión
        Centraliza lógica de WorkflowEngine._replan_with_reflection_insights
        """
        try:
            # Usar insights para mejorar plan original
            improved_steps = []
            
            for step in original_result.steps:
                # Aplicar mejoras basadas en análisis
                improved_step = step.copy()
                
                # Aquí se aplicarían mejoras específicas basadas en reflection_analysis
                # Por ahora, mantener estructura básica
                
                improved_steps.append(improved_step)
            
            return improved_steps
            
        except Exception as e:
            self.logger.log_error(e, "re-planning with reflection insights")
            return original_result.steps
    
    async def _analyze_execution_errors(self, errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analiza errores de ejecución para generar recomendaciones"""
        error_analysis = {
            "total_errors": len(errors),
            "error_types": {},
            "suggestions": []
        }
        
        for error in errors:
            error_type = error.get("type", "unknown")
            error_analysis["error_types"][error_type] = error_analysis["error_types"].get(error_type, 0) + 1
        
        # Generar sugerencias basadas en tipos de error
        if "auth" in error_analysis["error_types"]:
            error_analysis["suggestions"].append("Check OAuth credentials")
        if "network" in error_analysis["error_types"]:
            error_analysis["suggestions"].append("Verify network connectivity")
        
        return error_analysis
    
    def _categorize_errors(self, errors: List[Dict[str, Any]]) -> Dict[str, List]:
        """Categoriza errores por tipo"""
        categories = {"auth": [], "network": [], "validation": [], "other": []}
        
        for error in errors:
            error_msg = error.get("message", "").lower()
            if "auth" in error_msg or "token" in error_msg:
                categories["auth"].append(error)
            elif "network" in error_msg or "connection" in error_msg:
                categories["network"].append(error)
            elif "validation" in error_msg or "invalid" in error_msg:
                categories["validation"].append(error)
            else:
                categories["other"].append(error)
        
        return categories
    
    def _get_error_recommendations(self, error_patterns: Dict[str, List]) -> List[str]:
        """Genera recomendaciones basadas en patrones de error"""
        recommendations = []
        
        if error_patterns["auth"]:
            recommendations.append("Re-authenticate required services")
        if error_patterns["network"]:
            recommendations.append("Check network connectivity and retry")
        if error_patterns["validation"]:
            recommendations.append("Validate input parameters")
        
        return recommendations