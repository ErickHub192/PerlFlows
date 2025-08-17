"""
Servicio inteligente de formularios que combina:
1. Sistema tradicional: Parámetros de BD → JSON Schema
2. Sistema nuevo: Discovery + parámetros faltantes → JSON Schema dinámico
"""

from typing import Dict, Any, List, Optional
from uuid import UUID
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .ISmartFormService import ISmartFormService
from .iparameter_service import IParameterService
from .parameter_service import get_parameter_service
from app.dtos.form_schema_dto import FormSchemaDTO
from app.dtos.parameter_dto import ActionParamDTO
from app.exceptions.smart_parameter_handler import smart_parameter_handler
from app.exceptions.logging_utils import get_kyra_logger
from app.connectors.factory import execute_tool, execute_node
from app.db.database import get_db

logger = get_kyra_logger(__name__)


class SmartFormService(ISmartFormService):
    """
    Servicio que combina formularios tradicionales (BD) con formularios inteligentes (discovery)
    """
    
    def __init__(self, parameter_service: IParameterService):
        self.parameter_service = parameter_service
    
    async def analyze_handler_parameters(self, handler_name: str, discovered_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analiza qué parámetros faltan comparando discovery vs especificaciones
        """
        logger.info(f"Analizando parámetros para handler: {handler_name}")
        logger.debug(f"Parámetros descubiertos", discovered=list(discovered_params.keys()))
        
        try:
            analysis = smart_parameter_handler.analyze_parameters(handler_name, discovered_params)
            
            return {
                "handler_name": analysis.handler_name,
                "needs_user_input": analysis.needs_user_input,
                "discovered_params": list(analysis.discovered_params.keys()),
                "missing_params": analysis.missing_params,
                "invalid_params": analysis.invalid_params,
                "analysis_source": "smart_discovery"
            }
            
        except Exception as e:
            logger.error(f"Error en análisis de parámetros para {handler_name}", error=e)
            raise
    
    async def get_missing_parameters_form(self, handler_name: str, discovered_params: Dict[str, Any]) -> Optional[FormSchemaDTO]:
        """
        Genera formulario solo para parámetros que Kyra no pudo descubrir
        """
        logger.info(f"Generando formulario para parámetros faltantes: {handler_name}")
        
        try:
            missing_info = smart_parameter_handler.get_missing_parameters_info(handler_name, discovered_params)
            
            if not missing_info.get("form_schema"):
                logger.debug(f"No se requiere formulario para {handler_name}")
                return None
            
            # Convertir el schema generado a FormSchemaDTO
            schema_dict = missing_info["form_schema"]
            form_schema = FormSchemaDTO(**schema_dict)
            
            logger.info(f"Formulario generado para {handler_name}", 
                       missing_count=missing_info["missing_count"])
            
            return form_schema
            
        except Exception as e:
            logger.error(f"Error generando formulario para {handler_name}", error=e)
            raise
    
    async def get_traditional_form_by_action(self, action_id: UUID) -> FormSchemaDTO:
        """
        Genera formulario tradicional basado en parámetros de BD (flujo original)
        MANTIENE COMPATIBILIDAD con el sistema existente
        """
        logger.info(f"Generando formulario tradicional para action_id: {action_id}")
        
        try:
            # Usar el servicio existente para obtener parámetros de BD
            params = await self.parameter_service.list_parameters(action_id)
            
            if not params:
                raise ValueError(f"No se encontraron parámetros para action_id {action_id}")
            
            # Convertir parámetros de BD a JSON Schema (flujo original)
            properties = {}
            required = []
            
            for param in params:
                param_schema = {
                    "type": self._map_param_type_to_json_schema(param.param_type),
                    "title": param.description or param.name.replace("_", " ").title()
                }
                
                if param.description:
                    param_schema["description"] = param.description
                
                if param.default is not None:
                    param_schema["default"] = param.default
                
                if param.options:
                    param_schema["enum"] = param.options
                
                properties[param.name] = param_schema
                
                if param.required:
                    required.append(param.name)
            
            schema_dict = {
                "title": f"Formulario para acción {action_id}",
                "type": "object", 
                "properties": properties,
                "required": required
            }
            
            logger.info(f"Formulario tradicional generado para action_id {action_id}",
                       param_count=len(properties))
            
            return FormSchemaDTO(**schema_dict)
            
        except Exception as e:
            logger.error(f"Error generando formulario tradicional para action_id {action_id}", error=e)
            raise
    
    async def merge_and_execute_handler(
        self, 
        handler_name: str, 
        discovered_params: Dict[str, Any],
        user_provided_params: Dict[str, Any],
        execution_creds: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Combina parámetros y ejecuta el handler
        """
        logger.info(f"Ejecutando {handler_name} con parámetros combinados")
        logger.debug(f"Parámetros descubiertos: {list(discovered_params.keys())}")
        logger.debug(f"Parámetros del usuario: {list(user_provided_params.keys())}")
        
        try:
            # Combinar parámetros (usuario tiene prioridad)
            final_params = smart_parameter_handler.merge_parameters(discovered_params, user_provided_params)
            
            logger.debug(f"Parámetros finales: {list(final_params.keys())}")
            
            # Intentar ejecutar como tool primero, luego como nodo
            execution_result = await self._execute_handler_with_fallback(
                handler_name, final_params, execution_creds
            )
            
            return {
                "status": "success",
                "execution_result": execution_result["result"],
                "execution_type": execution_result["type"],
                "merged_params_count": len(final_params),
                "handler_name": handler_name
            }
            
        except Exception as e:
            logger.error(f"Error ejecutando {handler_name} con parámetros combinados", error=e)
            return {
                "status": "error",
                "error": str(e),
                "handler_name": handler_name
            }
    
    async def should_use_smart_form(self, handler_name: str) -> bool:
        """
        Determina si usar sistema inteligente o tradicional
        """
        try:
            # Si el handler tiene especificaciones registradas, usar sistema inteligente
            from app.exceptions.parameter_validation import parameter_validator
            specs = parameter_validator.get_handler_specs(handler_name)
            
            use_smart = len(specs) > 0
            logger.debug(f"Handler {handler_name} usará {'smart' if use_smart else 'traditional'} forms")
            
            return use_smart
            
        except Exception as e:
            logger.warning(f"Error determinando tipo de form para {handler_name}", error=e)
            # En caso de duda, usar tradicional
            return False
    
    def _map_param_type_to_json_schema(self, param_type: str) -> str:
        """
        Mapea tipos de parámetros de BD a tipos JSON Schema
        """
        type_mapping = {
            "string": "string",
            "integer": "integer",
            "number": "number", 
            "boolean": "boolean",
            "array": "array",
            "object": "object",
            "enum": "string",  # enum se maneja con property "enum"
            "select": "string"  # select se maneja con property "enum"
        }
        
        return type_mapping.get(param_type.lower(), "string")
    
    async def _execute_handler_with_fallback(self, handler_name: str, params: Dict[str, Any], creds: Dict[str, Any]) -> Dict[str, Any]:
        """
        Intenta ejecutar handler como tool, si falla como nodo
        """
        try:
            result = await execute_tool(handler_name, params, creds)
            return {"result": result, "type": "tool"}
            
        except (ValueError, RuntimeError):
            # Si falla como tool, intentar como nodo
            if "." in handler_name:
                node_name, action_name = handler_name.split(".", 1)
                result = await execute_node(node_name, action_name, params, creds)
                return {"result": result, "type": "node"}
            else:
                raise ValueError(f"No se pudo ejecutar {handler_name} como tool o nodo")


async def get_smart_form_service(
    parameter_service: IParameterService = Depends(get_parameter_service)
) -> ISmartFormService:
    """
    Factory para inyección de dependencias
    """
    return SmartFormService(parameter_service)