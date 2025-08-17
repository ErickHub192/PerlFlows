"""
Dropbox Discovery Handler
Descubre archivos en Dropbox del usuario
"""
import logging
from typing import Dict, Any, List, Optional

from .discovery_factory import register_discovery_handler, BaseDiscoveryHandler

logger = logging.getLogger(__name__)


@register_discovery_handler("dropbox")
class DropboxDiscoveryHandler(BaseDiscoveryHandler):
    """
    Discovery handler para Dropbox
    Descubre archivos y carpetas en Dropbox
    """
    
    def __init__(self, credentials: Dict[str, Any]):
        super().__init__(credentials)
        self.access_token = credentials.get('access_token')
        self.dbx = None
    
    async def discover_files(
        self, 
        file_types: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Descubre archivos en Dropbox
        """
        try:
            import dropbox
            
            if not self.dbx:
                self.dbx = dropbox.Dropbox(self.access_token)
            
            # Listar archivos en la raíz
            result = self.dbx.files_list_folder("", limit=limit)
            
            discovered_files = []
            
            for entry in result.entries:
                if isinstance(entry, dropbox.files.FileMetadata):
                    file_info = self._format_dropbox_file(entry)
                    
                    # Filtrar por tipo si se especifica
                    if file_types:
                        file_type = file_info.get('type', 'unknown')
                        if file_type not in file_types and not any(
                            file_type.startswith(ft) for ft in file_types
                        ):
                            continue
                    
                    discovered_files.append(file_info)
                
                elif isinstance(entry, dropbox.files.FolderMetadata):
                    # Incluir carpetas si se requieren
                    if not file_types or 'folder' in file_types:
                        folder_info = self._format_dropbox_folder(entry)
                        discovered_files.append(folder_info)
            
            self.logger.info(f"Discovered {len(discovered_files)} items in Dropbox")
            return discovered_files
            
        except ImportError:
            self.logger.error("Dropbox library not available. Install with: pip install dropbox")
            return []
        except Exception as e:
            self.logger.error(f"Error discovering Dropbox files: {e}")
            return []
    
    async def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """
        Obtiene metadata de un archivo específico de Dropbox
        En Dropbox, file_id es el path del archivo
        """
        try:
            import dropbox
            
            if not self.dbx:
                self.dbx = dropbox.Dropbox(self.access_token)
            
            # Obtener metadata del archivo
            metadata = self.dbx.files_get_metadata(file_id)
            
            if isinstance(metadata, dropbox.files.FileMetadata):
                return self._format_dropbox_file(metadata, detailed=True)
            elif isinstance(metadata, dropbox.files.FolderMetadata):
                return self._format_dropbox_folder(metadata, detailed=True)
            
            return {}
            
        except ImportError:
            self.logger.error("Dropbox library not available")
            return {}
        except Exception as e:
            self.logger.error(f"Error getting Dropbox file metadata: {e}")
            return {}
    
    async def get_shared_links(self, file_path: str) -> Dict[str, Any]:
        """
        Obtiene enlaces compartidos para un archivo
        """
        try:
            import dropbox
            
            if not self.dbx:
                self.dbx = dropbox.Dropbox(self.access_token)
            
            # Intentar obtener enlace compartido existente
            try:
                links = self.dbx.sharing_list_shared_links(path=file_path)
                if links.links:
                    return {
                        "has_shared_link": True,
                        "shared_link": links.links[0].url,
                        "link_type": "existing"
                    }
            except:
                pass
            
            # Crear enlace compartido si no existe
            try:
                link = self.dbx.sharing_create_shared_link_with_settings(file_path)
                return {
                    "has_shared_link": True,
                    "shared_link": link.url,
                    "link_type": "created"
                }
            except:
                return {
                    "has_shared_link": False,
                    "error": "Could not create shared link"
                }
            
        except ImportError:
            return {"error": "Dropbox library not available"}
        except Exception as e:
            return {"error": str(e)}
    
    def _format_dropbox_file(self, file_entry, detailed: bool = False) -> Dict[str, Any]:
        """
        Formatea archivo de Dropbox a estructura estándar
        """
        # Determinar tipo de archivo por extensión
        name = file_entry.name
        file_type = self._get_file_type_from_name(name)
        icon = self._get_icon_for_type(file_type)
        
        # Estructura básica
        structure = {
            "type": "file",
            "can_download": True,
            "can_share": True
        }
        
        # Metadata
        metadata = {
            "path": file_entry.path_display,
            "path_lower": file_entry.path_lower,
            "content_hash": getattr(file_entry, 'content_hash', None),
            "is_downloadable": True
        }
        
        if detailed:
            metadata.update({
                "server_modified": getattr(file_entry, 'server_modified', None),
                "client_modified": getattr(file_entry, 'client_modified', None),
                "rev": getattr(file_entry, 'rev', None)
            })
        
        return self._format_file_info(
            file_id=file_entry.path_display,  # En Dropbox usamos el path como ID
            name=name,
            file_type=file_type,
            structure=structure,
            icon=icon,
            metadata=metadata,
            size=getattr(file_entry, 'size', None),
            modified=getattr(file_entry, 'server_modified', None),
            created=getattr(file_entry, 'client_modified', None)
        )
    
    def _format_dropbox_folder(self, folder_entry, detailed: bool = False) -> Dict[str, Any]:
        """
        Formatea carpeta de Dropbox
        """
        structure = {
            "type": "folder",
            "can_contain_files": True,
            "can_list": True
        }
        
        metadata = {
            "path": folder_entry.path_display,
            "path_lower": folder_entry.path_lower,
            "is_folder": True
        }
        
        return self._format_file_info(
            file_id=folder_entry.path_display,
            name=folder_entry.name,
            file_type='folder',
            structure=structure,
            icon='📁',
            metadata=metadata
        )
    
    def _get_file_type_from_name(self, name: str) -> str:
        """
        Determina tipo de archivo por extensión
        """
        name_lower = name.lower()
        
        if name_lower.endswith(('.pdf',)):
            return 'pdf'
        elif name_lower.endswith(('.doc', '.docx')):
            return 'document'
        elif name_lower.endswith(('.xls', '.xlsx', '.csv')):
            return 'spreadsheet'
        elif name_lower.endswith(('.ppt', '.pptx')):
            return 'presentation'
        elif name_lower.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
            return 'image'
        elif name_lower.endswith(('.mp4', '.avi', '.mov', '.wmv')):
            return 'video'
        elif name_lower.endswith(('.mp3', '.wav', '.flac', '.aac')):
            return 'audio'
        elif name_lower.endswith(('.txt', '.md', '.rtf')):
            return 'text'
        elif name_lower.endswith(('.json',)):
            return 'json'
        elif name_lower.endswith(('.zip', '.rar', '.7z')):
            return 'archive'
        
        return 'unknown'
    
    def _get_icon_for_type(self, file_type: str) -> str:
        """
        Retorna emoji apropiado para el tipo de archivo
        """
        icon_map = {
            'pdf': '📕',
            'document': '📄',
            'spreadsheet': '📊',
            'presentation': '📽️',
            'image': '🖼️',
            'video': '🎥',
            'audio': '🎵',
            'text': '📝',
            'json': '🔧',
            'archive': '📦',
            'folder': '📁'
        }
        
        return icon_map.get(file_type, '📄')