"""
Base Google Action Handler
Combina ActionHandler con Google Discovery Service para nodos ejecutores
"""
import logging
from typing import Dict, Any

from .connector_handler import ActionHandler
from .discovery.base_google_discovery import BaseGoogleDiscoveryHandler

logger = logging.getLogger(__name__)


class BaseGoogleActionHandler(ActionHandler):
    """
    Base class para Google action handlers (nodos ejecutores)
    Combina ActionHandler con auto-discovery de Google APIs
    """
    
    def __init__(self, creds: Dict[str, Any], service_name: str):
        # Inicializar ActionHandler
        ActionHandler.__init__(self, creds)
        
        # Inicializar Google Discovery capabilities
        self._discovery_handler = BaseGoogleDiscoveryHandler(creds, service_name)
        self.service_name = service_name
    
    async def get_main_service(self):
        """Obtiene el servicio principal con auto-discovery"""
        return await self._discovery_handler.get_main_service()
    
    async def get_drive_service(self):
        """Helper para Drive service"""
        return await self._discovery_handler.get_drive_service()
    
    async def get_sheets_service(self):
        """Helper para Sheets service"""
        return await self._discovery_handler.get_sheets_service()
    
    async def get_gmail_service(self):
        """Helper para Gmail service"""
        return await self._discovery_handler.get_gmail_service()
    
    async def get_calendar_service(self):
        """Helper para Calendar service"""
        return await self._discovery_handler.get_calendar_service()
    
    def get_service_info(self) -> Dict[str, Any]:
        """Retorna información del servicio discovered"""
        return self._discovery_handler.get_service_info()
    
    async def discover_available_methods(self):
        """Descubre métodos disponibles para debugging"""
        return await self._discovery_handler.discover_available_methods()