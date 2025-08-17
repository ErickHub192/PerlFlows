"""
🚀 WORKFLOW EXECUTION HELPER
Función centralizada para ejecutar workflows completos desde cualquier trigger
Esto asegura que TODOS los triggers (cron, webhook, gmail, etc.) ejecuten workflows completos
"""
import logging
from typing import Dict, Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)

async def execute_complete_workflow(
    flow_id: UUID,
    user_id: int,
    trigger_data: Dict[str, Any] = None,
    inputs: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    🎯 FUNCIÓN CENTRALIZADA: Ejecuta un workflow completo desde cualquier trigger
    
    Esta función es utilizada por TODOS los triggers para asegurar que 
    los workflows se ejecuten completamente a través del WorkflowRunner
    
    Args:
        flow_id: UUID del workflow a ejecutar
        user_id: ID del usuario propietario
        trigger_data: Datos específicos del trigger (email data, webhook payload, etc.)
        inputs: Inputs adicionales para el workflow
        
    Returns:
        Dict con resultado de la ejecución
    """
    try:
        logger.info(f"🚀 WORKFLOW EXECUTION: Starting complete workflow {flow_id} for user {user_id}")
        
        # Importar dependencias necesarias
        from app.db.database import get_db
        from app.services.workflow_runner_service import create_workflow_runner_manual
        from app.services.flow_service import create_flow_service_manual
        
        # Crear sesión de BD
        db_gen = get_db()
        db_session = await anext(db_gen)
        
        try:
            # Crear flow service para obtener la spec del workflow
            flow_service = await create_flow_service_manual(db_session)
            
            # Obtener el workflow completo
            flow = await flow_service.repo.get_by_id(flow_id)
            if not flow:
                logger.error(f"❌ WORKFLOW EXECUTION: Flow {flow_id} not found")
                return {
                    "status": "error",
                    "error": f"Flow {flow_id} not found"
                }
            
            # Verificar que el workflow esté activo
            if not flow.is_active:
                logger.warning(f"⚠️ WORKFLOW EXECUTION: Flow {flow_id} is not active, skipping execution")
                return {
                    "status": "skipped",
                    "message": f"Flow {flow_id} is not active"
                }
            
            # Verificar propiedad del usuario
            if flow.owner_id != user_id:
                logger.error(f"❌ WORKFLOW EXECUTION: Flow {flow_id} does not belong to user {user_id}")
                return {
                    "status": "error",
                    "error": f"Flow {flow_id} does not belong to user {user_id}"
                }
            
            # Extraer los steps del workflow spec
            workflow_spec = flow.spec
            steps = workflow_spec.get("steps", [])
            
            if not steps:
                logger.error(f"❌ WORKFLOW EXECUTION: No steps found in workflow {flow_id}")
                return {
                    "status": "error",
                    "error": f"No steps found in workflow {flow_id}"
                }
            
            # Preparar inputs del workflow
            workflow_inputs = inputs or {}
            
            # Si hay trigger_data, agregarlo a los inputs para que esté disponible en todos los steps
            if trigger_data:
                workflow_inputs["trigger_data"] = trigger_data
                logger.info(f"🎯 WORKFLOW EXECUTION: Added trigger_data to workflow inputs")
            
            logger.info(f"🚀 WORKFLOW EXECUTION: Executing workflow {flow_id} with {len(steps)} steps")
            
            # Crear workflow runner
            workflow_runner = await create_workflow_runner_manual(db_session)
            
            # Ejecutar el workflow completo
            execution_id, result = await workflow_runner.execute_workflow_steps(
                steps=steps,
                user_id=user_id,
                inputs=workflow_inputs,
                simulate=False,
                flow_id=flow_id
            )
            
            logger.info(f"✅ WORKFLOW EXECUTION: Workflow {flow_id} executed successfully. Execution ID: {execution_id}, Status: {result.overall_status}")
            
            return {
                "status": "success",
                "output": {
                    "execution_id": str(execution_id),
                    "workflow_status": result.overall_status,
                    "steps_executed": len(result.steps),
                    "flow_id": str(flow_id),
                    "user_id": user_id
                }
            }
            
        finally:
            await db_session.close()
            
    except Exception as e:
        logger.error(f"❌ WORKFLOW EXECUTION ERROR: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": f"Workflow execution failed: {str(e)}"
        }


async def should_execute_workflow(node_name: str, action_name: str, params: Dict[str, Any]) -> bool:
    """
    🎯 HELPER: Determina si los parámetros indican que se debe ejecutar un workflow completo
    
    Args:
        node_name: Nombre del nodo trigger
        action_name: Acción del trigger
        params: Parámetros del trigger
        
    Returns:
        True si se debe ejecutar workflow completo, False si solo el nodo individual
    """
    # Verificar si hay flow_id en los parámetros
    flow_id = params.get("flow_id")
    user_id = params.get("user_id")
    
    # Si hay flow_id y user_id, es un trigger de workflow
    if flow_id and user_id:
        logger.info(f"🎯 WORKFLOW DETECTION: Detected workflow trigger - {node_name}.{action_name} for flow {flow_id}")
        return True
    
    # Si no hay flow_id, es una ejecución individual de nodo
    logger.info(f"🔧 NODE EXECUTION: Detected individual node execution - {node_name}.{action_name}")
    return False


def extract_trigger_metadata(params: Dict[str, Any]) -> tuple[Optional[UUID], Optional[int], Dict[str, Any]]:
    """
    🎯 HELPER: Extrae metadatos del trigger para ejecución de workflow
    
    Args:
        params: Parámetros del trigger
        
    Returns:
        Tuple con (flow_id, user_id, trigger_data)
    """
    flow_id = params.get("flow_id")
    user_id = params.get("user_id")
    
    # Convertir flow_id a UUID si es string
    if isinstance(flow_id, str):
        try:
            flow_id = UUID(flow_id)
        except ValueError:
            logger.error(f"❌ TRIGGER METADATA: Invalid flow_id format: {flow_id}")
            flow_id = None
    
    # Extraer datos específicos del trigger
    trigger_data = {}
    for key, value in params.items():
        if key not in ["flow_id", "user_id", "first_step", "scheduler", "creds"]:
            trigger_data[key] = value
    
    return flow_id, user_id, trigger_data