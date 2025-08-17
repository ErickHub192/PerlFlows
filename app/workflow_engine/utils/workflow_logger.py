"""
Workflow Logger - Logging consistente para el workflow engine
Centraliza y estandariza el logging a través de todos los módulos
"""
import logging
from typing import Any, Dict, Optional, List
from ..core.interfaces import WorkflowCreationResult


class WorkflowLogger:
    """
    Proporciona métodos de logging consistentes para el workflow engine
    """
    
    def __init__(self, logger_name: str = __name__):
        self.logger = logging.getLogger(logger_name)
    
    def log_request_start(self, user_id: int, user_message: str, selected_services: Optional[List[str]] = None):
        """Log del inicio de procesamiento de request"""
        if selected_services:
            self.logger.info(f"Processing user request with selected services: {selected_services} - user_id={user_id}")
        else:
            self.logger.info(f"Processing user request: user_id={user_id}, message='{user_message}'")
    
    # log_intent_analysis ELIMINADO - LLM maneja intent naturalmente
    
    def log_discovery_start(self, discovery_mode: str, provider_count: int):
        """Log del inicio de discovery"""
        self.logger.info(f"Starting {discovery_mode} discovery with {provider_count} providers")
    
    def log_discovery_result(self, capabilities_count: int, confidence: str):
        """Log del resultado de discovery"""
        self.logger.info(f"Discovery completed: {capabilities_count} capabilities found, "
                        f"confidence={confidence}")
    
    def log_oauth_required(self, oauth_requirements: List[Any]):
        """Log cuando se requiere OAuth"""
        # Handle both old and new DTO formats
        oauth_items = []
        for req in oauth_requirements:
            if hasattr(req, 'provider'):
                oauth_items.append(req.provider)
            elif hasattr(req, 'oauth_url'):
                # ClarifyOAuthItemDTO format - extract provider from URL
                url = req.oauth_url
                if '/auth/' in url:
                    provider = url.split('/auth/')[1].split('/')[0]
                    oauth_items.append(provider)
                else:
                    oauth_items.append('oauth')
            else:
                oauth_items.append(str(req))
        self.logger.info(f"OAuth required: {oauth_items}")
    
    def log_workflow_success(self, steps_count: int, workflow_type: str):
        """Log de workflow creado exitosamente"""
        self.logger.info(f"Workflow creation successful: {steps_count} steps, {workflow_type} type")
    
    def log_error(self, error: Exception, context: str = ""):
        """Log de errores con contexto"""
        context_msg = f" in {context}" if context else ""
        self.logger.error(f"Error{context_msg}: {error}", exc_info=True)
    
    def log_provider_registration(self, provider_name: str, provider_type: str):
        """Log de registro de discovery provider"""
        self.logger.info(f"Registered discovery provider: {provider_name} ({provider_type})")
    
    def log_strategy_registration(self, strategy_name: str, workflow_type: str):
        """Log de registro de planning strategy"""
        self.logger.info(f"Registered planning strategy: {strategy_name} ({workflow_type})")
    
    # log_analyzer_configuration ELIMINADO - LLM maneja intent naturalmente
    
    def log_warning(self, message: str):
        """Log de warnings"""
        self.logger.warning(message)
    
    def log_debug(self, message: str):
        """Log de debug messages"""
        self.logger.debug(message)