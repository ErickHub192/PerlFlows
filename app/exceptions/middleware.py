"""
Middleware para manejo centralizado de errores y logging en Kyra
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from .logging_utils import get_kyra_logger, log_error_with_context, error_tracker, sanitize_sensitive_data


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware que captura todas las excepciones no manejadas y proporciona
    logging detallado y respuestas estructuradas
    """
    
    def __init__(self, app, include_error_details: bool = True):
        super().__init__(app)
        self.include_error_details = include_error_details
        self.logger = get_kyra_logger(__name__)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generar ID único para la petición
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        start_time = time.time()
        
        # Log de la petición entrante
        self.logger.log_api_request(
            method=request.method,
            path=str(request.url.path),
            user_id=getattr(request.state, 'user_id', None),
            request_id=request_id,
            query_params=dict(request.query_params)
        )
        
        try:
            response = await call_next(request)
            
            # Log de respuesta exitosa
            duration_ms = int((time.time() - start_time) * 1000)
            self.logger.log_api_response(
                method=request.method,
                path=str(request.url.path),
                status_code=response.status_code,
                duration_ms=duration_ms,
                user_id=getattr(request.state, 'user_id', None)
            )
            
            # Agregar headers de tracking
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = str(duration_ms)
            
            return response
            
        except HTTPException as e:
            # HTTPExceptions son errores controlados, solo log como warning
            duration_ms = int((time.time() - start_time) * 1000)
            self.logger.warning(
                f"HTTP Exception: {e.status_code}",
                request_id=request_id,
                detail=str(e.detail),
                duration_ms=duration_ms
            )
            
            # Mantener el formato original de HTTPException pero agregar request_id
            if isinstance(e.detail, dict):
                e.detail["request_id"] = request_id
            else:
                detail = {
                    "detail": e.detail,
                    "request_id": request_id
                }
                e.detail = detail
            
            raise e
            
        except Exception as e:
            # Errores no controlados - logging detallado
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Contexto de la petición
            context = {
                "method": request.method,
                "path": str(request.url.path),
                "user_id": getattr(request.state, 'user_id', None),
                "request_id": request_id,
                "duration_ms": duration_ms,
                "query_params": dict(request.query_params),
                "headers": dict(request.headers)
            }
            
            # Log del error con contexto completo
            log_error_with_context(self.logger.logger, e, context)
            
            # Track error para analytics
            error_tracker.track_error(
                error=e,
                component="API_MIDDLEWARE",
                operation=f"{request.method} {request.url.path}",
                context=context
            )
            
            # Crear respuesta de error estructurada
            error_response = self._create_error_response(e, request_id, context)
            
            return JSONResponse(
                status_code=500,
                content=error_response,
                headers={
                    "X-Request-ID": request_id,
                    "X-Response-Time": str(duration_ms)
                }
            )
    
    def _create_error_response(self, error: Exception, request_id: str, context: dict) -> dict:
        """
        Crea una respuesta de error estructurada
        """
        base_response = {
            "error": "Internal Server Error",
            "request_id": request_id,
            "timestamp": time.time()
        }
        
        if self.include_error_details:
            # En desarrollo, incluir detalles del error
            base_response.update({
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": sanitize_sensitive_data(context)
            })
        else:
            # En producción, solo mensaje genérico
            base_response["message"] = "An unexpected error occurred. Please contact support with the request ID."
        
        return base_response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware para logging detallado de peticiones (separado del manejo de errores)
    """
    
    def __init__(self, app, log_request_body: bool = False, log_response_body: bool = False):
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.logger = get_kyra_logger(__name__)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Log request details
        if self.log_request_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    # Solo log los primeros 500 caracteres del body
                    body_preview = body.decode()[:500]
                    self.logger.debug(
                        "Request body preview",
                        path=str(request.url.path),
                        body_preview=body_preview
                    )
            except Exception:
                pass  # Ignore body reading errors
        
        response = await call_next(request)
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Track performance issues
        if duration_ms > 5000:  # Requests taking more than 5 seconds
            error_tracker.track_performance_issue(
                operation=f"{request.method} {request.url.path}",
                duration_ms=duration_ms,
                context={
                    "user_id": getattr(request.state, 'user_id', None),
                    "query_params": dict(request.query_params)
                }
            )
        
        return response