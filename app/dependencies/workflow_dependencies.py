# app/dependencies/workflow_dependencies.py

import logging
from fastapi import Depends

logger = logging.getLogger(__name__)
from app.workflow_engine.core.workflow_engine_simple import SimpleWorkflowEngine
from app.workflow_engine.core.simple_engine_factory import SimpleWorkflowEngineFactory
from app.services.cag_service import get_cag_service
from app.services.auto_auth_trigger import get_auto_auth_trigger

async def get_simple_workflow_engine(
    chat_id: str = None,
    cag_service = Depends(get_cag_service),
    auto_auth_trigger = Depends(get_auto_auth_trigger)
) -> SimpleWorkflowEngine:
    """
    🔥 UPDATED: Uses WorkflowEngineManager for singleton behavior
    ✅ Maintains same instance per chat_id to preserve Kyra's identity
    """
    from app.workflow_engine.core.workflow_engine_manager import WorkflowEngineManager
    
    if not chat_id:
        # Para casos donde no hay chat_id específico, generar uno temporal
        from uuid import uuid4
        chat_id = str(uuid4())
        logger.warning(f"⚠️ WORKFLOW ENGINE: No chat_id provided, generated temporary: {chat_id}")
    else:
        logger.info(f"✅ WORKFLOW ENGINE: Using provided chat_id: {chat_id}")
    
    # ✅ FIX: Verificar si estamos en contexto FastAPI o llamada manual
    from fastapi.dependencies.utils import get_dependant
    # Verificar si son objetos Depends sin resolver
    is_depends_cag = hasattr(cag_service, 'dependency') if cag_service else False
    is_depends_auth = hasattr(auto_auth_trigger, 'dependency') if auto_auth_trigger else False
    
    if is_depends_cag or is_depends_auth:
        # Llamada manual sin contexto FastAPI - pasar None para que el manager cree dependencies manualmente
        logger.info("🔧 MANUAL CALL: Creating dependencies manually (no FastAPI context)")
        return await WorkflowEngineManager.get_or_create(
            chat_id=chat_id,
            cag_service=None,
            auto_auth_trigger=None
        )
    else:
        # Contexto FastAPI normal - usar dependencias resueltas
        logger.info("🔧 FASTAPI CONTEXT: Using resolved dependencies")
        return await WorkflowEngineManager.get_or_create(
            chat_id=chat_id,
            cag_service=cag_service,
            auto_auth_trigger=auto_auth_trigger
        )


