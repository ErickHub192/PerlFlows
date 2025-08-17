"""
Sistema inteligente que combina discovery automático con forms dinámicos
Solo solicita al usuario los parámetros que Kyra no pudo descubrir
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from .parameter_validation import parameter_validator, ValidationResult
from .logging_utils import get_kyra_logger

logger = get_kyra_logger(__name__)


class ParameterStatus(Enum):
    DISCOVERED = "discovered"      # Kyra lo descubrió automáticamente
    MISSING = "missing"           # Falta y necesita input del usuario
    PROVIDED = "provided"         # Usuario ya lo proporcionó
    INVALID = "invalid"           # Presente pero con tipo incorrecto


@dataclass
class ParameterAnalysis:
    """Análisis de parámetros: qué tiene Kyra vs qué falta"""
    handler_name: str
    discovered_params: Dict[str, Any]
    missing_params: List[str]
    invalid_params: List[str]
    needs_user_input: bool
    form_schema: Optional[Dict[str, Any]] = None


class SmartParameterHandler:
    """
    Maneja inteligentemente la combinación de discovery + forms dinámicos
    """
    
    def __init__(self):
        self.logger = get_kyra_logger(__name__)
    
    def analyze_parameters(self, handler_name: str, kyra_discovered: Dict[str, Any]) -> ParameterAnalysis:
        """
        Analiza qué parámetros descubrió Kyra vs qué falta para el handler
        """
        self.logger.info(f"Analizando parámetros para {handler_name}")
        self.logger.debug(f"Parámetros descubiertos por Kyra", discovered=list(kyra_discovered.keys()))
        
        # Obtener especificaciones del handler
        handler_specs = parameter_validator.get_handler_specs(handler_name)
        
        if not handler_specs:
            self.logger.warning(f"No hay especificaciones para {handler_name}")
            return ParameterAnalysis(
                handler_name=handler_name,
                discovered_params=kyra_discovered,
                missing_params=[],
                invalid_params=[],
                needs_user_input=False
            )
        
        # Analizar cada parámetro requerido
        missing_params = []
        invalid_params = []
        
        for spec in handler_specs:
            if spec.required:
                if spec.name not in kyra_discovered:
                    # Kyra no lo descubrió
                    missing_params.append(spec.name)
                    self.logger.debug(f"Parámetro faltante: {spec.name}")
                else:
                    # Kyra lo descubrió, verificar si es válido
                    value = kyra_discovered[spec.name]
                    if not self._validate_parameter_type(value, spec.type_hint):
                        invalid_params.append(spec.name)
                        self.logger.debug(f"Parámetro inválido: {spec.name}")
        
        needs_input = len(missing_params) > 0 or len(invalid_params) > 0
        
        # Generar schema del form solo para parámetros faltantes/inválidos
        form_schema = None
        if needs_input:
            form_schema = self._generate_form_schema_for_missing(
                handler_name, handler_specs, missing_params + invalid_params
            )
        
        analysis = ParameterAnalysis(
            handler_name=handler_name,
            discovered_params=kyra_discovered,
            missing_params=missing_params,
            invalid_params=invalid_params,
            needs_user_input=needs_input,
            form_schema=form_schema
        )
        
        self.logger.info(f"Análisis completado para {handler_name}", 
                        missing_count=len(missing_params),
                        invalid_count=len(invalid_params),
                        needs_input=needs_input)
        
        return analysis
    
    def _validate_parameter_type(self, value: Any, expected_type: type) -> bool:
        """Valida si un valor tiene el tipo esperado"""
        try:
            if expected_type == Any:
                return True
            
            # Validaciones básicas
            if expected_type in [str, int, float, bool, list, dict]:
                return isinstance(value, expected_type)
            
            # Por defecto aceptar (mejor que rechazar incorrectamente)
            return True
            
        except Exception:
            return True  # En caso de duda, aceptar
    
    def _generate_form_schema_for_missing(self, handler_name: str, all_specs: List, missing_param_names: List[str]) -> Dict[str, Any]:
        """
        Genera JSON Schema solo para los parámetros que faltan
        """
        properties = {}
        required = []
        
        for spec in all_specs:
            if spec.name in missing_param_names:
                # Solo incluir parámetros que realmente faltan
                param_schema = {
                    "type": self._map_python_type_to_json_schema(spec.type_hint),
                    "title": spec.description or spec.name.replace("_", " ").title()
                }
                
                # Añadir información adicional si está disponible
                if spec.description:
                    param_schema["description"] = spec.description
                
                if spec.default_value is not None:
                    param_schema["default"] = spec.default_value
                
                properties[spec.name] = param_schema
                
                if spec.required:
                    required.append(spec.name)
        
        schema = {
            "title": f"Parámetros faltantes para {handler_name}",
            "description": f"Kyra necesita que proporciones los siguientes parámetros que no pudo descubrir automáticamente",
            "type": "object",
            "properties": properties,
            "required": required
        }
        
        self.logger.debug(f"Schema generado para parámetros faltantes", param_count=len(properties))
        return schema
    
    def _map_python_type_to_json_schema(self, python_type: type) -> str:
        """Mapea tipos de Python a tipos de JSON Schema"""
        type_mapping = {
            str: "string",
            int: "integer", 
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object"
        }
        
        return type_mapping.get(python_type, "string")  # Default a string
    
    def merge_parameters(self, discovered: Dict[str, Any], user_provided: Dict[str, Any]) -> Dict[str, Any]:
        """
        Combina parámetros descubiertos por Kyra con los proporcionados por el usuario
        Los parámetros del usuario tienen prioridad en caso de conflicto
        """
        merged = discovered.copy()
        merged.update(user_provided)
        
        self.logger.debug(f"Parámetros combinados", 
                         discovered_count=len(discovered),
                         user_count=len(user_provided),
                         total_count=len(merged))
        
        return merged
    
    def should_request_user_input(self, handler_name: str, kyra_params: Dict[str, Any]) -> bool:
        """
        Determina si se necesita solicitar input del usuario
        """
        analysis = self.analyze_parameters(handler_name, kyra_params)
        return analysis.needs_user_input
    
    def get_missing_parameters_info(self, handler_name: str, kyra_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Obtiene información detallada sobre parámetros faltantes para mostrar al usuario
        """
        analysis = self.analyze_parameters(handler_name, kyra_params)
        
        return {
            "handler_name": handler_name,
            "total_required": len(parameter_validator.get_required_parameters(handler_name)),
            "discovered_by_kyra": len(analysis.discovered_params),
            "missing_count": len(analysis.missing_params),
            "missing_params": analysis.missing_params,
            "invalid_params": analysis.invalid_params,
            "form_schema": analysis.form_schema,
            "message": self._generate_user_message(analysis)
        }
    
    def _generate_user_message(self, analysis: ParameterAnalysis) -> str:
        """
        Genera un mensaje descriptivo para el usuario
        """
        if not analysis.needs_user_input:
            return f"Todos los parámetros para {analysis.handler_name} fueron descubiertos automáticamente."
        
        discovered_count = len(analysis.discovered_params)
        missing_count = len(analysis.missing_params)
        
        message = f"Para ejecutar {analysis.handler_name}:\n"
        
        if discovered_count > 0:
            message += f"✅ Kyra descubrió automáticamente {discovered_count} parámetros\n"
        
        if missing_count > 0:
            message += f"❓ Necesito que proporciones {missing_count} parámetros adicionales: {', '.join(analysis.missing_params)}"
        
        return message


# Instancia global
smart_parameter_handler = SmartParameterHandler()