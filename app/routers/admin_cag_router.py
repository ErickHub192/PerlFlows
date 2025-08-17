# app/routers/admin_cag_router.py

from fastapi import APIRouter, Depends, HTTPException, status
from app.services.cag_service import ICAGService, get_cag_service
from app.core.auth import require_admin
from app.core.scheduler import get_scheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler

router = APIRouter()

@router.post(
    "/api/cag/regenerate",
    summary="Regenera manualmente el cache CAG (público)",
    tags=["cag"]
)
async def regenerate_cag_public(
    service: ICAGService = Depends(get_cag_service)
) -> dict:
    """
    Endpoint público para regenerar el cache CAG sin requerir privilegios de admin.
    """
    try:
        path = await service.regenerate()
        return {"status": "ok", "path": path}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error regenerando CAG cache: {e}"
        )

@router.post(
    "/api/admin/cag/regenerate",
    summary="Regenera manualmente el cache CAG (protegido para admins)",
    tags=["admin"],
    dependencies=[Depends(require_admin)]
)
async def regenerate_cag_admin(
    service: ICAGService = Depends(get_cag_service)
) -> dict:
    """
    Endpoint protegido que sólo pueden usar admins para regenerar el cache CAG.
    """
    try:
        path = await service.regenerate()
        return {"status": "ok", "path": path}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error regenerando CAG cache: {e}"
        )

@router.post(
    "/api/admin/scheduler/clear-phantom-jobs",
    summary="Limpia jobs fantasma del scheduler",
    tags=["admin"],
    dependencies=[Depends(require_admin)]
)
async def clear_phantom_jobs_admin(
    scheduler: AsyncIOScheduler = Depends(get_scheduler)
) -> dict:
    """
    🚨 EMERGENCY ENDPOINT: Limpia jobs fantasma de workflows eliminados (ADMIN)
    """
    return await _clear_phantom_jobs_impl(scheduler)


async def _clear_phantom_jobs_impl(scheduler: AsyncIOScheduler) -> dict:
    """
    🚨 EMERGENCY FUNCTION: Limpia jobs fantasma de workflows eliminados
    
    Identifica y elimina jobs de APScheduler que no tienen workflows correspondientes en BD.
    Útil para limpiar workflows fantasma que causan errores 404 cada 5 minutos.
    """
    import logging
    from app.repositories.flow_repository import FlowRepository
    from app.db.database import async_session
    
    logger = logging.getLogger(__name__)
    
    try:
        # Obtener todos los jobs activos del scheduler
        all_jobs = scheduler.get_jobs()
        logger.info(f"🔍 SCHEDULER CLEANUP: Found {len(all_jobs)} active jobs")
        
        # Obtener todos los flow_ids válidos de BD
        async with async_session() as session:
            flow_repo = FlowRepository(session)
            valid_flows = await flow_repo.list_all()
            valid_flow_ids = {str(flow.flow_id) for flow in valid_flows}
            logger.info(f"🔍 SCHEDULER CLEANUP: Found {len(valid_flow_ids)} valid flows in BD")
        
        
        # Identificar jobs fantasma (job_id no corresponde a flow válido)
        phantom_jobs = []
        for job in all_jobs:
            job_id = job.id
            # Los cron jobs usan flow_id como job_id
            if job_id not in valid_flow_ids:
                phantom_jobs.append(job)
                logger.warning(f"🚨 PHANTOM JOB DETECTED: {job_id} - no matching flow in BD")
        
        # Eliminar jobs fantasma
        removed_count = 0
        for phantom_job in phantom_jobs:
            try:
                scheduler.remove_job(phantom_job.id)
                removed_count += 1
                logger.info(f"✅ PHANTOM JOB REMOVED: {phantom_job.id}")
            except Exception as job_error:
                logger.error(f"❌ ERROR REMOVING JOB {phantom_job.id}: {job_error}")
        
        result = {
            "status": "success",
            "total_jobs_found": len(all_jobs),
            "valid_flows_in_bd": len(valid_flow_ids),
            "phantom_jobs_detected": len(phantom_jobs),
            "phantom_jobs_removed": removed_count,
            "phantom_job_ids": [job.id for job in phantom_jobs]
        }
        
        logger.info(f"🧹 SCHEDULER CLEANUP COMPLETED: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ SCHEDULER CLEANUP ERROR: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cleaning phantom jobs: {str(e)}"
        )
