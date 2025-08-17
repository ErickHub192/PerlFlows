from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

# ✅ REFACTORIZADO: Entrada agnóstica con service_id + backward compatibility
class CredentialInputDTO(BaseModel):
    # Nuevo sistema agnóstico
    service_id: Optional[str] = None
    mechanism: Optional[str] = None
    config: Optional[dict] = None
    
    # Legacy compatibility (deprecated)
    provider: Optional[str] = None
    flavor: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    scopes: Optional[List[str]] = None
    chat_id: Optional[str] = None

# ✅ REFACTORIZADO: Respuesta agnóstica con service_id + backward compatibility
class CredentialDTO(BaseModel):
    id: int
    user_id: int
    chat_id: Optional[str] = None
    
    # Nuevo sistema agnóstico
    service_id: Optional[str] = None
    mechanism: Optional[str] = None
    config: Optional[dict] = None
    
    # Legacy compatibility (deprecated but maintained)
    provider: Optional[str] = None
    flavor: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    scopes: Optional[List[str]] = None
    
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
