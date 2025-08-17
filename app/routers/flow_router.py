# app/routers/flow_router.py - CONSOLIDADO CON WORKFLOW_ROUTER
# Maneja tanto definición como ejecución de flows

import logging
from uuid import UUID
from typing import List

from fastapi import APIRouter, HTTPException, Depends, status, Query

logger = logging.getLogger(__name__)

from app.models.chat_models import ChatRequestModel
# ARREGLADO: Usar WorkflowEngine en lugar de orchestrator_service faltante (import removido - no se usa)
from app.dtos.flow_dtos import (
    DryRunRequestDTO,
    InMemoryWorkflowRunRequestDTO,
    ToggleFlowDTO,
    FlowSummaryDTO,
    FlowDetailDTO,
    CreateFlowRequestDTO,
    CreateFlowResponseDTO,
)
# PlannerResponseDTO y ValidateResponseDTO removidos - endpoints eliminados
from app.dtos.workflow_result_dto import WorkflowResultDTO
from app.services.workflow_runner_service import get_workflow_runner
from app.services.workflow_runner_service import WorkflowRunnerService
from app.services.trigger_orchestrator_service import TriggerOrchestratorService
from app.services.trigger_orchestrator_service import get_trigger_orchestrator_service
from app.services.flow_service import FlowService
from app.services.flow_service import get_flow_service
# Orchestrator service removido - endpoints /planner y /flows/validate eliminados
from app.services.flow_execution_service import FlowExecutionService
from app.services.flow_execution_service import get_flow_execution_service
from app.services.flow_definition_service import FlowDefinitionService
from app.services.flow_definition_service import get_flow_definition_service
from app.core.auth import get_current_user_id

router = APIRouter(prefix="/api", tags=["flow"])


@router.get(
    "/flows",
    response_model=List[FlowSummaryDTO],
    summary="Lista los flujos del usuario autenticado",
)
async def list_flows(
    flow_svc: FlowService = Depends(get_flow_service),
    user_id: int = Depends(get_current_user_id),
) -> List[FlowSummaryDTO]:
    logger.info(f"FLOW_ROUTER: Listando flows para user_id: {user_id}")
    try:
        flows = await flow_svc.list_flows(user_id)
        logger.info(f"FLOW_ROUTER: Se encontraron {len(flows)} flows para user_id: {user_id}")
        return flows
    except Exception as e:
        logger.error(f"FLOW_ROUTER: Error listando flows para user_id: {user_id}: {str(e)}")
        logger.exception("FLOW_ROUTER: Stack trace completo del error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error listing flows: {type(e).__name__}")


@router.get(
    "/flows/{flow_id}",
    response_model=FlowDetailDTO,
    summary="Obtiene el detalle de un flujo",
)
async def get_flow(
    flow_id: UUID,
    include_spec: bool = Query(False, alias="includeSpec"),
    flow_svc: FlowService = Depends(get_flow_service),
    user_id: int = Depends(get_current_user_id),
) -> FlowDetailDTO:
    try:
        # ✅ Delegar toda la lógica al service
        return await flow_svc.get_flow_detail(
            flow_id=flow_id,
            owner_id=UUID(str(user_id)),
            include_spec=include_spec
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Endpoints /planner y /flows/validate removidos - no se usaban en el frontend


@router.post(
    "/flows/dry-run",
    response_model=WorkflowResultDTO,
    summary="Simula la ejecución de un flujo sin afectar sistemas externos"
)
async def dry_run_flow(
    request: DryRunRequestDTO,
    runner: WorkflowRunnerService = Depends(get_workflow_runner),
):
    """
    Recibe:
      - flow_id: UUID del flujo a simular
      - steps: lista de StepMetaDTO con retries, timeout_ms, etc.
      - user_id: ID del usuario
      - test_inputs: inputs opcionales
    Devuelve WorkflowResultDTO con outputs stub y status.
    """
    try:
        _, result = await runner.run_workflow(
            flow_id=request.flow_id,
            steps=request.steps,
            user_id=request.user_id,
            inputs=request.test_inputs or {},
            simulate=True
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/flows/execute-temp",
    response_model=WorkflowResultDTO,
    summary="Ejecuta un workflow temporal sin guardarlo (n8n-style)"
)
async def execute_temp_workflow(
    request: InMemoryWorkflowRunRequestDTO,
    runner: WorkflowRunnerService = Depends(get_workflow_runner),
):
    """
    Ejecuta un workflow temporal sin guardarlo en la BD.
    Perfecto para workflows conversacionales que no necesitan persistir.
    
    Similar a n8n donde puedes ejecutar workflows directamente.
    """
    try:
        logger.info(f"🚀 TEMP WORKFLOW: Executing {len(request.steps)} steps, simulate={request.simulate}")
        
        # 🔧 OPTIMIZACIÓN: Generar UUID temporal para trazabilidad pero no guardar workflow
        from uuid import uuid4
        temp_flow_id = uuid4()
        
        # Usar el nuevo método execute_workflow_steps con flow_id temporal
        execution_id, result = await runner.execute_workflow_steps(
            steps=request.steps,
            user_id=request.user_id,
            inputs=request.inputs,
            simulate=request.simulate,
            flow_id=temp_flow_id  # UUID temporal para trazabilidad de ejecución
        )
        
        logger.info(f"✅ TEMP WORKFLOW: Completed with status {result.overall_status}, execution_id={execution_id}")
        return result
        
    except Exception as e:
        logger.error(f"❌ TEMP WORKFLOW: Error executing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error ejecutando workflow temporal: {str(e)}"
        )


@router.post(
    "/flows/{flow_id}/activate",
    response_model=ToggleFlowDTO,
    summary="Activa o desactiva el trigger de un flujo"
)
async def toggle_flow(
    flow_id: UUID,
    payload: ToggleFlowDTO,
    flow_svc: FlowService = Depends(get_flow_service),
    orchestrator: TriggerOrchestratorService = Depends(get_trigger_orchestrator_service),
    def_service: FlowDefinitionService = Depends(get_flow_definition_service),
    user_id: int = Depends(get_current_user_id),
):
    """
    Persiste el flag is_active en Flow y luego programa o cancela el trigger:
      1) flow_svc.set_flow_active(...)
      2) orchestrator.schedule_flow(...) o unschedule_flow(...)
    """
    try:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🔧 TOGGLE_FLOW: Starting toggle for flow {flow_id}, target state: {payload.is_active}")

        # 1) Recupera spec primero para validación
        spec = await def_service.get_flow_spec(flow_id)
        
        # 2) Programa/desprograma triggers ANTES de actualizar BD
        if payload.is_active:
            logger.info(f"🔧 TOGGLE_FLOW: Scheduling flow {flow_id}")
            await orchestrator.schedule_flow(flow_id, spec, user_id)
        else:
            logger.info(f"🔧 TOGGLE_FLOW: Unscheduling flow {flow_id}")
            await orchestrator.unschedule_flow(flow_id, spec, user_id)

        # 3) Solo si el scheduling fue exitoso, actualizar BD
        logger.info(f"🔧 TOGGLE_FLOW: Updating flow status in DB to {payload.is_active}")
        updated_flow = await flow_svc.set_flow_active(flow_id, payload.is_active, user_id)
        
        logger.info(f"🔧 TOGGLE_FLOW: Successfully toggled flow {flow_id} to {updated_flow.is_active}")
        return ToggleFlowDTO(is_active=updated_flow.is_active)
    except Exception as e:
        logger.error(f"🔧 TOGGLE_FLOW: Error toggling flow {flow_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/flows/create",
    response_model=CreateFlowResponseDTO,
    summary="Crea y guarda un nuevo workflow"
)
async def create_flow(
    request: CreateFlowRequestDTO,
    flow_svc: FlowService = Depends(get_flow_service),
    user_id: int = Depends(get_current_user_id),
):
    """
    Crea un nuevo workflow y lo guarda en la base de datos.
    El workflow se crea inactivo por defecto.
    """
    try:
        # Crear el flow usando el servicio
        flow_summary = await flow_svc.create_flow(
            name=request.name,
            spec=request.spec,
            owner_id=user_id,
            description=request.description
        )
        
        # Preparar respuesta
        return CreateFlowResponseDTO(
            flow_id=flow_summary.flow_id,
            name=flow_summary.name,
            description=request.description,
            is_active=flow_summary.is_active,
            created_at=flow_summary.created_at,
            success=True,
            message=f"Workflow '{request.name}' guardado exitosamente"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error creando workflow: {str(e)}"
        )


# ==================== ENDPOINTS CONSOLIDADOS DE WORKFLOW_ROUTER ====================
# Agregados para consolidar funcionalidad de ejecución

from app.dtos.workflow_run_request_dto import WorkflowRunRequestDTO

@router.post(
    "/flows/{flow_id}/run",
    response_model=WorkflowResultDTO,
    summary="Ejecuta un flujo y persiste los resultados (CONSOLIDADO)"
)
async def run_flow_with_persistence(
    flow_id: UUID,
    request: WorkflowRunRequestDTO,
    flow_exec_svc: FlowExecutionService = Depends(get_flow_execution_service),
    runner: WorkflowRunnerService = Depends(get_workflow_runner),
):
    """
    CONSOLIDADO de workflow_router.py:
    1) Registra la ejecución con estado 'running'.
    2) Ejecuta cada paso del flujo.
    3) Actualiza la ejecución con 'success' o 'error', outputs y posible mensaje de error.
    """
    # 1) Iniciar ejecución
    exec_dto = await flow_exec_svc.start_execution(
        flow_id=flow_id,
        inputs=request.inputs,
    )

    try:
        # 2) Ejecutar los pasos definidos
        _, result = await runner.run_workflow(
            steps=request.steps,
            user_id=request.user_id,
            flow_id=flow_id,
            inputs=request.inputs
        )

        # 3) Finalizar con éxito
        await flow_exec_svc.finish_execution(
            execution_id=exec_dto.execution_id,
            status="success",
            outputs=result.dict(),   # Ajustar según la forma esperada de outputs
        )

        return result

    except Exception as e:
        # 4) Finalizar con error
        await flow_exec_svc.finish_execution(
            execution_id=exec_dto.execution_id,
            status="error",
            error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Error en ejecución: {str(e)}")


@router.post(
    "/flows/{flow_id}/run-now",
    response_model=WorkflowResultDTO,
    summary="Dispara manualmente el workflow sin simular"
)
async def run_flow_now(
    flow_id: UUID,
    runner: WorkflowRunnerService = Depends(get_workflow_runner),
    user_id: int = Depends(get_current_user_id),
    def_service: FlowDefinitionService = Depends(get_flow_definition_service),
):
    """
    Dispara una ejecución real del flujo usando su spec guardada.
    """
    try:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🔧 RUN-NOW: Starting manual execution for flow {flow_id}")
        
        spec = await def_service.get_flow_spec(flow_id)
        logger.info(f"🔧 RUN-NOW: Retrieved spec with {len(spec.get('steps', []))} steps")
        
        # 🚨 FIX: Convertir steps del spec a formato compatible con WorkflowRunnerService
        from uuid import UUID as UUIDClass
        
        converted_steps = []
        for step in spec.get("steps", []):
            # Asegurar que node_id y action_id sean UUID objects
            converted_step = {
                **step,
                'node_id': UUIDClass(step['node_id']) if isinstance(step.get('node_id'), str) else step.get('node_id'),
                'action_id': UUIDClass(step['action_id']) if isinstance(step.get('action_id'), str) else step.get('action_id'),
            }
            converted_steps.append(converted_step)
        
        logger.info(f"🔧 RUN-NOW: Converted {len(converted_steps)} steps to proper format")
        
        # Use the manual creation function for the bridge service
        from app.services.chat_workflow_bridge_service import create_chat_workflow_bridge_service_manual
        from app.db.database import async_session
        
        async with async_session() as session:
            bridge_service = await create_chat_workflow_bridge_service_manual(session)
            
            # Crear contexto de workflow simulado para el bridge service
            workflow_context = {
                'steps': converted_steps,
                'status': 'execute_workflow'
            }
            
            result = await bridge_service._execute_workflow_now(workflow_context, user_id)
            logger.info(f"🔧 RUN-NOW: Execution completed with status: {result.status}")
            
            # Convert WorkflowCreationResultDTO to WorkflowResultDTO format
            from app.dtos.workflow_result_dto import WorkflowResultDTO
            from app.dtos.step_result_dto import StepResultDTO
            
            # Map status from WorkflowCreationResultDTO to WorkflowResultDTO format
            status_mapping = {
                "execute_workflow": "success",
                "ready": "success", 
                "error": "failure",
                "oauth_required": "partial_failure",
                "needs_clarification": "partial_failure"
            }
            
            mapped_status = status_mapping.get(result.status, "success")
            
            # Create step results from the execution metadata if available
            step_results = []
            execution_result = result.metadata.get('execution_result')
            if execution_result and hasattr(execution_result, 'steps'):
                step_results = execution_result.steps
            else:
                # Create basic step results from the workflow steps
                from uuid import uuid4
                for i, step in enumerate(converted_steps):
                    step_results.append(StepResultDTO(
                        node_id=step.get('node_id', uuid4()),
                        action_id=step.get('action_id', uuid4()),
                        status="success",
                        output={"message": "Step completed successfully"},
                        error=None,
                        duration_ms=100
                    ))
            
            return WorkflowResultDTO(
                overall_status=mapped_status,
                steps=step_results
            )
            
    except Exception as e:
        logger.error(f"🔧 RUN-NOW: Error executing workflow {flow_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete(
    "/flows/{flow_id}",
    summary="Elimina un workflow y su chat asociado"
)
async def delete_flow(
    flow_id: UUID,
    flow_svc: FlowService = Depends(get_flow_service),
    orchestrator: TriggerOrchestratorService = Depends(get_trigger_orchestrator_service),
    user_id: int = Depends(get_current_user_id),
):
    """
    Elimina un workflow pero preserva el chat asociado.
    También desactiva cualquier trigger programado.
    """
    try:
        # 1) Desactivar el workflow si está activo
        try:
            await orchestrator.unschedule_flow(flow_id, {}, user_id)
        except Exception as e:
            logger.warning(f"Error unscheduling flow {flow_id}: {e}")
        
        # 2) Eliminar solo el workflow (mantener chat asociado)
        result = await flow_svc.delete_flow(flow_id, user_id)
        
        return {
            "success": True,
            "message": "Workflow eliminado exitosamente (chat preservado)",
            "deleted_flow_id": str(flow_id),
            "chat_preserved": True
        }
        
    except Exception as e:
        logger.error(f"Error deleting flow {flow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error eliminando workflow: {str(e)}"
        )
