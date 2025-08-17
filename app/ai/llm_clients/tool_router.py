# app/ai/tool_router.py

from typing import Any, Dict
from app.connectors.factory import get_tool_handler
from app.exceptions.parameter_validation import parameter_validator, ParameterValidationError
from app.exceptions.smart_parameter_handler import smart_parameter_handler
from app.exceptions.logging_utils import get_kyra_logger

logger = get_kyra_logger(__name__)

class ToolRouter:
    """
    Encapsula la lógica de enrutamiento de llamadas a conectores de herramientas externas.
    """

    async def call(
        self,
        tool_name: str,
        params: Dict[str, Any],
        creds: Dict[str, Any]
    ) -> Any:
        """
        Dado el nombre de la herramienta, los parámetros y credenciales,
        obtiene el handler apropiado desde la fábrica y ejecuta la acción.

        :param tool_name: Identificador de la herramienta (p.ej. 'google_sheets', 'gmail_send').
        :param params:   Parámetros específicos de la herramienta.
        :param creds:    Credenciales o contexto necesarios para inicializar el handler.
        :return:         El resultado que devuelva el handler (puede ser dict, objeto, etc.).
        :raises:         Cualquier excepción de get_handler o de handler.execute.
        """
        logger.debug(f"Llamando tool: {tool_name}", provided_params=list(params.keys()))
        
        # Obtener handler
        handler = get_tool_handler(tool_name, creds)
        
        # Validar parámetros antes de ejecutar
        try:
            validation_result = parameter_validator.validate_parameters(
                tool_name, params, strict_mode=False
            )
            
            if not validation_result.is_valid:
                logger.warning(f"Validación de parámetros falló para {tool_name}",
                             missing=validation_result.missing_required,
                             invalid_types=validation_result.invalid_types)
                raise ParameterValidationError(tool_name, validation_result)
            
            logger.debug(f"Parámetros validados para {tool_name}")
            
        except ParameterValidationError:
            # Re-raise validation errors
            raise
        except Exception as e:
            # Si la validación falla por otro motivo, log pero continúa
            logger.warning(f"Error en validación de parámetros para {tool_name}", error=e)
        
        # Ejecutar handler
        return await handler.execute(params, creds)

    def is_registered(self, tool_name: str) -> bool:
        """Return True if a tool handler is registered for the given name."""
        from app.connectors.factory import _TOOL_REGISTRY
        return tool_name in _TOOL_REGISTRY
