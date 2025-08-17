"""
Discovery Factory - Registry para handlers de descubrimiento
Patrón factory para registrar y obtener discovery handlers dinámicamente
"""
import logging
from typing import Dict, Type, Optional, Any

logger = logging.getLogger(__name__)

# Registry global de discovery handlers
_discovery_handlers: Dict[str, Type] = {}


def register_discovery_handler(*providers):
    """
    Decorador para registrar discovery handlers con múltiples aliases
    
    Args:
        *providers: Uno o más nombres de provider/aliases
    """
    def decorator(handler_class):
        for provider in providers:
            _discovery_handlers[provider.lower()] = handler_class
            logger.debug(f"Discovery handler registered: {provider} -> {handler_class.__name__}")
        return handler_class
    
    return decorator


def get_discovery_handler(provider: str, credentials: Dict[str, Any]):
    """
    Factory method para obtener discovery handler
    
    Args:
        provider: Nombre del provider
        credentials: Credenciales para el provider
        
    Returns:
        Instancia del discovery handler o None si no existe
    """
    handler_class = _discovery_handlers.get(provider.lower())
    if handler_class:
        try:
            # Clean SQLAlchemy metadata from credentials
            clean_credentials = {k: v for k, v in credentials.items() if not k.startswith('_sa_')}
            return handler_class(clean_credentials)
        except Exception as e:
            logger.error(f"Error creating discovery handler for {provider}: {e}")
            return None
    
    logger.warning(f"No discovery handler found for provider: {provider}")
    return None


def list_available_handlers() -> Dict[str, str]:
    """
    Lista handlers de descubrimiento disponibles
    
    Returns:
        Dict con provider -> class name
    """
    return {provider: handler.__name__ for provider, handler in _discovery_handlers.items()}


class BaseDiscoveryHandler:
    """
    Clase base para discovery handlers
    Define la interfaz común que deben implementar
    """
    
    def __init__(self, credentials: Dict[str, Any]):
        """
        Inicializa handler con credenciales
        
        Args:
            credentials: Credenciales del provider
        """
        self.credentials = credentials
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def discover_files(
        self, 
        file_types: Optional[list] = None,
        limit: int = 50
    ) -> list:
        """
        Descubre archivos del provider
        
        Args:
            file_types: Tipos de archivo a filtrar (opcional)
            limit: Límite de archivos a retornar
            
        Returns:
            Lista de archivos descubiertos
        """
        raise NotImplementedError("Subclasses must implement discover_files()")
    
    async def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """
        Obtiene metadata de un archivo específico
        
        Args:
            file_id: ID del archivo
            
        Returns:
            Metadata del archivo
        """
        raise NotImplementedError("Subclasses must implement get_file_metadata()")
    
    def _format_file_info(
        self, 
        file_id: str, 
        name: str, 
        file_type: str = "unknown",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Formatea información de archivo a estructura estándar
        
        Args:
            file_id: ID del archivo
            name: Nombre del archivo
            file_type: Tipo de archivo
            **kwargs: Metadata adicional
            
        Returns:
            Dict con información formateada
        """
        return {
            "id": file_id,
            "name": name,
            "type": file_type,
            "provider": self.__class__.__name__.replace("DiscoveryHandler", "").lower(),
            "confidence": kwargs.get("confidence", 0.8),
            "structure": kwargs.get("structure", {}),
            "icon": kwargs.get("icon", "📄"),
            "metadata": kwargs.get("metadata", {}),
            "size": kwargs.get("size"),
            "modified": kwargs.get("modified"),
            "created": kwargs.get("created"),
            "mime_type": kwargs.get("mime_type"),
            "url": kwargs.get("url")
        }