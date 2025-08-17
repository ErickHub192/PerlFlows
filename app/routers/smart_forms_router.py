"""
Router para formularios inteligentes - SOLO ORQUESTACIÓN
"""

from typing import Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.services.ISmartFormService import ISmartFormService
from app.services.smart_form_service import get_smart_form_service
from app.dtos.form_schema_dto import FormSchemaDTO

router = APIRouter(prefix="/api/smart-forms", tags=["smart-forms"])


class ParameterAnalysisRequest(BaseModel):
    handler_name: str
    discovered_params: Dict[str, Any]


class ExecuteWithUserInputRequest(BaseModel):
    handler_name: str
    discovered_params: Dict[str, Any]
    user_provided_params: Dict[str, Any]
    execution_creds: Dict[str, Any] = {}


@router.post("/analyze")
async def analyze_handler_parameters(
    request: ParameterAnalysisRequest,
    form_service: ISmartFormService = Depends(get_smart_form_service)
):
    """Analiza qué parámetros faltan"""
    return await form_service.analyze_handler_parameters(
        request.handler_name, 
        request.discovered_params
    )


@router.post("/get-missing-form", response_model=FormSchemaDTO)
async def get_missing_parameters_form(
    request: ParameterAnalysisRequest,
    form_service: ISmartFormService = Depends(get_smart_form_service)
):
    """Obtiene formulario para parámetros faltantes"""
    return await form_service.get_missing_parameters_form(
        request.handler_name,
        request.discovered_params
    )


@router.get("/traditional-form", response_model=FormSchemaDTO)
async def get_traditional_form_by_action(
    action_id: UUID = Query(...),
    form_service: ISmartFormService = Depends(get_smart_form_service)
):
    """Formulario tradicional basado en BD"""
    return await form_service.get_traditional_form_by_action(action_id)


@router.post("/execute-with-user-input")
async def execute_handler_with_user_input(
    request: ExecuteWithUserInputRequest,
    form_service: ISmartFormService = Depends(get_smart_form_service)
):
    """Ejecuta handler con parámetros combinados"""
    return await form_service.merge_and_execute_handler(
        request.handler_name,
        request.discovered_params,
        request.user_provided_params,
        request.execution_creds
    )


@router.get("/should-use-smart/{handler_name}")
async def should_use_smart_form(
    handler_name: str,
    form_service: ISmartFormService = Depends(get_smart_form_service)
):
    """Determina tipo de formulario a usar"""
    use_smart = await form_service.should_use_smart_form(handler_name)
    return {
        "handler_name": handler_name,
        "use_smart_form": use_smart,
        "form_type": "smart" if use_smart else "traditional"
    }