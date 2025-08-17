"""
Handler especial que permite a Kyra solicitar input del usuario mediante formularios dinámicos
"""

import time
from typing import Dict, Any
from app.handlers.connector_handler import ActionHandler
from app.connectors.factory import register_tool, register_node
from app.exceptions import requires_parameters, param, RequiresUserInputError
from app.exceptions.logging_utils import get_kyra_logger

logger = get_kyra_logger(__name__)


@register_node("System.request_user_input")
@register_tool("System.request_user_input")
@requires_parameters(
    param("handler_name", str, True, description="Nombre del handler que necesita parámetros"),
    param("message", str, False, description="Mensaje personalizado para el usuario"),
    param("discovered_params", dict, False, {}, "Parámetros que Kyra ya descubrió")
)
class RequestUserInputHandler(ActionHandler):
    """
    Tool especial que Kyra puede usar para solicitar explícitamente input del usuario
    cuando detecta que faltan parámetros para ejecutar otro handler.
    
    Ejemplo de uso por Kyra:
    "Para enviar el mensaje de Telegram necesito que me proporciones el chat_id. 
    Voy a activar un formulario para que lo ingreses."
    """

    def __init__(self, creds: Dict[str, Any]):
        super().__init__(creds)

    async def execute(
        self,
        params: Dict[str, Any],
        creds: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Solicita input del usuario para un handler específico
        """
        start_time = time.perf_counter()
        
        handler_name = params["handler_name"]
        custom_message = params.get("message", "")
        discovered_params = params.get("discovered_params", {})
        
        logger.info(f"Kyra solicita input del usuario para handler: {handler_name}")
        logger.debug(f"Parámetros ya descubiertos", discovered=list(discovered_params.keys()))
        
        try:
            from app.exceptions.smart_parameter_handler import smart_parameter_handler
            
            # Analizar qué parámetros faltan
            missing_info = smart_parameter_handler.get_missing_parameters_info(
                handler_name, discovered_params
            )
            
            # Personalizar el mensaje si Kyra proporcionó uno
            if custom_message:
                missing_info["message"] = custom_message
                missing_info["custom_message"] = True
            else:
                missing_info["custom_message"] = False
            
            # Añadir información adicional para el contexto
            missing_info["requested_by_kyra"] = True
            missing_info["tool_used"] = "System.request_user_input"
            
            logger.info(f"Formulario preparado para {handler_name}",
                       missing_count=missing_info["missing_count"],
                       has_custom_message=bool(custom_message))
            
            # Lanzar la excepción especial que activará el formulario
            raise RequiresUserInputError(handler_name, missing_info)
            
        except RequiresUserInputError:
            # Re-raise para que sea manejado por el sistema de forms
            raise
        except Exception as e:
            logger.error(f"Error procesando solicitud de input del usuario", error=e)
            
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return {
                "status": "error",
                "output": None,
                "error": f"Error preparando formulario para {handler_name}: {str(e)}",
                "duration_ms": duration_ms,
                "handler": "RequestUserInputHandler"
            }


@register_node("System.merge_user_input")
@register_tool("System.merge_user_input")
@requires_parameters(
    param("handler_name", str, True, description="Handler que se va a ejecutar"),
    param("discovered_params", dict, True, description="Parámetros descubiertos por Kyra"),
    param("user_provided_params", dict, True, description="Parámetros proporcionados por el usuario"),
    param("execution_creds", dict, False, {}, "Credenciales para ejecutar el handler")
)
class MergeUserInputHandler(ActionHandler):
    """
    Tool que combina parámetros descubiertos por Kyra con los proporcionados por el usuario
    y ejecuta el handler final.
    """

    def __init__(self, creds: Dict[str, Any]):
        super().__init__(creds)

    async def execute(
        self,
        params: Dict[str, Any],
        creds: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Combina parámetros y ejecuta el handler final
        """
        start_time = time.perf_counter()
        
        handler_name = params["handler_name"]
        discovered = params["discovered_params"]
        user_provided = params["user_provided_params"]
        execution_creds = params.get("execution_creds", creds or {})
        
        logger.info(f"Combinando parámetros para ejecutar {handler_name}")
        logger.debug(f"Parámetros descubiertos: {list(discovered.keys())}")
        logger.debug(f"Parámetros del usuario: {list(user_provided.keys())}")
        
        try:
            from app.exceptions.smart_parameter_handler import smart_parameter_handler
            from app.connectors.factory import execute_tool, execute_node
            
            # Combinar parámetros (usuario tiene prioridad)
            final_params = smart_parameter_handler.merge_parameters(discovered, user_provided)
            
            logger.info(f"Parámetros combinados para {handler_name}", 
                       total_params=len(final_params))
            
            # Intentar ejecutar como tool primero, luego como nodo
            try:
                result = await execute_tool(handler_name, final_params, execution_creds)
                execution_type = "tool"
            except (ValueError, RuntimeError):
                # Si falla como tool, intentar como nodo
                if "." in handler_name:
                    node_name, action_name = handler_name.split(".", 1)
                    result = await execute_node(node_name, action_name, final_params, execution_creds)
                    execution_type = "node"
                else:
                    raise ValueError(f"No se pudo ejecutar {handler_name} como tool o nodo")
            
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            
            logger.info(f"Handler {handler_name} ejecutado exitosamente como {execution_type}")
            
            # Envolver el resultado para indicar que fue ejecutado vía merge
            return {
                "status": "success",
                "output": result,
                "execution_type": execution_type,
                "handler_name": handler_name,
                "merged_params_count": len(final_params),
                "duration_ms": duration_ms,
                "handler": "MergeUserInputHandler"
            }
            
        except Exception as e:
            logger.error(f"Error ejecutando {handler_name} con parámetros combinados", error=e)
            
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return {
                "status": "error",
                "output": None,
                "error": f"Error ejecutando {handler_name}: {str(e)}",
                "duration_ms": duration_ms,
                "handler": "MergeUserInputHandler"
            }