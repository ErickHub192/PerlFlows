from app.exceptions.api_exceptions import WorkflowProcessingException

class JSONParsingException(WorkflowProcessingException):
    """Error al parsear la respuesta JSON del LLM."""

class LLMConnectionException(WorkflowProcessingException):
    """Error de conexión o timeout con el servicio LLM."""
