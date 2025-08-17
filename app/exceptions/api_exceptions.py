# app/exceptions/api_exceptions.py
import logging
from typing import Any, Dict, Optional
from fastapi import HTTPException, status
from .logging_utils import get_kyra_logger, error_tracker

class ResourceNotFoundException(HTTPException):
    def __init__(self, detail: str = "El recurso solicitado no fue encontrado"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class InvalidDataException(HTTPException):
    def __init__(self, detail: str = "Los datos proporcionados no son válidos"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

class WorkflowProcessingException(HTTPException):
    def __init__(self, detail: str = "Error al procesar el workflow"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)
        

class RepositoryException(Exception):
    """
    Excepción para errores en la capa de repositorio.
    """
    def __init__(self, message: str):
        super().__init__(message)

class HandlerError(Exception):
    """Error controlado dentro del handler para formateo uniforme."""
    
    def __init__(self, message: str, component: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.component = component
        self.context = context
        
        # Auto-log del error
        if component:
            error_tracker.track_error(
                error=self,
                component=component,
                operation="handler_execution",
                context=context
            )

class NodeMappingException(Exception):
    """
    Excepción para cuando no se puede determinar el node_id apropiado
    para un archivo descubierto en Universal Discovery.
    """
    def __init__(self, provider: str, file_type: str = None):
        self.provider = provider
        self.file_type = file_type
        message = f"No se pudo determinar node_id para provider: {provider}"
        if file_type:
            message += f", file_type: {file_type}"
        super().__init__(message)


# Nuevas excepciones específicas para mejor rastreo

class AuthenticationError(HTTPException):
    """Error de autenticación con logging detallado"""
    
    def __init__(self, detail: str = "Authentication failed", context: Optional[Dict[str, Any]] = None):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
        
        error_tracker.track_error(
            error=self,
            component="AUTHENTICATION",
            operation="auth_validation",
            context=context
        )


class PlannerError(Exception):
    """Error en el proceso de planificación"""
    
    def __init__(self, message: str, goal: Optional[str] = None, available_tools: Optional[list] = None):
        super().__init__(message)
        self.goal = goal
        self.available_tools = available_tools
        
        context = {}
        if goal:
            context["goal"] = goal[:200]  # Truncar goal largo
        if available_tools:
            context["available_tools_count"] = len(available_tools)
            context["available_tools"] = available_tools[:10]  # Solo primeras 10
        
        error_tracker.track_error(
            error=self,
            component="PLANNER",
            operation="plan_generation",
            context=context
        )


class ToolExecutionError(HandlerError):
    """Error específico en la ejecución de herramientas"""
    
    def __init__(self, tool_name: str, message: str, tool_params: Optional[Dict[str, Any]] = None):
        self.tool_name = tool_name
        self.tool_params = tool_params
        
        context = {
            "tool_name": tool_name,
            "tool_params": tool_params
        }
        
        super().__init__(
            message=f"Tool execution failed for {tool_name}: {message}",
            component="TOOL_EXECUTOR",
            context=context
        )


class OrchestratorError(Exception):
    """Error en el orchestrator/workflow engine"""
    
    def __init__(self, message: str, user_id: Optional[int] = None, workflow_context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.user_id = user_id
        self.workflow_context = workflow_context
        
        context = {"user_id": user_id}
        if workflow_context:
            context.update(workflow_context)
        
        error_tracker.track_error(
            error=self,
            component="ORCHESTRATOR",
            operation="workflow_processing",
            context=context
        )


class DatabaseConnectionError(RepositoryException):
    """Error de conexión a base de datos con logging"""
    
    def __init__(self, operation: str, table: Optional[str] = None, original_error: Optional[Exception] = None):
        self.operation = operation
        self.table = table
        self.original_error = original_error
        
        message = f"Database connection error during {operation}"
        if table:
            message += f" on table {table}"
        if original_error:
            message += f": {str(original_error)}"
        
        super().__init__(message)
        
        context = {
            "operation": operation,
            "table": table,
            "original_error_type": type(original_error).__name__ if original_error else None
        }
        
        error_tracker.track_error(
            error=self,
            component="DATABASE",
            operation=operation,
            context=context
        )


class ExternalAPIError(Exception):
    """Error en llamadas a APIs externas"""
    
    def __init__(self, service: str, endpoint: str, status_code: Optional[int] = None, response_body: Optional[str] = None):
        self.service = service
        self.endpoint = endpoint
        self.status_code = status_code
        self.response_body = response_body
        
        message = f"External API error: {service} {endpoint}"
        if status_code:
            message += f" (status: {status_code})"
        
        super().__init__(message)
        
        context = {
            "service": service,
            "endpoint": endpoint,
            "status_code": status_code,
            "response_preview": response_body[:200] if response_body else None
        }
        
        error_tracker.track_error(
            error=self,
            component="EXTERNAL_API",
            operation=f"{service}_api_call",
            context=context
        )

