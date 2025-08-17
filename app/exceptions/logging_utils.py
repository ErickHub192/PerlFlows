"""
Utilidades centralizadas para logging y manejo de errores en Kyra
Integrado con el sistema de exceptions existente
"""

import logging
import traceback
from typing import Any, Dict, Optional
from datetime import datetime
import json
from fastapi import HTTPException


class KyraLogger:
    """
    Logger centralizado para Kyra que proporciona logging estructurado
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.component_name = name.split('.')[-1].upper()
    
    def _format_message(self, message: str, **kwargs) -> str:
        """Formatea el mensaje con información adicional"""
        prefix = f"{self.component_name}: {message}"
        if kwargs:
            additional_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
            return f"{prefix} | {additional_info}"
        return prefix
    
    def info(self, message: str, **kwargs):
        """Log nivel INFO con formato estructurado"""
        self.logger.info(self._format_message(message, **kwargs))
    
    def debug(self, message: str, **kwargs):
        """Log nivel DEBUG con formato estructurado"""
        self.logger.debug(self._format_message(message, **kwargs))
    
    def warning(self, message: str, **kwargs):
        """Log nivel WARNING con formato estructurado"""
        self.logger.warning(self._format_message(message, **kwargs))
    
    def error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log nivel ERROR con formato estructurado y stack trace opcional"""
        formatted_msg = self._format_message(message, **kwargs)
        if error:
            formatted_msg += f" | error_type={type(error).__name__} | error_msg={str(error)}"
        self.logger.error(formatted_msg)
        
        if error:
            self.logger.error(f"{self.component_name}: Stack trace: {traceback.format_exc()}")
    
    def exception(self, message: str, **kwargs):
        """Log nivel ERROR con stack trace automático"""
        self.logger.exception(self._format_message(message, **kwargs))
    
    def log_function_start(self, func_name: str, **params):
        """Log el inicio de una función con sus parámetros"""
        sanitized_params = {k: str(v)[:100] if isinstance(v, str) and len(str(v)) > 100 else v 
                          for k, v in params.items()}
        self.debug(f"Iniciando {func_name}", **sanitized_params)
    
    def log_function_end(self, func_name: str, duration_ms: Optional[int] = None, **result_info):
        """Log el final de una función con información de resultado"""
        if duration_ms:
            self.info(f"Completado {func_name}", duration_ms=duration_ms, **result_info)
        else:
            self.info(f"Completado {func_name}", **result_info)
    
    def log_api_request(self, method: str, path: str, user_id: Optional[int] = None, **extra):
        """Log una petición API"""
        self.info(f"API Request: {method} {path}", user_id=user_id, **extra)
    
    def log_api_response(self, method: str, path: str, status_code: int, duration_ms: int, user_id: Optional[int] = None):
        """Log una respuesta API"""
        self.info(f"API Response: {method} {path}", status_code=status_code, duration_ms=duration_ms, user_id=user_id)


def get_kyra_logger(name: str) -> KyraLogger:
    """Factory para obtener un KyraLogger"""
    return KyraLogger(name)


def log_error_with_context(logger: logging.Logger, error: Exception, context: Dict[str, Any]):
    """
    Utility para loggear errores con contexto detallado
    """
    # Sanitizar datos sensibles del contexto
    sanitized_context = sanitize_sensitive_data(context)
    
    error_info = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": sanitized_context,
        "timestamp": datetime.utcnow().isoformat(),
        "stack_trace": traceback.format_exc()
    }
    
    logger.error(f"Error detallado: {json.dumps(error_info, indent=2, default=str)}")


def create_detailed_500_error(error: Exception, context: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None) -> HTTPException:
    """
    Crea un HTTPException 500 detallado para debugging
    """
    sanitized_context = sanitize_sensitive_data(context) if context else {}
    
    error_detail = {
        "error": "Internal Server Error",
        "error_type": type(error).__name__,
        "error_message": str(error),
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": request_id,
        "context": sanitized_context
    }
    
    return HTTPException(
        status_code=500,
        detail=error_detail
    )


def sanitize_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remueve o enmascara datos sensibles antes de logging
    """
    sensitive_keys = {
        'password', 'token', 'secret', 'key', 'auth', 'credential', 
        'api_key', 'access_token', 'refresh_token', 'hashed_password'
    }
    
    sanitized = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(sensitive_key in key_lower for sensitive_key in sensitive_keys):
            sanitized[key] = "***REDACTED***"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_sensitive_data(value)
        elif isinstance(value, str) and len(value) > 200:
            # Truncar strings muy largos
            sanitized[key] = value[:200] + "...TRUNCATED"
        else:
            sanitized[key] = value
    
    return sanitized


class ErrorTracker:
    """
    Rastreador de errores para analytics y debugging
    """
    
    def __init__(self):
        self.logger = get_kyra_logger(__name__)
    
    def track_error(self, error: Exception, component: str, operation: str, context: Optional[Dict[str, Any]] = None):
        """
        Rastrea un error con información estructurada
        """
        error_data = {
            "component": component,
            "operation": operation,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.utcnow().isoformat(),
            "context": sanitize_sensitive_data(context) if context else {}
        }
        
        self.logger.error("Error tracked", **error_data)
        
        # Aquí podrías integrar con sistemas de monitoring externos
        # como Sentry, DataDog, etc.
    
    def track_performance_issue(self, operation: str, duration_ms: int, threshold_ms: int = 5000, context: Optional[Dict[str, Any]] = None):
        """
        Rastrea problemas de performance
        """
        if duration_ms > threshold_ms:
            perf_data = {
                "operation": operation,
                "duration_ms": duration_ms,
                "threshold_ms": threshold_ms,
                "timestamp": datetime.utcnow().isoformat(),
                "context": sanitize_sensitive_data(context) if context else {}
            }
            
            self.logger.warning("Performance issue detected", **perf_data)


# Instancia global del error tracker
error_tracker = ErrorTracker()