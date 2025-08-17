# app/core/scheduler.py

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings

logger = logging.getLogger(__name__)

def init_scheduler() -> AsyncIOScheduler:
    """
    Inicializa el AsyncIOScheduler con Redis como JobStore.
    No arranca el loop aquí: solo crea la instancia.
    """
    jobstores = {
        'default': RedisJobStore(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.SCHEDULER_REDIS_DB,
            password=settings.REDIS_PASSWORD,
        )
    }
    scheduler = AsyncIOScheduler(jobstores=jobstores)
    return scheduler

# — Quitamos el scheduler.start() de nivel módulo —
scheduler = init_scheduler()

def start_scheduler() -> None:
    """
    Arranca el scheduler. Debe llamarse UNA VEZ,
    cuando ya exista un event loop (FastAPI startup).
    """
    scheduler.start()
    logger.info("Scheduler iniciado con RedisJobStore")

def get_scheduler() -> AsyncIOScheduler:
    """
    FastAPI dependency: devuelve la instancia global del scheduler.
    """
    return scheduler

def schedule_job(
    scheduler: AsyncIOScheduler,
    job_id: str,
    func: callable,
    trigger_type: str,
    trigger_args: dict,
    **kwargs
) -> None:
    if trigger_type == 'cron':
        trigger = CronTrigger(**trigger_args)
    elif trigger_type == 'interval':
        trigger = IntervalTrigger(**trigger_args)
    else:
        raise ValueError(f"Trigger desconocido: {trigger_type}")

    scheduler.add_job(
        func,
        trigger=trigger,
        id=job_id,
        replace_existing=True,
        kwargs=kwargs,
    )
    logger.info(f"Job programado: id={job_id}, tipo={trigger_type}, args={trigger_args}")

def unschedule_job(scheduler: AsyncIOScheduler, job_id: str) -> None:
    job = scheduler.get_job(job_id)
    if job:
        scheduler.remove_job(job_id)
        logger.info(f"Job cancelado: id={job_id}")
    else:
        logger.warning(f"No se encontró job con id={job_id} para cancelar")
