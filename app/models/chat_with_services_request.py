from pydantic import BaseModel
from typing import List, Dict, Any
from uuid import UUID

class ChatWithServicesRequest(BaseModel):
    """
    Request model para el endpoint /api/chat/with-services
    Incluye los servicios seleccionados por el usuario del dropdown
    """
    session_id: UUID
    message: str
    conversation: List[Dict[str, Any]] = []
    workflow_type: str  # Viene del switch del frontend - NO DEFAULT para forzar que frontend lo envíe
    selected_services: List[str]  # Servicios seleccionados del dropdown