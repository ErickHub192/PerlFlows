# app/routers/chat_router.py

import logging
import hashlib
import time
import json
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from uuid import UUID
from app.models.chat_models import ChatRequestModel, WorkflowModificationRequestModel
from app.models.chat_with_services_request import ChatWithServicesRequest
from app.dtos.chat_dto import ChatDTO
from app.core.auth import get_current_user_id
from app.db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.IChat_service import IChatService
from app.services.chat_service_clean import ChatService, get_chat_service
from app.exceptions.api_exceptions import InvalidDataException
from app.mappers.chat_mapper import map_chat_response_to_dto
from app.ai.llm_clients.llm_service import get_llm_service, LLMService
# Orchestrator imports removed - using WorkflowEngine via ChatService
from app.services.chat_session_service import get_chat_session_service
from app.dependencies.llm_dependencies import get_intelligent_llm_service
from app.services.intelligent_llm_service import IntelligentLLMService
# Removed: workflow_context_service - refactored away

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger(__name__)

# 🚨 CRITICAL FIX: Request deduplication cache
_REQUEST_CACHE = {}
_CACHE_TTL = 5  # ✅ REDUCED: 5 seconds TTL - only block rapid duplicates

def _clean_expired_requests():
    """Clean expired requests from cache"""
    current_time = time.time()
    expired_keys = [k for k, v in _REQUEST_CACHE.items() if current_time - v['timestamp'] > _CACHE_TTL]
    for key in expired_keys:
        del _REQUEST_CACHE[key]
        
def _get_request_hash(session_id: str, message: str, user_id: int) -> str:
    """Generate unique hash for request deduplication"""
    content = f"{session_id}:{message}:{user_id}"
    return hashlib.md5(content.encode()).hexdigest()

def _is_duplicate_request(session_id: str, message: str, user_id: int) -> bool:
    """Check if this is a duplicate request within TTL window"""
    _clean_expired_requests()
    request_hash = _get_request_hash(session_id, message, user_id)
    
    if request_hash in _REQUEST_CACHE:
        logger.info(f"🚫 API DEDUP: Blocked duplicate request - hash: {request_hash[:8]}...")
        return True
    
    # Mark this request as processed
    _REQUEST_CACHE[request_hash] = {'timestamp': time.time()}
    logger.info(f"✅ API DEDUP: Processing new request - hash: {request_hash[:8]}...")
    return False

@router.post(
    "/enhanced",
    response_model=ChatDTO,
    summary="Procesa mensaje con Universal Discovery"
)
async def chat_enhanced_endpoint(
    request: ChatRequestModel,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    NUEVO: Endpoint que usa Universal Discovery para zero-friction experience
    """
    try:
        # ✅ Usar factory async para producción con DI correcta
        service = await get_chat_service()
        
        # Usar método estándar del ChatService (ya incluye enhanced capabilities)
        resp = await service.process_chat(
            session_id=request.session_id,
            user_message=request.message,
            conversation=request.conversation or [],
            user_id=user_id,
            db_session=db,
            workflow_type=request.workflow_type  # ← PASAR WORKFLOW_TYPE
        )
        return map_chat_response_to_dto(resp)
    except InvalidDataException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.exception("Error processing /api/chat/enhanced")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "",
    response_model=ChatDTO,
    summary="Procesa un mensaje de chat"
)
async def chat_endpoint(
    request: ChatRequestModel,
    user_id: int = Depends(get_current_user_id),
    chat_service: IChatService = Depends(get_chat_service),
    chat_session_service = Depends(get_chat_session_service),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ REFACTORED: Procesa un mensaje de usuario usando FastAPI DI.
    """
    try:
        # 🔧 DISABLE: Removed aggressive deduplication that was blocking legitimate requests
        # The frontend duplication issue should be fixed at the source, not masked here
        
        # ✅ REFACTORED: Usar servicios inyectados via FastAPI DI
        
        # ✅ SIMPLIFIED: Simple session handling like backup
        session_id = request.session_id
        if session_id is None:
            # Create new session automatically
            session = await chat_session_service.create_session(user_id, "Nuevo chat")
            session_id = session["session_id"] if isinstance(session, dict) else session.session_id
        else:
            # Simple validation - if session doesn't exist, create new one
            try:
                await chat_session_service.get_session(session_id)
            except ValueError:
                # Session doesn't exist, create new one
                session = await chat_session_service.create_session(user_id, "Nuevo chat") 
                session_id = session["session_id"] if isinstance(session, dict) else session.session_id
                logger.info(f"Created replacement session {session_id}")
        
        resp = await chat_service.process_chat(
            session_id=session_id,
            user_message=request.message,
            conversation=request.conversation or [],
            user_id=user_id,
            workflow_type=request.workflow_type,
            db_session=db,
            # 🚨 NEW: Pass OAuth system message parameters
            oauth_completed=getattr(request, 'oauth_completed', None),
            system_message=getattr(request, 'system_message', None),
            continue_workflow=getattr(request, 'continue_workflow', False)
        )
        return map_chat_response_to_dto(resp)
    except InvalidDataException as e:
        # 400 en caso de datos inválidos
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.exception("Error processing /api/chat")
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/with-services", response_model=ChatDTO)
async def chat_with_selected_services(
    request: ChatWithServicesRequest,
    user_id: int = Depends(get_current_user_id),
    chat_service: IChatService = Depends(get_chat_service),
    db_session: AsyncSession = Depends(get_db)
):
    """
    Procesa chat después de que el usuario seleccionó servicios del dropdown
    """
    try:
        logger.info(f"Processing chat with selected services: {request.selected_services}")
        
        # Usar el workflow_type que viene del frontend (del switch)
        resp = await chat_service.process_chat(
            session_id=request.session_id,
            user_message=request.message,
            conversation=request.conversation,
            user_id=user_id,
            db_session=db_session,
            workflow_type=request.workflow_type,  # ✅ Del frontend
            selected_services=request.selected_services  # ✅ Pasar servicios seleccionados
        )
        
        return map_chat_response_to_dto(resp)
    except InvalidDataException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.exception("Error processing /api/chat/with-services")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/with-model",
    response_model=ChatDTO,
    summary="Chat with user-selected LLM model"
)
async def chat_with_custom_model(
    request: ChatRequestModel,
    model_key: str = None,  # Optional: if not provided, auto-selects best model
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    intelligent_llm: IntelligentLLMService = Depends(get_intelligent_llm_service)
):
    """
    Process chat using user-selected LLM model with intelligent selection,
    cost tracking, and usage analytics.
    
    This endpoint is for:
    - Custom agents created by users
    - Bill Agent with user-selected models
    - Any scenario where user chooses the LLM model
    
    Note: Kyra's internal operations still use the default LLMService.
    """
    try:
        # ✅ Usar factory async para producción con DI correcta
        service = await get_chat_service()
        
        # ✅ Delegar lógica de negocio al service
        resp = await service.process_chat_with_custom_model(
            session_id=request.session_id,
            user_message=request.message,
            conversation=request.conversation or [],
            user_id=user_id,
            db_session=db,
            model_key=model_key,
            intelligent_llm_service=intelligent_llm
        )
        
        return map_chat_response_to_dto(resp)
        
    except InvalidDataException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.exception("Error in chat with custom model")
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing chat with custom model: {str(e)}"
        )

@router.post(
    "/modify-workflow",
    response_model=ChatDTO,
    summary="Modifica workflow existente basado en feedback del usuario"
)
async def modify_workflow_endpoint(
    request: WorkflowModificationRequestModel,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint para modificar workflows existentes usando el LLM.
    """
    try:
        # ✅ Usar factory async para obtener el servicio
        service = await get_chat_service()
        
        # Usar método de modificación del ChatService
        resp = await service.handle_workflow_modification(
            chat_id=request.session_id,
            user_message=request.message,
            current_workflow=request.current_workflow,
            user_id=user_id,
            context={
                "conversation": request.conversation or []
            }
        )
        
        return map_chat_response_to_dto(resp)
        
    except InvalidDataException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.exception("Error in workflow modification")
        raise HTTPException(
            status_code=500, 
            detail=f"Error modifying workflow: {str(e)}"
        )


@router.post(
    "/approve-workflow/{session_id}",
    response_model=ChatDTO,
    summary="User approves workflow for execution"
)
async def approve_workflow_execution(
    session_id: str,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint for user to approve workflow execution after presentation.
    Triggers actual workflow execution via ReflectionService.
    """
    try:
        # Get chat service
        service = await get_chat_service()
        
        # Execute approved workflow
        resp = await service.execute_approved_workflow(
            session_id=session_id,
            user_id=user_id,
            db_session=db
        )
        
        return map_chat_response_to_dto(resp)
        
    except InvalidDataException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.exception("Error approving workflow execution")
        raise HTTPException(status_code=500, detail=f"Error approving workflow: {str(e)}")


@router.get(
    "/poll/{chat_id}",
    summary="Poll for new messages in chat"
)
async def poll_chat_messages(
    chat_id: UUID,
    last_message_timestamp: str = None,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint para polling de mensajes nuevos después de OAuth.
    Frontend puede usar esto para obtener actualizaciones.
    """
    try:
        from app.repositories.chat_session_repository import ChatSessionRepository
        from app.db.models import ChatMessage
        from sqlalchemy import select, desc
        from datetime import datetime
        
        chat_repo = ChatSessionRepository(db)
        
        # Construir query para mensajes nuevos
        query = (
            select(ChatMessage)
            .where(ChatMessage.session_id == chat_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(10)  # Últimos 10 mensajes
        )
        
        # Si se proporciona timestamp, filtrar solo mensajes más nuevos
        if last_message_timestamp:
            try:
                last_time = datetime.fromisoformat(last_message_timestamp.replace('Z', '+00:00'))
                query = query.where(ChatMessage.created_at > last_time)
            except Exception as e:
                logger.warning(f"Invalid timestamp format: {last_message_timestamp}, error: {e}")
        
        result = await db.execute(query)
        messages = result.scalars().all()
        
        # Convertir a formato JSON
        message_list = []
        for msg in messages:
            message_list.append({
                "message_id": str(msg.message_id),
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            })
        
        return {
            "chat_id": str(chat_id),
            "messages": message_list,
            "has_new_messages": len(message_list) > 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error polling chat messages: {e}")
        raise HTTPException(status_code=500, detail=f"Error polling messages: {str(e)}")


@router.get(
    "/workflow-status/{chat_id}",
    summary="Obtiene el estado real del workflow por chat_id"
)
async def get_workflow_status(
    chat_id: str,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint para obtener el estado real del workflow desde la base de datos
    Usado para sincronizar el switch del chat con el estado real
    """
    try:
        from app.services.chat_workflow_bridge_service import create_chat_workflow_bridge_service_manual
        
        # Crear bridge service manualmente
        bridge_service = await create_chat_workflow_bridge_service_manual(db)
        
        # Obtener estado real del workflow
        status = await bridge_service.get_workflow_real_status(chat_id, user_id)
        
        return {
            "success": True,
            "chat_id": chat_id,
            "workflow_status": status
        }
        
    except Exception as e:
        logger.error(f"Error getting workflow status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting workflow status: {str(e)}"
        )


# 🗑️ REMOVED: _get_workflow_from_context
# Router ya no extrae nada - delega TODO al planner y servicios


# 🗑️ REMOVED: Deprecated /workflow-context endpoint
# Frontend now uses execution_plan directly from LLM response metadata


@router.post(
    "/workflow-decision",
    summary="Procesa decisiones de workflow (guardar/activar/ejecutar)"
)
async def process_workflow_decision(
    request: dict,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint para procesar decisiones de workflow desde el frontend.
    Conecta WorkflowReviewComponent con ChatWorkflowBridgeService
    """
    try:
        logger.info(f"Processing workflow decision for user {user_id}")
        logger.info(f"🔄 ROUTER START: process_workflow_decision")
        logger.info(f"🔄 ROUTER STATE: db.is_active: {db.is_active}, in_transaction: {db.in_transaction()}")
        
        # Extraer datos del request
        decision = request.get("decision")  # "save", "activate", "execute"
        execution_plan = request.get("execution_plan", [])  # NEW: Direct from frontend
        workflow_context = request.get("workflow_context", {})  # DEPRECATED: Backward compatibility
        chat_id = request.get("chat_id")
        
        if not decision or not chat_id:
            raise HTTPException(
                status_code=400, 
                detail="Decision and chat_id are required"
            )
        
        if not execution_plan and not workflow_context:
            raise HTTPException(
                status_code=400,
                detail="Either execution_plan or workflow_context must be provided"
            )
        
        # 🔧 FIX: Usar factory manual para evitar errores de Depends
        from app.services.chat_workflow_bridge_service import create_chat_workflow_bridge_service_manual
        
        # Crear bridge service manualmente con todas las dependencias correctas
        bridge_service = await create_chat_workflow_bridge_service_manual(db)
        
        # Mapear decisiones del frontend a formato interno
        decision_mapping = {
            "save": "save_workflow",
            "activate": "save_and_activate_workflow", 
            "deactivate": "deactivate_workflow",
            "execute": "execute_workflow_now"
        }
        
        internal_decision = decision_mapping.get(decision)
        if not internal_decision:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid decision: {decision}. Must be 'save', 'activate', 'deactivate', or 'execute'"
            )
        
        # Procesar decisión a través del bridge service
        logger.info(f"🔄 ROUTER PRE-BRIDGE: About to call bridge_service.process_workflow_decision")
        logger.info(f"🔄 ROUTER PRE-BRIDGE STATE: db.in_transaction: {db.in_transaction()}")
        result = await bridge_service.process_workflow_decision(
            user_decision=internal_decision,
            execution_plan=execution_plan,
            user_id=user_id,
            chat_id=chat_id,
            workflow_context=workflow_context  # Deprecated: backward compatibility
        )
        logger.info(f"🔄 ROUTER POST-BRIDGE: bridge_service returned result: {result.status}")
        logger.info(f"🔄 ROUTER POST-BRIDGE STATE: db.in_transaction: {db.in_transaction()}")
        
        # Convertir resultado a formato API
        response = {
            "success": result.status not in ["error"],
            "status": result.status,
            "message": result.reply,
            "workflow_id": result.metadata.get("flow_id") if result.metadata else None,
            "execution_id": result.metadata.get("execution_id") if result.metadata else None,
            "metadata": result.metadata or {}
        }
        
        logger.info(f"Workflow decision processed successfully: {decision} for user {user_id}")
        logger.info(f"🔄 ROUTER SUCCESS: Returning response for decision {decision}")
        logger.info(f"🔄 ROUTER FINAL STATE: db.in_transaction: {db.in_transaction()}")
        
        # 🔧 EXPLICIT TRANSACTION HANDLING: Check if we need to commit or if auto-commit is handling it
        if db.in_transaction():
            logger.info(f"🔄 ROUTER COMMIT: Transaction is still active, this might be the issue!")
            logger.warning(f"🔄 ROUTER WARNING: Transaction should have been committed by bridge service")
        else:
            logger.info(f"🔄 ROUTER NO-TRANSACTION: No active transaction (expected after successful commit)")
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing workflow decision: {e}", exc_info=True)
        logger.error(f"🔄 ROUTER ERROR STATE: db.is_active: {db.is_active}, in_transaction: {db.in_transaction()}")
        
        # 🔧 ROLLBACK ON ERROR: Ensure we rollback on any uncaught errors
        if db.in_transaction():
            logger.error(f"🔄 ROUTER ROLLBACK: Rolling back transaction due to error...")
            await db.rollback()
            logger.error(f"🔄 ROUTER ROLLED BACK: Transaction rolled back")
        
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing workflow decision: {str(e)}"
        )

