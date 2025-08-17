"""
Discovery Handlers - Para descubrir/listar archivos y contenido
Separado de los handlers de acción, enfocado en lectura/descubrimiento
"""

# Importar todos los handlers para que se registren automáticamente
from .google_drive_discovery import GoogleDriveDiscoveryHandler
from .google_sheets_discovery import GoogleSheetsDiscoveryHandler  
from .gmail_discovery import GmailDiscoveryHandler
from .google_calendar_discovery import GoogleCalendarDiscoveryHandler
from .dropbox_discovery import DropboxDiscoveryHandler

# Factory es importado automáticamente por los handlers
from .discovery_factory import get_discovery_handler, list_available_handlers

__all__ = [
    'GoogleDriveDiscoveryHandler',
    'GoogleSheetsDiscoveryHandler', 
    'GmailDiscoveryHandler',
    'GoogleCalendarDiscoveryHandler',
    'DropboxDiscoveryHandler',
    'get_discovery_handler',
    'list_available_handlers'
]