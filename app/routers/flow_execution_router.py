# app/routers/flow_execution_router.py

from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException

from app.services.flow_execution_service import get_flow_execution_service, FlowExecutionService
from app.dtos.flow_execution_dto import (
    FlowExecutionDTO,
    FlowExecutionDetailDTO,
    FlowExecutionStepDTO,
)

router = APIRouter(prefix="/api/executions", tags=["executions"])


@router.get(
    "/flow/{flow_id}",
    response_model=List[FlowExecutionDTO],
    summary="Listar ejecuciones de un flujo"
)
async def list_executions(
    flow_id: UUID,
    svc: FlowExecutionService = Depends(get_flow_execution_service),
):
    executions = await svc.list_executions(flow_id)
    return [FlowExecutionDTO.model_validate(e) for e in executions]


@router.get(
    "/{execution_id}",
    response_model=FlowExecutionDetailDTO,
    summary="Obtener detalle de una ejecución"
)
async def get_execution_detail(
    execution_id: UUID,
    svc: FlowExecutionService = Depends(get_flow_execution_service),
):
    exec_rec = await svc.get_execution(execution_id)
    if not exec_rec:
        raise HTTPException(status_code=404, detail="Ejecución no encontrada")
    steps = await svc.list_steps(execution_id)
    return FlowExecutionDetailDTO(
        execution=FlowExecutionDTO.model_validate(exec_rec),
        steps=[FlowExecutionStepDTO.model_validate(s) for s in steps]
    )
