# app/routers/parameter_router.py

from fastapi import APIRouter, Depends, HTTPException, Path
from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.parameter_service import get_parameter_service
from app.repositories.iparameter_repository import IParameterRepository
from app.repositories.parameter_repository import ParameterRepository
from app.services.iparameter_service import IParameterService
from app.services.parameter_service import ParameterService
from app.dtos.parameter_dto import ActionParamDTO

router = APIRouter(prefix="/parameters", tags=["parameters"])



@router.get(
    "/{action_id}/",
    response_model=List[ActionParamDTO],
    summary="Recupera los parámetros de una acción por su ID"
)
async def list_parameters_for_action(
    action_id: UUID = Path(..., description="UUID de action cuyos parámetros quieres obtener"),
    svc: ParameterService = Depends(get_parameter_service),
):
    try:
        params = await svc.list_parameters(action_id)
        return [ActionParamDTO.model_validate(p) for p in params]
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
