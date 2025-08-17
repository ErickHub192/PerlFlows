# app/routers/chat_session_router.py

from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user_id
from app.services.chat_session_service import get_chat_session_service, ChatSessionService
from app.services.chat_title_service import get_chat_title_service, ChatTitleService
from app.services.chat_service_clean import get_chat_service, ChatService
from app.services.agent_run_service import get_agent_run_service, AgentRunService
from app.dtos.chat_session_dto import ChatSessionDTO, ChatMessageDTO
from app.dtos.chat_session_createDto import ChatSessionCreateDTO,ChatMessageCreateDTO
from app.dtos.chat_title_dto import TitleGenerationRequestDTO, TitleReadinessCheckDTO
router = APIRouter(prefix="/api/chats", tags=["chats"])




@router.get(
    "/",
    response_model=List[ChatSessionDTO],
    summary="Listar todas las sesiones de chat del usuario"
)
async def list_sessions(
    user_id: int = Depends(get_current_user_id),
    svc: ChatSessionService = Depends(get_chat_session_service),
):
    sessions = await svc.list_sessions(user_id)
    return [ChatSessionDTO.model_validate(s) for s in sessions]


@router.post(
    "/",
    response_model=ChatSessionDTO,
    summary="Crear una nueva sesión de chat"
)
async def create_session(
    dto: ChatSessionCreateDTO,
    user_id: int = Depends(get_current_user_id),
    svc: ChatSessionService = Depends(get_chat_session_service),
):
    session = await svc.create_session(user_id, dto.title)
    return ChatSessionDTO.model_validate(session)


@router.get(
    "/{session_id}",
    response_model=ChatSessionDTO,
    summary="Obtener metadata de una sesión de chat"
)
async def get_session(
    session_id: UUID,
    svc: ChatSessionService = Depends(get_chat_session_service),
):
    session = await svc.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return ChatSessionDTO.model_validate(session)


@router.get(
    "/{session_id}/messages",
    response_model=List[ChatMessageDTO],
    summary="Listar mensajes de una sesión de chat"
)
async def list_messages(
    session_id: UUID,
    user_id: int = Depends(get_current_user_id),
    svc: ChatSessionService = Depends(get_chat_session_service),
):
    # Asegura que sólo el dueño pueda ver su historial
    session = await svc.get_session(session_id)
    if not session or session.get('user_id') != user_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    messages = await svc.list_messages(session_id)
    return [ChatMessageDTO.model_validate(m) for m in messages]


@router.post(
    "/{session_id}/messages",
    response_model=ChatMessageDTO,
    summary="Agregar un mensaje a una sesión de chat"
)
async def add_message(
    session_id: UUID,
    dto: ChatMessageCreateDTO,
    svc: ChatSessionService = Depends(get_chat_session_service),
):
    msg = await svc.add_message(session_id, dto.role, dto.content)
    return ChatMessageDTO.model_validate(msg)


@router.patch(
    "/{session_id}/generate-title",
    summary="Generar título automático para la sesión usando Kyra LLM"
)
async def generate_chat_title(
    session_id: UUID,
    force_regenerate: bool = False,
    user_id: int = Depends(get_current_user_id),
    title_svc: ChatTitleService = Depends(get_chat_title_service),
):
    """
    Genera automáticamente un título para la sesión de chat basado en los mensajes iniciales.
    Toda la lógica de negocio está en el servicio usando DTOs.
    """
    request = TitleGenerationRequestDTO(
        session_id=session_id,
        user_id=user_id,
        force_regenerate=force_regenerate
    )
    
    result = await title_svc.generate_title_for_user_session(request)
    
    if not result.success:
        error_map = {
            "session_not_found": 404,
            "unauthorized": 403,
            "not_ready": 400,
            "generation_failed": 500,
            "internal_error": 500
        }
        status_code = error_map.get(result.error, 500)
        raise HTTPException(status_code=status_code, detail=result.message)
    
    return result


@router.get(
    "/{session_id}/title-ready",
    summary="Verificar si la sesión está lista para generar título"
)
async def check_title_generation_readiness(
    session_id: UUID,
    user_id: int = Depends(get_current_user_id),
    title_svc: ChatTitleService = Depends(get_chat_title_service),
):
    """
    Verifica si una sesión de chat está lista para generar un título automático.
    Toda la lógica de negocio está en el servicio usando DTOs.
    """
    request = TitleReadinessCheckDTO(
        session_id=session_id,
        user_id=user_id
    )
    
    result = await title_svc.check_title_readiness(request)
    
    if not result.success:
        error_map = {
            "session_not_found": 404,
            "unauthorized": 403,
            "internal_error": 500
        }
        status_code = error_map.get(result.error, 500)
        raise HTTPException(status_code=status_code, detail=result.message)
    
    return result


@router.get(
    "/{session_id}/stats",
    summary="Obtener estadísticas de ejecución para la sesión de chat"
)
async def get_session_stats(
    session_id: UUID,
    user_id: int = Depends(get_current_user_id),
    agent_run_svc: AgentRunService = Depends(get_agent_run_service),
):
    """
    Obtiene estadísticas de ejecución para una sesión de chat.
    
    - Si la sesión tiene agentes (modo AI): muestra stats de ejecuciones
    - Si no tiene agentes (modo classic): muestra info básica de workflow
    
    Usado por el sidebar para mostrar stats dinámicos en lugar de valores hardcodeados.
    """
    try:
        stats = await agent_run_svc.get_session_execution_stats(str(session_id), user_id)
        
        if stats is None:
            raise HTTPException(
                status_code=404, 
                detail="Sesión no encontrada o sin acceso"
            )
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo estadísticas: {str(e)}"
        )


@router.delete("/{session_id}")
async def delete_chat_session(
    session_id: str,
    user_id: int = Depends(get_current_user_id),
    chat_svc: ChatService = Depends(get_chat_service)
):
    """
    Eliminar una sesión de chat completa junto con sus mensajes
    """
    try:
        # Convertir session_id a UUID
        session_uuid = UUID(session_id)
        
        # Verificar que la sesión existe y pertenece al usuario
        try:
            session = await chat_svc.get_session(session_uuid)
        except ValueError:
            # Session not found - ChatSessionService raises ValueError
            raise HTTPException(
                status_code=404,
                detail="Sesión no encontrada"
            )
        
        if session.get('user_id') != user_id:
            raise HTTPException(
                status_code=403,
                detail="Sin acceso a esta sesión"
            )
        
        # Eliminar la sesión (cascada eliminará mensajes automáticamente)
        deleted = await chat_svc.delete_session(session_uuid)
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail="Sesión no encontrada"
            )
        
        return {"message": "Sesión eliminada exitosamente"}
        
    except ValueError as e:
        # Invalid UUID format
        if "invalid UUID" in str(e).lower():
            raise HTTPException(status_code=400, detail="ID de sesión inválido")
        # Re-raise other ValueErrors
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error eliminando sesión: {str(e)}"
        )


@router.patch("/{session_id}")
async def update_chat_session(
    session_id: str,
    update_data: dict,
    user_id: int = Depends(get_current_user_id),
    chat_svc: ChatService = Depends(get_chat_service)
):
    """
    Actualizar información de una sesión de chat (ej. título)
    """
    try:
        # Convertir session_id a UUID
        session_uuid = UUID(session_id)
        
        # Verificar que la sesión existe y pertenece al usuario
        try:
            session = await chat_svc.get_session(session_uuid)
        except ValueError:
            # Session not found - ChatSessionService raises ValueError
            raise HTTPException(
                status_code=404,
                detail="Sesión no encontrada"
            )
        
        if session.get('user_id') != user_id:
            raise HTTPException(
                status_code=403,
                detail="Sin acceso a esta sesión"
            )
        
        # Actualizar la sesión
        try:
            updated_session = await chat_svc.update_session(session_uuid, update_data)
            return updated_session
        except ValueError:
            # Update failed - session not found
            raise HTTPException(
                status_code=404,
                detail="Sesión no encontrada"
            )
        
    except ValueError as e:
        # Invalid UUID format
        if "invalid UUID" in str(e).lower():
            raise HTTPException(status_code=400, detail="ID de sesión inválido")
        # Re-raise other ValueErrors
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error actualizando sesión: {str(e)}"
        )
