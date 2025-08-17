"""
Excepción especial para cuando se requiere input del usuario
"""

from typing import Dict, Any
from .logging_utils import get_kyra_logger, error_tracker

logger = get_kyra_logger(__name__)


class RequiresUserInputError(Exception):
    """
    Excepción especial que indica que se necesita input del usuario
    para completar la ejecución de un handler
    """
    
    def __init__(self, handler_name: str, missing_info: Dict[str, Any]):
        self.handler_name = handler_name
        self.missing_info = missing_info
        
        message = f"Handler '{handler_name}' requires user input for missing parameters: {missing_info.get('missing_params', [])}"
        super().__init__(message)
        
        # Log especial para esta situación
        logger.info(f"Solicitando input del usuario para {handler_name}",
                   missing_count=missing_info.get('missing_count', 0),
                   missing_params=missing_info.get('missing_params', []))
        
        # Track como evento especial, no como error
        context = {
            "handler_name": handler_name,
            "missing_parameters": missing_info.get('missing_params', []),
            "discovered_count": missing_info.get('discovered_by_kyra', 0),
            "form_schema_available": missing_info.get('form_schema') is not None
        }
        
        # Usar el error tracker pero como evento informativo
        try:
            error_tracker.logger.info("User input required", **context)
        except Exception:
            pass  # No fallar si el tracking falla