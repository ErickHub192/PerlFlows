"""
Decoradores para validación de parámetros en handlers
"""

from typing import Any, Dict, List, Type, Optional
from functools import wraps
from .parameter_validation import ParameterSpec, parameter_validator, ParameterValidationError
from .logging_utils import get_kyra_logger

logger = get_kyra_logger(__name__)


def param(name: str, param_type: Type = Any, required: bool = True, 
          default: Any = None, description: str = None):
    """Helper para crear ParameterSpec fácilmente"""
    return ParameterSpec(
        name=name,
        type_hint=param_type,
        required=required,
        default_value=default,
        description=description
    )


def requires_parameters(*param_specs: ParameterSpec):
    """Decorador para especificar parámetros requeridos"""
    def decorator(cls):
        handler_name = getattr(cls, '__name__', str(cls))
        parameter_validator._handler_specs[handler_name] = list(param_specs)
        parameter_validator._discovered_handlers.add(handler_name)
        logger.info(f"Registradas especificaciones para {handler_name}: {len(param_specs)} parámetros")
        return cls
    return decorator


def validate_params(strict_mode: bool = False):
    """Decorador para validar parámetros automáticamente"""
    def decorator(cls):
        original_execute = cls.execute
        handler_name = getattr(cls, '__name__', str(cls))
        
        # Auto-descubrir parámetros
        parameter_validator.register_handler_specs(handler_name, cls)
        
        @wraps(original_execute)
        async def validated_execute(self, params: Dict[str, Any], creds: Dict[str, Any] = None):
            # Validar parámetros
            validation_result = parameter_validator.validate_parameters(
                handler_name, params, strict_mode
            )
            
            if not validation_result.is_valid:
                raise ParameterValidationError(handler_name, validation_result)
            
            # Ejecutar método original
            return await original_execute(self, params, creds)
        
        cls.execute = validated_execute
        return cls
    return decorator