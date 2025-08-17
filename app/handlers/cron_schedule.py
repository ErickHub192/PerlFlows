import time
from typing import Any, Dict
from uuid import UUID
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.connectors.factory import register_node, execute_node
from app.core.scheduler import schedule_job, unschedule_job
from app.utils.cron_utils import validate_cron_expression
from .connector_handler import ActionHandler
from .trigger_registry import register_trigger_capability


async def execute_cron_job(node_name: str, action_name: str, params: dict, creds: dict):
    """
    🔧 SERIALIZABLE FUNCTION: Función serializable para ejecutar cron jobs
    Esta función puede ser referenciada por el scheduler como texto
    
    ✅ UNIVERSAL FIX: Usa helper centralizado para ejecutar workflows completos
    desde cualquier tipo de trigger
    """
    import logging
    from app.handlers.workflow_execution_helper import should_execute_workflow, extract_trigger_metadata, execute_complete_workflow
    
    logger = logging.getLogger(__name__)
    logger.info(f"🚀 CRON JOB EXECUTION: Processing {node_name}.{action_name}")
    
    # 🎯 UNIVERSAL: Verificar si debe ejecutar workflow completo o solo el nodo
    if await should_execute_workflow(node_name, action_name, params):
        # Extraer metadatos del trigger
        flow_id, user_id, trigger_data = extract_trigger_metadata(params)
        
        if not flow_id or not user_id:
            logger.error(f"❌ CRON JOB: Missing flow_id or user_id in params: {params}")
            return {
                "status": "error",
                "error": "Missing flow_id or user_id in cron job parameters"
            }
        
        # 🚀 UNIVERSAL: Ejecutar workflow completo usando helper centralizado
        return await execute_complete_workflow(
            flow_id=flow_id,
            user_id=user_id,
            trigger_data=trigger_data,
            inputs={}  # No inputs iniciales para cron jobs
        )
    
    # Para ejecuciones individuales de nodos (sin workflow)
    else:
        logger.info(f"🔧 CRON JOB: Executing single node {node_name}.{action_name}")
        return await execute_node(node_name, action_name, params, creds)


@register_node("Cron_Trigger.schedule")
@register_trigger_capability("cron", "Cron_Trigger.schedule")
class CronScheduleHandler(ActionHandler):
    """
    ✅ REFACTORIZADO: Handler completo para triggers cron
    
    Funcionalidades:
    1. Valida expresión cron
    2. Programa job en scheduler
    3. Retorna job_id para cancelación posterior
    
    Parámetros esperados en params:
      • cron_expression: str con 5 campos cron (min hour day month dow)
      • flow_id: UUID del flujo a ejecutar
      • user_id: ID del usuario
      • first_step: Dict con el primer paso del workflow
      • scheduler: AsyncIOScheduler instance
      • creds: Credenciales del usuario
    """

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start = time.perf_counter()
        
        # Validar parámetros requeridos
        cron_expression = params.get("cron_expression")
        flow_id = params.get("flow_id")
        user_id = params.get("user_id")
        first_step = params.get("first_step")
        scheduler = params.get("scheduler")
        creds = params.get("creds", {})
        
        if not cron_expression:
            return {
                "status": "error",
                "error": "Debe proporcionar 'cron_expression'",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }

        # Validar formato cron
        parts = cron_expression.split()
        if len(parts) != 5:
            return {
                "status": "error",
                "error": f"Cron inválido: '{cron_expression}' debe tener 5 campos",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }

        minute, hour, day, month, day_of_week = parts
        
        # Validar expresión cron completa
        full_expr = " ".join([minute, hour, day, month, day_of_week])
        if not validate_cron_expression(full_expr):
            return {
                "status": "error",
                "error": f"Expresión cron inválida: '{full_expr}'",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }

        # Si es solo validación/preparación, retornar trigger_args
        if not scheduler or not flow_id or not first_step:
            duration_ms = int((time.perf_counter() - start) * 1000)
            return {
                "status": "success",
                "output": {
                    "trigger_type": "cron",
                    "trigger_args": {
                        "minute": minute,
                        "hour": hour,
                        "day": day,
                        "month": month,
                        "day_of_week": day_of_week,
                    },
                    "cron_expression": cron_expression
                },
                "duration_ms": duration_ms,
            }

        # ✅ NUEVA FUNCIONALIDAD: Programar job real
        try:
            job_id = str(flow_id)
            
            # Crear trigger_args para el scheduler
            trigger_args = {
                "minute": minute,
                "hour": hour, 
                "day": day,
                "month": month,
                "day_of_week": day_of_week,
            }
            
            # 🔧 CRITICAL FIX: Incluir flow_id y user_id en params para workflow execution
            workflow_params = {
                **first_step.get("params", {}),
                "flow_id": flow_id,
                "user_id": user_id,
                "first_step": first_step  # Incluir first_step para compatibilidad
            }
            
            # Programar job en scheduler
            schedule_job(
                scheduler,
                job_id,
                func=execute_cron_job,  # 🔧 FIX: Pasar función directa en lugar de string
                trigger_type="cron",
                trigger_args=trigger_args,
                # Pasar como kwargs para que schedule_job los forwarde correctamente
                node_name=first_step["node_name"],
                action_name=first_step["action_name"], 
                params=workflow_params,  # 🔧 CRITICAL: Usar params enriquecidos con flow_id y user_id
                creds=creds
            )
            
            duration_ms = int((time.perf_counter() - start) * 1000)
            return {
                "status": "success",
                "output": {
                    "trigger_type": "cron",
                    "job_id": job_id,
                    "scheduled": True,
                    "cron_expression": cron_expression,
                    "trigger_args": trigger_args,
                },
                "duration_ms": duration_ms,
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "error": f"Error programando cron job: {str(e)}",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
    
    async def unschedule(self, scheduler: AsyncIOScheduler, job_id: str) -> Dict[str, Any]:
        """
        ✅ NUEVA: Funcionalidad para cancelar jobs programados
        """
        try:
            unschedule_job(scheduler, job_id)
            return {
                "status": "success",
                "message": f"Job {job_id} cancelado exitosamente"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error cancelando job {job_id}: {str(e)}"
            }