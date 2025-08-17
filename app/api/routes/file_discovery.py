"""
🔥 UPDATED: Router de File Discovery - Descubrimiento de archivos/metadata de nodos
Solo orquestación, recibe credenciales de UnifiedOAuthManager
NO confundir con Auth Service Discovery
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status

from app.dtos.file_discovery_dto import (
    FileDiscoveryRequestDTO, 
    FileDiscoveryResponseDTO,
    DiscoveredFileDTO
)
from app.services.file_discovery_service import FileDiscoveryService, get_file_discovery_service
from app.core.auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/file-discovery", tags=["file-discovery"])


@router.post("/discover", response_model=FileDiscoveryResponseDTO)
async def discover_files(
    request: FileDiscoveryRequestDTO,
    current_user: Dict[str, Any] = Depends(get_current_user_id),
    discovery_service: FileDiscoveryService = Depends(get_file_discovery_service)
):
    """
    Descubre recursos del usuario basado en nodos seleccionados por Kyra
    """
    try:
        user_id = current_user["user_id"]
        logger.info(f"Starting resource discovery for user {user_id}")
        
        # ✅ UPDATED: Usar nueva arquitectura - planned_steps desde request
        planned_steps = request.planned_steps if hasattr(request, 'planned_steps') else []
        
        if not planned_steps:
            logger.warning("No planned steps provided - file discovery requires specific nodes")
            discovered_files = []
        else:
            logger.info(f"Using {len(planned_steps)} planned steps for node-specific discovery")
            discovered_files = await discovery_service.discover_user_files(
                user_id=user_id,
                planned_steps=planned_steps,
                file_types=request.file_types
            )
        
        # Convertir a DTOs
        file_dtos = [
            DiscoveredFileDTO(
                id=file.id,
                name=file.name,
                provider=file.provider,
                file_type=file.file_type,
                confidence=file.confidence,
                structure=file.structure,
                icon=file.icon,
                metadata=file.metadata
            )
            for file in discovered_files
        ]
        
        # Extraer providers usados
        providers_used = list(set(file.provider for file in discovered_files))
        
        return FileDiscoveryResponseDTO(
            discovered_files=file_dtos,
            total_files=len(file_dtos),
            providers_used=providers_used,
            message=f"Se descubrieron {len(file_dtos)} recursos de {len(providers_used)} providers"
        )
        
    except Exception as e:
        logger.error(f"Error en discovery: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error descubriendo recursos: {str(e)}"
        )


@router.get("/available-handlers")
async def get_available_handlers():
    """Lista los handlers de discovery disponibles"""
    try:
        from app.handlers.discovery.discovery_factory import list_available_handlers
        handlers = list_available_handlers()
        
        return {
            "handlers": handlers,
            "total": len(handlers),
            "message": f"{len(handlers)} handlers de discovery disponibles"
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo handlers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo handlers disponibles"
        )