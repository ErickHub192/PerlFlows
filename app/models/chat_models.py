# app/models/chat_models.py

from typing import Any, Dict, List, Optional, Union
from app.models.clarify_models import ClarifyPayload
from app.models.form_payload import FormPayload
from pydantic import BaseModel
from uuid import UUID

class ConversationMessage(BaseModel):
    """Modelo para representar un mensaje en la conversación"""
    role: str  # "user" o "assistant"
    content: str

class ChatRequestModel(BaseModel):
    session_id: Optional[UUID] = None  # Ahora opcional - se crea si no existe
    message: Union[str, ClarifyPayload, FormPayload]
    conversation: List[Dict[str, Any]] = []
    workflow_type: str  # ← CAMPO REQUERIDO del switch frontend
    # 🚨 NEW: OAuth system message injection support
    oauth_completed: Optional[List[str]] = None  # List of completed OAuth services
    system_message: Optional[str] = None  # System message to inject
    continue_workflow: bool = False  # Flag to indicate workflow continuation

class WorkflowModificationRequestModel(BaseModel):
    session_id: UUID
    message: str
    current_workflow: Dict[str, Any]
    conversation: List[Dict[str, Any]] = []
    
    

class ChatResponseModel(BaseModel):
    """
    Modelo interno usado por ChatService. Se mapea a ChatDTO.
    EXTENDIDO: Nuevos campos para Universal Discovery y Service Suggestions
    """
    reply: Optional[str] = None
    conversation: List[Dict[str, Any]] = []
    newMessages: List[Dict[str, Any]] = []
    finalize: bool = False
    editable: bool = False
    clarify: Optional[List[Dict[str, Any]]] = None
    orchestration: Optional[Any] = None
    # NUEVOS CAMPOS para Universal Discovery
    oauth_flows: Optional[List[Dict[str, Any]]] = None
    enhanced_workflow: bool = False
    discovered_files: int = 0
    # NUEVO CAMPO para Service Suggestions (LLM + CAG)
    service_suggestions: Optional[List[Dict[str, Any]]] = None
    # NUEVO CAMPO para OAuth Requirements  
    oauth_requirements: Optional[List[Dict[str, Any]]] = None
    # NUEVO CAMPO para retornar session_id creado automáticamente
    session_id: Optional[UUID] = None
    # ✨ NUEVO CAMPO para workflow steps (necesario para dropdown)
    steps: Optional[List[Dict[str, Any]]] = None
    # ✨ NUEVOS CAMPOS para service selection dropdown
    similar_services_found: bool = False
    service_groups: Optional[List[Dict[str, Any]]] = None
    # ✨ NUEVO CAMPO para smart forms
    smart_form: Optional[Dict[str, Any]] = None
    smart_forms_required: bool = False
    # 🔧 NUEVOS CAMPOS para button state management
    status: Optional[str] = None
    workflow_status: Optional[str] = None
    workflow_action: Optional[str] = None  # 'save', 'activate', 'execute'
    metadata: Optional[Dict[str, Any]] = None
    # 🚀 NUEVO CAMPO para execution_plan (source of truth for workflow extraction)
    execution_plan: Optional[List[Dict[str, Any]]] = None

    class Config:
        # Allow arbitrary types for orchestration field
        arbitrary_types_allowed = True
