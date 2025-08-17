"""
🔥 UPDATED: File Discovery DTOs - Para descubrimiento de archivos/metadata de nodos
NO confundir con Auth Service Discovery DTOs
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class FileDiscoveryRequestDTO(BaseModel):
    """
    🔥 UPDATED: Request para file discovery de archivos/metadata
    Ahora soporta planned_steps de la nueva arquitectura
    """
    user_message: str = Field(..., description="Mensaje del usuario")
    file_types: Optional[List[str]] = Field(None, description="Tipos de archivo específicos")
    providers: Optional[List[str]] = Field(None, description="Providers específicos")
    planned_steps: Optional[List[Dict[str, Any]]] = Field(None, description="Pasos del workflow planificados por Kyra")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_message": "Busca mis archivos de ventas",
                "file_types": ["xlsx", "csv", "pdf"],
                "providers": ["google", "dropbox"],
                "planned_steps": [
                    {
                        "id": "step_1",
                        "action_id": "action_123",
                        "default_auth": "oauth2_google_sheets",
                        "name": "Read Google Sheets"
                    }
                ]
            }
        }


class DiscoveredFileDTO(BaseModel):
    """Archivo descubierto"""
    id: str
    name: str
    provider: str
    file_type: str
    confidence: float = 0.8
    structure: Dict[str, Any] = {}
    icon: str = "📄"
    metadata: Dict[str, Any] = {}


class FileDiscoveryResponseDTO(BaseModel):
    """Response de file discovery"""
    discovered_files: List[DiscoveredFileDTO]
    total_files: int
    providers_used: List[str]
    message: str