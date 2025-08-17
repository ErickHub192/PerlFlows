# app/routers/ai_agent_router.py

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.db.models import AgentStatus

from app.db.database import get_db
from app.services.ai_agent_service import AIAgentService, get_ai_agent_service
from app.services.agent_run_service import AgentRunService, get_agent_run_service
from app.dtos.ai_agent_dto import AIAgentDTO
from app.dtos.ai_agent_create_request_dto import AIAgentCreateRequestDTO
from app.dtos.ai_agent_update_request_dto import AIAgentUpdateRequestDTO
from app.dtos.ai_agent_deploy_request_dto import AIAgentDeployRequestDTO
from app.dtos.agent_run_dto import (
    AgentRunDTO,
    AgentRunsListResponseDTO,
    AgentRunStatisticsDTO,
    AgentRunAnalyticsDTO,
    CreateAgentRunDTO,
    UpdateAgentRunDTO
)
from app.services.IAgentDeploymentService import IAgentDeploymentService
from app.services.agent_deployment_service import get_agent_deployment_service

# Fusión: Imports del ai_agent_runner_router
from fastapi import Header, Path
from fastapi.responses import JSONResponse
from app.dtos.ai_agent_request_dto import AIAgentRequestDTO
from app.dtos.ai_agent_response_dto import AIAgentResponseDTO

router = APIRouter(prefix="/api/ai_agents", tags=["ai_agents"])
logger = logging.getLogger(__name__)


@router.get(
    "/",
    response_model=List[AIAgentDTO],
    summary="Lista todos los agentes AI configurados"
)
async def list_agents(
    service: AIAgentService = Depends(get_ai_agent_service)
) -> List[AIAgentDTO]:
    return await service.list_agents()


@router.get(
    "/{agent_id}",
    response_model=AIAgentDTO,
    summary="Recupera un agente AI por su ID"
)
async def get_agent(
    agent_id: UUID,
    service: AIAgentService = Depends(get_ai_agent_service)
) -> AIAgentDTO:
    agent = await service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    return agent


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=AIAgentDTO,
    summary="Crea un nuevo agente AI con validación de modelo LLM"
)
async def create_agent(
    agent_req: AIAgentCreateRequestDTO,
    service: AIAgentService = Depends(get_ai_agent_service)
) -> AIAgentDTO:
    created = await service.create_agent(agent_req)
    return created


@router.patch(
    "/{agent_id}",
    response_model=AIAgentDTO,
    summary="Actualiza un agente AI existente con validación de modelo LLM"
)
async def update_agent(
    agent_id: UUID,
    agent_req: AIAgentUpdateRequestDTO,
    service: AIAgentService = Depends(get_ai_agent_service)
) -> AIAgentDTO:
    updated = await service.update_agent(agent_id, agent_req)
    if not updated:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    return updated


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Elimina un agente AI por su ID"
)
async def delete_agent(
    agent_id: UUID,
    service: AIAgentService = Depends(get_ai_agent_service)
) -> None:
    success = await service.delete_agent(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agente no encontrado")


@router.get(
    "/{agent_id}/model-config",
    summary="Obtiene la configuración del modelo LLM del agente"
)
async def get_agent_model_config(
    agent_id: UUID,
    service: AIAgentService = Depends(get_ai_agent_service)
):
    """Obtiene la configuración completa del modelo LLM asignado al agente"""
    return await service.get_agent_model_config(agent_id)


@router.get(
    "/models/available",
    summary="Lista modelos LLM disponibles para agentes"
)
async def list_available_models(
    service: AIAgentService = Depends(get_ai_agent_service)
):
    """Lista todos los modelos LLM disponibles para asignar a agentes"""
    return await service.list_available_models_for_agents()


# ===============================
# AGENT RUNS ENDPOINTS
# ===============================

@router.get(
    "/{agent_id}/runs",
    response_model=AgentRunsListResponseDTO,
    summary="Lista las ejecuciones de un agente"
)
async def list_agent_runs(
    agent_id: UUID,
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    status: Optional[AgentStatus] = Query(None, description="Filtrar por estado"),
    run_service: AgentRunService = Depends(get_agent_run_service)
):
    """Lista las ejecuciones de un agente con paginación y filtros opcionales"""
    try:
        return await run_service.list_agent_runs(
            agent_id=agent_id,
            page=page,
            page_size=page_size,
            status=status
        )
    except Exception as e:
        logger.error(f"Error listing runs for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener las ejecuciones")


@router.get(
    "/{agent_id}/runs/statistics",
    response_model=AgentRunStatisticsDTO,
    summary="Obtiene estadísticas de ejecución de un agente"
)
async def get_agent_statistics(
    agent_id: UUID,
    run_service: AgentRunService = Depends(get_agent_run_service)
):
    """Obtiene estadísticas de éxito, fallas y rendimiento de un agente"""
    try:
        return await run_service.get_agent_statistics(agent_id)
    except Exception as e:
        logger.error(f"Error getting statistics for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener estadísticas")


@router.get(
    "/{agent_id}/runs/analytics",
    response_model=AgentRunAnalyticsDTO,
    summary="Obtiene analytics completos de un agente"
)
async def get_agent_analytics(
    agent_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Días de historial"),
    recent_limit: int = Query(10, ge=1, le=50, description="Límite de ejecuciones recientes"),
    run_service: AgentRunService = Depends(get_agent_run_service)
):
    """Obtiene analytics completos: estadísticas, ejecuciones recientes y tendencias diarias"""
    try:
        return await run_service.get_agent_analytics(
            agent_id=agent_id,
            days=days,
            recent_runs_limit=recent_limit
        )
    except Exception as e:
        logger.error(f"Error getting analytics for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener analytics")


@router.get(
    "/{agent_id}/runs/recent",
    response_model=List[AgentRunDTO],
    summary="Obtiene actividad reciente de un agente"
)
async def get_recent_activity(
    agent_id: UUID,
    days: int = Query(7, ge=1, le=30, description="Días de actividad reciente"),
    limit: int = Query(10, ge=1, le=50, description="Número máximo de ejecuciones"),
    run_service: AgentRunService = Depends(get_agent_run_service)
):
    """Obtiene las ejecuciones más recientes de un agente"""
    try:
        return await run_service.get_recent_activity(
            agent_id=agent_id,
            days=days,
            limit=limit
        )
    except Exception as e:
        logger.error(f"Error getting recent activity for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener actividad reciente")


@router.get(
    "/{agent_id}/runs/trend",
    summary="Obtiene tendencia de éxito de un agente"
)
async def get_success_trend(
    agent_id: UUID,
    days: int = Query(30, ge=1, le=90, description="Días para la tendencia"),
    run_service: AgentRunService = Depends(get_agent_run_service)
):
    """Obtiene la tendencia de tasa de éxito diaria para gráficos"""
    try:
        return await run_service.get_success_trend(
            agent_id=agent_id,
            days=days
        )
    except Exception as e:
        logger.error(f"Error getting success trend for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener tendencia")


@router.get(
    "/runs/{run_id}",
    response_model=AgentRunDTO,
    summary="Obtiene detalles de una ejecución específica"
)
async def get_run_details(
    run_id: UUID,
    run_service: AgentRunService = Depends(get_agent_run_service)
):
    """Obtiene los detalles completos de una ejecución específica"""
    try:
        run = await run_service.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Ejecución no encontrada")
        return run
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting run {run_id}: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener la ejecución")


@router.post(
    "/{agent_id}/runs",
    response_model=AgentRunDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Crea una nueva ejecución de agente"
)
async def create_agent_run(
    agent_id: UUID,
    run_request: CreateAgentRunDTO,
    run_service: AgentRunService = Depends(get_agent_run_service)
):
    """Crea una nueva ejecución para un agente"""
    try:
        # Ensure agent_id matches the path parameter
        run_request.agent_id = agent_id
        return await run_service.create_run(run_request)
    except Exception as e:
        logger.error(f"Error creating run for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Error al crear la ejecución")


@router.patch(
    "/runs/{run_id}",
    response_model=AgentRunDTO,
    summary="Actualiza el estado de una ejecución"
)
async def update_run_status(
    run_id: UUID,
    update_request: UpdateAgentRunDTO,
    run_service: AgentRunService = Depends(get_agent_run_service)
):
    """Actualiza el estado y resultado de una ejecución"""
    try:
        updated_run = await run_service.update_run_status(run_id, update_request)
        if not updated_run:
            raise HTTPException(status_code=404, detail="Ejecución no encontrada")
        return updated_run
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating run {run_id}: {e}")
        raise HTTPException(status_code=500, detail="Error al actualizar la ejecución")


@router.post(
    "/{agent_id}/deploy",
    summary="Despliega un agente AI en un canal"
)
async def deploy_agent(
    agent_id: UUID,
    req: AIAgentDeployRequestDTO,
    deployment_service: IAgentDeploymentService = Depends(get_agent_deployment_service),
) -> dict:
    """Despliega un agente AI en el canal especificado."""
    # ✅ Delegar toda la lógica de negocio al service
    return await deployment_service.deploy_agent(agent_id, req)


# ===============================
# AGENT EXECUTION (fusionado de ai_agent_runner_router.py)
# ===============================

@router.post(
    "/{agent_id}/run",
    response_model=AIAgentResponseDTO,
    summary="Ejecuta un agente AI con el prompt indicado"
)
async def run_agent(
    agent_id: UUID = Path(..., description="ID del agente a ejecutar"),
    request: AIAgentRequestDTO = Depends(),
    x_api_key: str = Header(..., alias="X-API-Key"),
    service: AIAgentService = Depends(get_ai_agent_service)
):
    """
    Lanza el agente AI identificado por `agent_id` con los parámetros:
      - model:         nombre del modelo (p.ej. 'gpt-4.1')
      - temperature:   nivel de aleatoriedad
      - prompt:        mensaje del usuario

    La API key se provee en el header `X-API-Key`.
    
    SINGLE SOURCE OF TRUTH: Uses AIAgentService directly instead of Handler.
    """
    try:
        # Execute agent via service (SINGLE SOURCE OF TRUTH)
        # Service handles all business logic and returns DTO-ready format
        return await service.execute_agent_for_api(
            agent_id=agent_id,
            user_prompt=request.prompt,
            api_key=x_api_key,
            temperature=request.temperature,
            model=request.model  # Pass model for validation
        )
    except Exception as e:
        logger.error(f"Router agent execution error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error executing agent: {str(e)}")
