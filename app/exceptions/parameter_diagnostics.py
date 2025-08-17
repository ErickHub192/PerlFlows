"""
Herramientas de diagnóstico para problemas de parámetros
"""

from typing import Dict, Any, List
from .parameter_validation import parameter_validator, ValidationResult
from .logging_utils import get_kyra_logger

logger = get_kyra_logger(__name__)


def diagnose_parameter_mismatch(handler_name: str, provided_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Diagnostica problemas de parámetros y proporciona sugerencias
    """
    logger.info(f"Diagnosticando parámetros para handler: {handler_name}")
    
    # Obtener especificaciones del handler
    specs = parameter_validator.get_handler_specs(handler_name)
    
    if not specs:
        return {
            "status": "no_specs",
            "message": f"No hay especificaciones registradas para el handler '{handler_name}'",
            "suggestions": [
                "Verificar que el handler esté correctamente registrado",
                "Añadir decorador @requires_parameters o @validate_params al handler"
            ]
        }
    
    # Validar parámetros
    validation_result = parameter_validator.validate_parameters(handler_name, provided_params)
    
    diagnosis = {
        "handler_name": handler_name,
        "status": "valid" if validation_result.is_valid else "invalid",
        "provided_params": list(provided_params.keys()),
        "required_params": [spec.name for spec in specs if spec.required],
        "optional_params": [spec.name for spec in specs if not spec.required],
        "validation_result": validation_result,
        "suggestions": []
    }
    
    # Generar sugerencias específicas
    if validation_result.missing_required:
        diagnosis["suggestions"].append(
            f"Faltan parámetros requeridos: {', '.join(validation_result.missing_required)}"
        )
    
    if validation_result.invalid_types:
        diagnosis["suggestions"].append(
            f"Tipos de parámetros incorrectos: {', '.join(validation_result.invalid_types)}"
        )
    
    if validation_result.unexpected_params:
        diagnosis["suggestions"].append(
            f"Parámetros inesperados: {', '.join(validation_result.unexpected_params)}"
        )
    
    # Sugerencias para parámetros similares (typos)
    missing_suggestions = _suggest_similar_params(
        validation_result.missing_required, 
        provided_params.keys()
    )
    if missing_suggestions:
        diagnosis["suggestions"].extend(missing_suggestions)
    
    return diagnosis


def _suggest_similar_params(missing_params: List[str], provided_params: List[str]) -> List[str]:
    """
    Sugiere parámetros similares para posibles typos
    """
    suggestions = []
    
    for missing in missing_params:
        for provided in provided_params:
            # Verificar similaridad simple
            if _levenshtein_distance(missing.lower(), provided.lower()) <= 2:
                suggestions.append(f"¿Quisiste decir '{missing}' en lugar de '{provided}'?")
    
    return suggestions


def _levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calcula la distancia de Levenshtein entre dos strings
    """
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def get_handler_parameter_info(handler_name: str) -> Dict[str, Any]:
    """
    Obtiene información completa sobre los parámetros de un handler
    """
    specs = parameter_validator.get_handler_specs(handler_name)
    
    if not specs:
        return {
            "handler_name": handler_name,
            "has_specs": False,
            "message": "No hay especificaciones registradas para este handler"
        }
    
    param_info = []
    for spec in specs:
        param_info.append({
            "name": spec.name,
            "type": str(spec.type_hint),
            "required": spec.required,
            "default": spec.default_value,
            "description": spec.description
        })
    
    return {
        "handler_name": handler_name,
        "has_specs": True,
        "parameter_count": len(specs),
        "required_count": len([s for s in specs if s.required]),
        "optional_count": len([s for s in specs if not s.required]),
        "parameters": param_info
    }


def list_all_registered_handlers() -> Dict[str, Any]:
    """
    Lista todos los handlers registrados y su estado de validación
    """
    from app.connectors.factory import get_registry_status
    
    registry_status = get_registry_status()
    
    handlers_with_specs = []
    handlers_without_specs = []
    
    all_handler_names = registry_status["tool_keys"] + registry_status["node_keys"]
    
    for handler_name in all_handler_names:
        if handler_name in parameter_validator._discovered_handlers:
            specs = parameter_validator.get_handler_specs(handler_name)
            handlers_with_specs.append({
                "name": handler_name,
                "param_count": len(specs),
                "required_count": len([s for s in specs if s.required])
            })
        else:
            handlers_without_specs.append(handler_name)
    
    return {
        "total_handlers": len(all_handler_names),
        "handlers_with_specs": len(handlers_with_specs),
        "handlers_without_specs": len(handlers_without_specs),
        "coverage_percentage": (len(handlers_with_specs) / len(all_handler_names)) * 100 if all_handler_names else 0,
        "handlers_with_validation": handlers_with_specs,
        "handlers_missing_validation": handlers_without_specs,
        "registry_status": registry_status
    }