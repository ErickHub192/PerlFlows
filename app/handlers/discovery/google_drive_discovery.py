"""
Google Drive Discovery Handler
Descubre archivos reales en Google Drive del usuario
"""
import logging
from typing import Dict, Any, List, Optional
from googleapiclient.errors import HttpError

from .discovery_factory import register_discovery_handler, BaseDiscoveryHandler
from .base_google_discovery import BaseGoogleDiscoveryHandler

logger = logging.getLogger(__name__)


@register_discovery_handler("google_drive", "googledrive", "drive")
class GoogleDriveDiscoveryHandler(BaseGoogleDiscoveryHandler):
    """
    Discovery handler específico para Google Drive
    Enfocado solo en archivos de Drive, no Sheets
    """
    
    def __init__(self, credentials: Dict[str, Any]):
        super().__init__(credentials, service_name='drive')
    
    async def discover_files(
        self, 
        file_types: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Descubre archivos en Google Drive
        
        Args:
            file_types: Tipos de archivo a filtrar (ej: ['document', 'presentation'])
            limit: Límite de archivos
            
        Returns:
            Lista de archivos encontrados
        """
        try:
            # ✅ Usar servicio auto-discovered
            drive_service = await self.get_main_service()
            
            # Construir query dinámicamente
            query_parts = ["trashed=false"]
            
            if file_types:
                # Mapear tipos a mimeTypes de Google
                mime_type_map = {
                    'spreadsheet': 'application/vnd.google-apps.spreadsheet',
                    'document': 'application/vnd.google-apps.document',
                    'presentation': 'application/vnd.google-apps.presentation',
                    'folder': 'application/vnd.google-apps.folder',
                    'pdf': 'application/pdf',
                    'image': 'image/',
                    'video': 'video/',
                    'audio': 'audio/'
                }
                
                mime_queries = []
                for file_type in file_types:
                    if file_type in mime_type_map:
                        mime_type = mime_type_map[file_type]
                        if mime_type.endswith('/'):
                            mime_queries.append(f"mimeType contains '{mime_type}'")
                        else:
                            mime_queries.append(f"mimeType='{mime_type}'")
                
                if mime_queries:
                    query_parts.append(f"({' or '.join(mime_queries)})")
            
            query = " and ".join(query_parts)
            
            # Buscar archivos
            results = drive_service.files().list(
                q=query,
                pageSize=min(limit, 100),
                fields="files(id,name,mimeType,size,modifiedTime,createdTime,webViewLink,thumbnailLink,parents)"
            ).execute()
            
            files = results.get('files', [])
            
            # Formatear archivos
            discovered_files = []
            for file in files:
                file_info = self._format_drive_file(file)
                discovered_files.append(file_info)
            
            self.logger.info(f"Discovered {len(discovered_files)} files in Google Drive")
            return discovered_files
            
        except HttpError as e:
            self.logger.error(f"Google Drive API error: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error discovering Google Drive files: {e}")
            return []
    
    async def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """
        Obtiene metadata detallada de un archivo
        """
        try:
            # ✅ Usar servicio auto-discovered
            drive_service = await self.get_main_service()
            
            file = drive_service.files().get(
                fileId=file_id,
                fields="id,name,mimeType,size,modifiedTime,createdTime,webViewLink,thumbnailLink,parents,description,properties"
            ).execute()
            
            return self._format_drive_file(file, detailed=True)
            
        except HttpError as e:
            self.logger.error(f"Error getting file metadata: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Error getting file metadata: {e}")
            return {}
    
    def _format_drive_file(self, file: Dict[str, Any], detailed: bool = False) -> Dict[str, Any]:
        """
        Formatea archivo de Google Drive a estructura estándar
        """
        # Determinar tipo de archivo por mimeType
        mime_type = file.get('mimeType', '')
        file_type = self._get_file_type_from_mime(mime_type)
        
        # Determinar icono
        icon = self._get_icon_for_type(file_type, mime_type)
        
        # Estructura básica
        structure = {}
        if file_type == 'spreadsheet':
            structure = {"type": "spreadsheet", "has_sheets": True}
        elif file_type == 'document':
            structure = {"type": "document", "has_text": True}
        elif file_type == 'presentation':
            structure = {"type": "presentation", "has_slides": True}
        elif file_type == 'folder':
            structure = {"type": "folder", "can_contain_files": True}
        
        # Metadata
        metadata = {
            "mime_type": mime_type,
            "web_view_link": file.get('webViewLink'),
            "thumbnail_link": file.get('thumbnailLink'),
            "parents": file.get('parents', [])
        }
        
        if detailed:
            metadata.update({
                "description": file.get('description'),
                "properties": file.get('properties', {})
            })
        
        return self._format_file_info(
            file_id=file['id'],
            name=file['name'],
            file_type=file_type,
            structure=structure,
            icon=icon,
            metadata=metadata,
            size=file.get('size'),
            modified=file.get('modifiedTime'),
            created=file.get('createdTime'),
            mime_type=mime_type,
            url=file.get('webViewLink')
        )
    
    def _get_file_type_from_mime(self, mime_type: str) -> str:
        """
        Convierte mimeType a tipo de archivo legible
        """
        mime_map = {
            'application/vnd.google-apps.spreadsheet': 'spreadsheet',
            'application/vnd.google-apps.document': 'document',
            'application/vnd.google-apps.presentation': 'presentation',
            'application/vnd.google-apps.folder': 'folder',
            'application/pdf': 'pdf',
            'text/plain': 'text',
            'application/json': 'json',
            'text/csv': 'csv'
        }
        
        if mime_type in mime_map:
            return mime_map[mime_type]
        
        # Tipos genéricos
        if mime_type.startswith('image/'):
            return 'image'
        elif mime_type.startswith('video/'):
            return 'video'
        elif mime_type.startswith('audio/'):
            return 'audio'
        elif mime_type.startswith('text/'):
            return 'text'
        
        return 'unknown'
    
    def _get_icon_for_type(self, file_type: str, mime_type: str) -> str:
        """
        Retorna emoji/icon apropiado para el tipo de archivo
        """
        icon_map = {
            'spreadsheet': '📊',
            'document': '📄',
            'presentation': '📽️',
            'folder': '📁',
            'pdf': '📕',
            'image': '🖼️',
            'video': '🎥',
            'audio': '🎵',
            'text': '📝',
            'csv': '📋',
            'json': '🔧'
        }
        
        return icon_map.get(file_type, '📄')