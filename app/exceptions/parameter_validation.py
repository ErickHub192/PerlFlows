"""
Sistema de validación de parámetros para handlers en Kyra
Valida que los parámetros enviados coincidan con los esperados por cada handler
"""

import inspect
from typing import Any, Dict, List, Optional, Set, Union, Type, get_type_hints
from dataclasses import dataclass
from app.exceptions.logging_utils import get_kyra_logger, error_tracker

logger = get_kyra_logger(__name__)


@dataclass
class ParameterSpec:
    """Especificación de un parámetro esperado por un handler"""
    name: str
    type_hint: Type
    required: bool
    default_value: Any = None
    description: Optional[str] = None


@dataclass
class ValidationResult:
    """Resultado de la validación de parámetros"""
    is_valid: bool
    missing_required: List[str] = None
    invalid_types: List[str] = None
    unexpected_params: List[str] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.missing_required is None:
            self.missing_required = []
        if self.invalid_types is None:
            self.invalid_types = []
        if self.unexpected_params is None:
            self.unexpected_params = []
        if self.errors is None:
            self.errors = []


class ParameterValidationError(Exception):
    """Error específico para problemas de validación de parámetros"""
    
    def __init__(self, handler_name: str, validation_result: ValidationResult):
        self.handler_name = handler_name
        self.validation_result = validation_result
        
        # Construir mensaje detallado
        error_parts = [f"Parameter validation failed for handler '{handler_name}'"]
        
        if validation_result.missing_required:
            error_parts.append(f"Missing required parameters: {validation_result.missing_required}")
        
        if validation_result.invalid_types:
            error_parts.append(f"Invalid parameter types: {validation_result.invalid_types}")
        
        if validation_result.unexpected_params:
            error_parts.append(f"Unexpected parameters: {validation_result.unexpected_params}")
        
        if validation_result.errors:
            error_parts.extend(validation_result.errors)
        
        message = ". ".join(error_parts)
        super().__init__(message)
        
        # Auto-log del error
        context = {
            "handler_name": handler_name,
            "missing_required": validation_result.missing_required,
            "invalid_types": validation_result.invalid_types,
            "unexpected_params": validation_result.unexpected_params,
            "validation_errors": validation_result.errors
        }
        
        error_tracker.track_error(
            error=self,
            component="PARAMETER_VALIDATOR",
            operation="parameter_validation",
            context=context
        )


class ParameterValidator:
    """
    Validador genérico de parámetros para handlers
    """
    
    def __init__(self):
        self._handler_specs: Dict[str, List[ParameterSpec]] = {}
        self._discovered_handlers: Set[str] = set()
    
    def discover_handler_parameters(self, handler_class: Type, handler_name: str) -> List[ParameterSpec]:
        """
        Auto-descubre los parámetros esperados por un handler analizando su método execute
        """
        logger.debug(f"Descubriendo parámetros para handler: {handler_name}")
        
        try:
            # Obtener el método execute
            execute_method = getattr(handler_class, 'execute', None)
            if not execute_method:
                logger.warning(f"Handler {handler_name} no tiene método execute")
                return []
            
            # Obtener la signatura del método
            sig = inspect.signature(execute_method)
            
            # Obtener type hints si están disponibles
            try:
                type_hints = get_type_hints(execute_method)
            except Exception as e:
                logger.debug(f"No se pudieron obtener type hints para {handler_name}: {e}")
                type_hints = {}
            
            specs = []
            
            # Analizar cada parámetro (excepto self, params y creds que son estándar)
            for param_name, param in sig.parameters.items():
                if param_name in ['self', 'params', 'creds']:
                    continue
                
                # Determinar tipo
                param_type = type_hints.get(param_name, Any)
                
                # Determinar si es requerido
                required = param.default == inspect.Parameter.empty
                default_value = param.default if not required else None
                
                spec = ParameterSpec(
                    name=param_name,
                    type_hint=param_type,
                    required=required,
                    default_value=default_value
                )
                specs.append(spec)
            
            # También intentar extraer parámetros del docstring si existe
            docstring_params = self._extract_params_from_docstring(execute_method)
            self._merge_docstring_info(specs, docstring_params)
            
            logger.info(f"Descubiertos {len(specs)} parámetros para {handler_name}")
            return specs
            
        except Exception as e:
            logger.error(f"Error descubriendo parámetros para {handler_name}", error=e)
            return []
    
    def _extract_params_from_docstring(self, method) -> Dict[str, str]:
        """
        Extrae información de parámetros del docstring del método
        """
        docstring_params = {}
        
        if not method.__doc__:
            return docstring_params
        
        lines = method.__doc__.split('\n')
        in_params_section = False
        
        for line in lines:
            line = line.strip()
            
            # Detectar sección de parámetros
            if 'parámetros' in line.lower() or 'parameters' in line.lower():
                in_params_section = True
                continue
            
            # Si estamos en la sección de parámetros
            if in_params_section and line:
                # Buscar patrón como "- param_name (type): description"
                if line.startswith('-') or line.startswith('*'):
                    parts = line[1:].strip().split(':', 1)
                    if len(parts) == 2:
                        param_part = parts[0].strip()
                        description = parts[1].strip()
                        
                        # Extraer nombre del parámetro (remover tipo si existe)
                        param_name = param_part.split('(')[0].strip()
                        docstring_params[param_name] = description
            
            # Salir de la sección si encontramos otra sección
            elif in_params_section and (line.startswith('Returns') or line.startswith('Raises')):
                break
        
        return docstring_params
    
    def _merge_docstring_info(self, specs: List[ParameterSpec], docstring_params: Dict[str, str]):
        """
        Merge información del docstring con las especificaciones de parámetros
        """
        for spec in specs:
            if spec.name in docstring_params:
                spec.description = docstring_params[spec.name]
    
    def register_handler_specs(self, handler_name: str, handler_class: Type):
        """
        Registra las especificaciones de parámetros para un handler
        """
        if handler_name not in self._discovered_handlers:
            specs = self.discover_handler_parameters(handler_class, handler_name)
            self._handler_specs[handler_name] = specs
            self._discovered_handlers.add(handler_name)
            
            logger.info(f"Registradas especificaciones para handler: {handler_name}")
    
    def validate_parameters(self, handler_name: str, provided_params: Dict[str, Any], 
                          strict_mode: bool = False) -> ValidationResult:
        """
        Valida los parámetros proporcionados contra las especificaciones del handler
        
        Args:
            handler_name: Nombre del handler
            provided_params: Parámetros proporcionados
            strict_mode: Si True, rechaza parámetros no esperados
        """
        logger.debug(f"Validando parámetros para handler: {handler_name}")
        
        result = ValidationResult(is_valid=True)
        
        # Si no tenemos specs para este handler, solo log
        if handler_name not in self._handler_specs:
            logger.warning(f"No hay especificaciones registradas para handler: {handler_name}")
            return result
        
        specs = self._handler_specs[handler_name]
        expected_params = {spec.name: spec for spec in specs}
        
        # 1. Verificar parámetros requeridos faltantes
        for spec in specs:
            if spec.required and spec.name not in provided_params:
                result.missing_required.append(spec.name)
                result.is_valid = False
        
        # 2. Verificar tipos de parámetros proporcionados
        for param_name, param_value in provided_params.items():
            if param_name in expected_params:
                spec = expected_params[param_name]
                if not self._validate_type(param_value, spec.type_hint):
                    result.invalid_types.append(f"{param_name} (expected {spec.type_hint}, got {type(param_value)})")
                    result.is_valid = False
            elif strict_mode:
                result.unexpected_params.append(param_name)
                result.is_valid = False
        
        # 3. Log de resultados
        if not result.is_valid:
            logger.warning(f"Validación falló para {handler_name}", 
                         missing=result.missing_required,
                         invalid_types=result.invalid_types,
                         unexpected=result.unexpected_params)
        else:
            logger.debug(f"Validación exitosa para {handler_name}")
        
        return result
    
    def _validate_type(self, value: Any, expected_type: Type) -> bool:
        """
        Valida si un valor coincide con el tipo esperado
        """
        if expected_type == Any:
            return True
        
        # Manejar tipos básicos
        if expected_type in [str, int, float, bool, list, dict]:
            return isinstance(value, expected_type)
        
        # Manejar Union types (como Optional)
        if hasattr(expected_type, '__origin__'):
            if expected_type.__origin__ is Union:
                return any(self._validate_type(value, arg) for arg in expected_type.__args__)
        
        # Manejar None para Optional
        if value is None and hasattr(expected_type, '__args__') and type(None) in expected_type.__args__:
            return True
        
        # Por defecto, aceptar el valor (mejor que fallar)
        return True
    
    def get_handler_specs(self, handler_name: str) -> List[ParameterSpec]:
        """
        Obtiene las especificaciones de parámetros para un handler
        """
        return self._handler_specs.get(handler_name, [])
    
    def get_required_parameters(self, handler_name: str) -> List[str]:
        """
        Obtiene la lista de parámetros requeridos para un handler
        """
        specs = self.get_handler_specs(handler_name)
        return [spec.name for spec in specs if spec.required]
    
    def get_all_parameters(self, handler_name: str) -> List[str]:
        """
        Obtiene la lista de todos los parámetros para un handler
        """
        specs = self.get_handler_specs(handler_name)
        return [spec.name for spec in specs]


# Instancia global del validador
parameter_validator = ParameterValidator()