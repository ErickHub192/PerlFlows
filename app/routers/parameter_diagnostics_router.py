"""
Router para diagnóstico de parámetros de handlers
Útil para debugging y desarrollo
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.exceptions.parameter_diagnostics import (
    diagnose_parameter_mismatch,
    get_handler_parameter_info,
    list_all_registered_handlers
)
from app.exceptions.logging_utils import get_kyra_logger

logger = get_kyra_logger(__name__)

router = APIRouter(prefix="/api/diagnostics", tags=["diagnostics"])


class ParameterDiagnosisRequest(BaseModel):
    handler_name: str
    provided_params: Dict[str, Any]


@router.post("/parameters/diagnose")
async def diagnose_parameters(request: ParameterDiagnosisRequest):
    """
    Diagnostica problemas de parámetros para un handler específico
    """
    logger.info(f"Diagnosticando parámetros para handler: {request.handler_name}")
    
    try:
        diagnosis = diagnose_parameter_mismatch(
            request.handler_name, 
            request.provided_params
        )
        
        logger.info(f"Diagnóstico completado para {request.handler_name}")
        return diagnosis
        
    except Exception as e:
        logger.error(f"Error en diagnóstico de parámetros", error=e)
        raise HTTPException(status_code=500, detail=f"Error en diagnóstico: {str(e)}")


@router.get("/parameters/handler/{handler_name}")
async def get_handler_parameters(handler_name: str):
    """
    Obtiene información detallada sobre los parámetros de un handler
    """
    logger.info(f"Obteniendo información de parámetros para: {handler_name}")
    
    try:
        info = get_handler_parameter_info(handler_name)
        
        if not info["has_specs"]:
            raise HTTPException(
                status_code=404, 
                detail=f"No hay especificaciones registradas para el handler '{handler_name}'"
            )
        
        return info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo información de parámetros", error=e)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/handlers/registry")
async def get_handlers_registry(
    include_missing: bool = Query(True, description="Incluir handlers sin validación")
):
    """
    Lista todos los handlers registrados y su estado de validación
    """
    logger.info("Obteniendo registro de handlers")
    
    try:
        registry_info = list_all_registered_handlers()
        
        if not include_missing:
            # Remover handlers sin especificaciones si no se solicitan
            registry_info.pop("handlers_missing_validation", None)
        
        return registry_info
        
    except Exception as e:
        logger.error(f"Error obteniendo registro de handlers", error=e)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/parameters/coverage")
async def get_parameter_coverage():
    """
    Obtiene estadísticas de cobertura de validación de parámetros
    """
    logger.info("Calculando cobertura de validación de parámetros")
    
    try:
        registry_info = list_all_registered_handlers()
        
        coverage = {
            "total_handlers": registry_info["total_handlers"],
            "handlers_with_validation": registry_info["handlers_with_specs"],
            "handlers_without_validation": registry_info["handlers_without_specs"],
            "coverage_percentage": registry_info["coverage_percentage"],
            "coverage_status": "good" if registry_info["coverage_percentage"] >= 80 else 
                              "fair" if registry_info["coverage_percentage"] >= 50 else "poor"
        }
        
        return coverage
        
    except Exception as e:
        logger.error(f"Error calculando cobertura", error=e)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/parameters/validate")
async def validate_handler_parameters(request: ParameterDiagnosisRequest):
    """
    Valida parámetros para un handler sin ejecutarlo
    """
    logger.info(f"Validando parámetros para handler: {request.handler_name}")
    
    try:
        from app.exceptions.parameter_validation import parameter_validator
        
        validation_result = parameter_validator.validate_parameters(
            request.handler_name,
            request.provided_params,
            strict_mode=True
        )
        
        response = {
            "handler_name": request.handler_name,
            "is_valid": validation_result.is_valid,
            "provided_params": list(request.provided_params.keys()),
            "missing_required": validation_result.missing_required,
            "invalid_types": validation_result.invalid_types,
            "unexpected_params": validation_result.unexpected_params,
            "errors": validation_result.errors
        }
        
        logger.info(f"Validación completada para {request.handler_name}: {'válida' if validation_result.is_valid else 'inválida'}")
        return response
        
    except Exception as e:
        logger.error(f"Error en validación de parámetros", error=e)
        raise HTTPException(status_code=500, detail=f"Error en validación: {str(e)}")