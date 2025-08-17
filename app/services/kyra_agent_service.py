from typing import List, Dict, Any
from uuid import UUID, uuid4
import json
import logging

from fastapi import Depends

from app.ai.llm_clients.llm_service import LLMService, get_llm_service
from app.ai.memories.manager import MemoryManager
from app.agent.guardrails import Guardrail
from app.agent.run_manager import RunManager
from app.db.models import AgentStatus
from app.dtos.step_meta_dto import StepMetaDTO
from app.dtos.step_result_dto import StepResultDTO
from app.services.workflow_runner_service import (
    get_workflow_runner,
    WorkflowRunnerService,
)
from app.services.cag_service import get_cag_service, ICAGService
from app.telemetry.agent_instrumentation import start_span

# INTEGRACIÓN: Import de LLMWorkflowPlanner para unificar planificación
from app.workflow_engine.llm.llm_workflow_planner import LLMWorkflowPlanner, get_unified_workflow_planner


class KyraAgentService:
    """Execute a plan step by step with reflection and guardrails."""

    REFLECT_INTERVAL = 3

    def __init__(
        self,
        llm_service: LLMService = None,
        workflow_runner: WorkflowRunnerService = None,
        cag_service: ICAGService = None,
        workflow_planner: LLMWorkflowPlanner = None,
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self.llm_service = llm_service
        self.workflow_runner = workflow_runner
        self.cag_service = cag_service
        # INTEGRACIÓN: Fuente única de verdad para planificación
        self.workflow_planner = workflow_planner

    async def _compose_system_prompt(self, base_prompt: str) -> str:
        """Append static CAG context to the base system prompt."""
        context = await self.cag_service.build_context()
        ctx_text = json.dumps(context, ensure_ascii=False)
        return f"{base_prompt}\n\n{ctx_text}"

    async def execute_single_step(self, step: StepMetaDTO, user_id: int) -> StepResultDTO:
        """Run one workflow step via WorkflowRunnerService."""
        _fid = uuid4()
        _, result = await self.workflow_runner.run_workflow(
            flow_id=_fid,
            steps=[step.model_dump()],
            user_id=user_id,
            inputs=step.params,
            simulate=step.simulate,
        )
        return result.steps[0]

    async def run(
        self,
        run_manager: RunManager,
        memory_manager: MemoryManager,
        agent_id: UUID,
        run_id: UUID,
        steps: List[StepMetaDTO] | None = None,
        user_id: int = 0,
        system_prompt: str = "",
        user_prompt: str = "",
    ) -> None:
        full_prompt = await self._compose_system_prompt(system_prompt)

        if steps is None:
            # INTEGRACIÓN: Usar LLMWorkflowPlanner como fuente única de verdad
            short_term = await memory_manager.load_short_term(agent_id)
            long_term = await memory_manager.search_long_term(user_prompt)
            
            # Preparar contexto de memoria para el planner
            history = [
                {"role": "short_term", "content": short_term},
                {"role": "long_term", "content": long_term}
            ]
            
            with start_span("unified_plan", agent_id=str(agent_id), run_id=str(run_id)):
                # Obtener CAG context desde cag_service
                cag_context = await self.cag_service.build_context()
                
                # Usar workflow planner unificado
                execution_plan = await self.workflow_planner.unified_workflow_planning(
                    user_message=user_prompt,
                    history=history,
                    cag_context=cag_context,
                    workflow_type="execution"  # Indicar que es para ejecución directa
                )
                
                # Convertir plan a StepMetaDTO format
                steps = [self._convert_plan_step_to_meta_dto(step) for step in execution_plan]

        i = 0
        while i < len(steps):
            step = steps[i]
            await Guardrail.check(f"{step.node_name}.{step.action_name}", step.params)
            with start_span("tool_call", step=step.node_name):
                result = await self.execute_single_step(step, user_id)
            with start_span("memory_write", step=str(step.id)):
                await memory_manager.append_short_term(
                    agent_id,
                    {"step": step.id, "result": result.model_dump()},
                )
            if result.status != "success":
                await run_manager.update_status(run_id, AgentStatus.failed)
                return
            await run_manager.update_status(run_id, AgentStatus.running)
            i += 1
            if i % self.REFLECT_INTERVAL == 0:
                # REFACTORIZADO: Usa ReflectionService centralizado
                from app.workflow_engine.reflection.reflection_service import ReflectionService
                
                reflection_service = ReflectionService()
                recent = await memory_manager.load_short_term(agent_id)
                long_term = await memory_manager.search_long_term(user_prompt)
                
                execution_context = {
                    "recent": recent,
                    "long_term": long_term,
                    "agent_id": str(agent_id),
                    "run_id": str(run_id)
                }
                
                with start_span("reflect", agent_id=str(agent_id), run_id=str(run_id)):
                    reflection = await reflection_service.reflect_with_interval(
                        steps=steps[:i],  # Steps ejecutados hasta ahora
                        current_step=i,
                        goal=user_prompt,
                        execution_context=execution_context
                    )
                
                if reflection:
                    nxt = reflection.get("next_step")
                    if nxt:
                        try:
                            steps.insert(i, StepMetaDTO(**nxt))
                        except Exception:
                            pass
        await run_manager.update_status(run_id, AgentStatus.succeeded)

    def _convert_plan_step_to_meta_dto(self, plan_step: Dict[str, Any]) -> StepMetaDTO:
        """
        INTEGRACIÓN: Convierte step del LLMWorkflowPlanner a formato StepMetaDTO
        """
        try:
            # El plan del LLMWorkflowPlanner incluye estos campos estándar
            return StepMetaDTO(
                id=plan_step.get("id", str(uuid4())),
                node_name=plan_step.get("node_name", "unknown"),
                action_name=plan_step.get("action_name", "unknown"),
                params=plan_step.get("params", {}),
                simulate=plan_step.get("simulate", False),
                description=plan_step.get("description", ""),
                expected_output=plan_step.get("expected_output", ""),
                requires_auth=plan_step.get("requires_auth", False)
            )
        except Exception as e:
            self.logger.warning(f"Error converting plan step to StepMetaDTO: {e}, using fallback")
            # Fallback si hay problemas de formato
            return StepMetaDTO(
                id=str(uuid4()),
                node_name="fallback",
                action_name="error",
                params={"error": str(e), "original_step": plan_step},
                simulate=True
            )


# INTEGRACIÓN: Factory actualizado para incluir LLMWorkflowPlanner
def get_kyra_agent_service(
    llm_service: LLMService = None,
    workflow_runner: WorkflowRunnerService = None,
    cag_service: ICAGService = None,
    workflow_planner: LLMWorkflowPlanner = None,
) -> KyraAgentService:
    """
    Factory para KyraAgentService con integración completa
    Incluye LLMWorkflowPlanner como fuente única de verdad para planificación
    Acepta dependencias opcionales para compatibilidad con worker
    """
    return KyraAgentService(
        llm_service=llm_service or get_llm_service(),
        workflow_runner=workflow_runner or get_workflow_runner(),
        cag_service=cag_service,  # Debe pasarse externamente por session dependency
        workflow_planner=workflow_planner  # Debe pasarse externamente por async dependency
    )


# INTEGRACIÓN: Factory con Depends para FastAPI
async def get_kyra_agent_service_for_api(
    llm_service: LLMService = Depends(get_llm_service),
    workflow_runner: WorkflowRunnerService = Depends(get_workflow_runner),
    cag_service: ICAGService = Depends(get_cag_service),
) -> KyraAgentService:
    """
    Factory async para KyraAgentService en contexto FastAPI
    """
    workflow_planner = await get_unified_workflow_planner()
    return KyraAgentService(
        llm_service=llm_service,
        workflow_runner=workflow_runner,
        cag_service=cag_service,
        workflow_planner=workflow_planner
    )
