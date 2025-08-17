from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any, Optional,Union
from uuid import UUID
from app.dtos.question_dto import QuestionDTO
from app.dtos.clarify_oauth_dto import ClarifyOAuthItemDTO

class ChatDTO(BaseModel):
    reply: Optional[str] = None
    newMessages: Optional[List[Dict[str, Any]]] = None
    clarify: Optional[List[Union[QuestionDTO, ClarifyOAuthItemDTO]]] = None
    finalize: bool
    editable: bool
    # NUEVOS CAMPOS para Universal Discovery
    oauth_flows: Optional[List[Dict[str, Any]]] = None
    enhanced_workflow: Optional[bool] = False
    discovered_files: Optional[int] = 0
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
    # ✨ NUEVOS CAMPOS para smart forms
    smart_form: Optional[Dict[str, Any]] = None
    smart_forms_required: bool = False
    # 🔧 NUEVOS CAMPOS para button state management
    status: Optional[str] = None
    workflow_status: Optional[str] = None
    workflow_action: Optional[str] = None  # 'save', 'activate', 'execute'
    metadata: Optional[Dict[str, Any]] = None
    # 🚀 NUEVO CAMPO para execution_plan (source of truth for workflow extraction)
    execution_plan: Optional[List[Dict[str, Any]]] = None

    model_config = ConfigDict(from_attributes=True)
