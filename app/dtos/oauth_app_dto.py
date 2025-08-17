"""
OAuth App DTOs - Modelos para gestión de aplicaciones OAuth del usuario
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class OAuthAppCreateRequest(BaseModel):
    """DTO para crear nueva OAuth App"""
    provider: str
    client_id: str
    client_secret: str
    app_name: str


class OAuthAppUpdateRequest(BaseModel):
    """DTO para actualizar OAuth App"""
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    app_name: Optional[str] = None


class OAuthAppResponse(BaseModel):
    """DTO para respuesta de OAuth App"""
    provider: str
    client_id: str
    app_name: str
    created_at: str
    is_active: bool = True
    
    class Config:
        from_attributes = True


class OAuthAppsListResponse(BaseModel):
    """DTO para lista de OAuth Apps del usuario"""
    oauth_apps: list[OAuthAppResponse]
    total: int