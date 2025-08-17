# app/services/flow_validator_service.py
from typing import List, Dict, Any, Union, Set
from app.dtos.step_meta_dto import StepMetaDTO
from app.dtos.branch_step_dto import BranchStepDTO
from uuid import UUID

class FlowValidatorService:
    """
    Servicio que implementa la validación de pasos antes de su ejecución.
    """
    async def validate_steps(self, steps: List[StepMetaDTO]) -> None:
        for step in steps:
            # Validar número de reintentos
            if step.retries < 0:
                raise ValueError(
                    f"Step {step.node_name}.{step.action_name}: retries debe ser >= 0, hallado {step.retries}"
                )
            # Validar timeout
            if step.timeout_ms is not None and step.timeout_ms < 0:
                raise ValueError(
                    f"Step {step.node_name}.{step.action_name}: timeout_ms debe ser >= 0, hallado {step.timeout_ms}"
                )
            # Validar simulate
            if not isinstance(step.simulate, bool):
                raise ValueError(
                    f"Step {step.node_name}.{step.action_name}: simulate debe ser booleano"
                )
            # Validar uses_mcp
            if not isinstance(step.uses_mcp, bool):
                raise ValueError(
                    f"Step {step.node_name}.{step.action_name}: uses_mcp debe ser booleano"
                )
        # Si llega aquí, todas las validaciones pasaron

    async def validate_flow_spec(self, spec: Dict[str, Any]) -> None:
        steps_raw = spec.get("steps", [])
        if not steps_raw:
            raise ValueError("Spec debe incluir lista 'steps'")
        start_id = spec.get("start_id")
        if start_id is None:
            raise ValueError("Spec debe incluir 'start_id'")

        step_models: Dict[UUID, Union[StepMetaDTO, BranchStepDTO]] = {}
        for item in steps_raw:
            step_type = item.get("type", "action")
            if step_type == "branch":
                step = BranchStepDTO(**item)
            else:
                step = StepMetaDTO(**item)
            if step.id in step_models:
                raise ValueError(f"Paso duplicado: {step.id}")
            step_models[step.id] = step

        ids: Set[UUID] = set(step_models.keys())

        for step in step_models.values():
            if isinstance(step, StepMetaDTO):
                if step.next and step.next not in ids:
                    raise ValueError(f"Paso {step.id} referencia next desconocida {step.next}")
            else:  # BranchStepDTO
                if step.next_on_true not in ids or step.next_on_false not in ids:
                    raise ValueError(f"Branch {step.id} referencias inválidas")
                if not isinstance(step.condition, str) or not step.condition:
                    raise ValueError(f"Branch {step.id} condición inválida")

        # Detección simple de ciclos mediante DFS
        def dfs(sid: UUID, path: Set[UUID]):
            if sid in path:
                raise ValueError("Ciclo detectado en spec")
            path.add(sid)
            step = step_models[sid]
            if isinstance(step, StepMetaDTO):
                if step.next:
                    dfs(step.next, path.copy())
            else:
                dfs(step.next_on_true, path.copy())
                dfs(step.next_on_false, path.copy())

        dfs(start_id, set())
        
def get_flow_validator_service() -> FlowValidatorService:
    """
    Factory para inyectar FlowValidatorService en FastAPI.
    """
    return FlowValidatorService()        
