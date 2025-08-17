# app/services/trigger_orchestrator_service.py

from uuid import UUID
from typing import Dict, Any, List

from fastapi import Depends, HTTPException, status

# Interface removed - using concrete class
from app.services.flow_definition_service import FlowDefinitionService
from app.repositories.credential_repository import CredentialRepository, get_credential_repository
from app.repositories.flow_repository import FlowRepository
from app.repositories.flow_repository import get_flow_repository
from app.repositories.trigger_repository import TriggerRepository, get_trigger_repository
from app.repositories.node_repository import NodeRepository, get_node_repository
from app.repositories.action_repository import ActionRepository, get_action_repository
from app.core.scheduler import get_scheduler
from app.connectors.factory import execute_node
from app.services.flow_definition_service import get_flow_definition_service
from app.handlers.trigger_registry import get_trigger_registry



class TriggerOrchestratorService:
    """
    Servicio que programa y cancela triggers usando el primer nodo del flujo.
    """
    def __init__(
        self,
        def_service: FlowDefinitionService,
        cred_repo: CredentialRepository,
        flow_repo: FlowRepository,
        trigger_repo: TriggerRepository,
        node_repo: NodeRepository,
        action_repo: ActionRepository,
        scheduler,
    ):
        self.def_service = def_service
        self.cred_repo = cred_repo
        self.flow_repo = flow_repo
        self.trigger_repo = trigger_repo
        self.node_repo = node_repo
        self.action_repo = action_repo
        self.scheduler = scheduler

    def _validate_workflow_spec(self, spec: Dict[str, Any]) -> bool:
        """
        🔍 VALIDATION: Valida que el workflow no contenga nodos fallback
        """
        steps = spec.get("steps", [])
        
        for step in steps:
            node_type = step.get("node_type", "")
            
            # Detectar patrones fallback
            if any(pattern in node_type.lower() for pattern in 
                   ["fallback", "error", "unavailable", "quota_exceeded"]):
                return False
                
            # Detectar acciones fallback
            if "fallback_action" in str(step):
                return False
        
        return True

    async def schedule_flow(
        self,
        flow_id: UUID,
        spec: Dict[str, Any],
        user_id: int
    ) -> None:
        # 🚨 FIX: Limpiar triggers existentes antes de crear nuevos
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🔧 SCHEDULE: Checking for existing triggers for flow {flow_id}")
        
        existing_triggers = await self.trigger_repo.get_active_triggers(flow_id)
        if existing_triggers:
            logger.info(f"🔧 SCHEDULE: Found {len(existing_triggers)} existing triggers, cleaning up...")
            await self.unschedule_flow(flow_id, spec, user_id)
            logger.info(f"🔧 SCHEDULE: Cleanup completed, proceeding with new scheduling")
        
        # 🔍 VALIDATION: Verificar que no sea workflow fallback
        if not self._validate_workflow_spec(spec):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="❌ Cannot schedule fallback workflow. Please recreate the workflow."
            )
        
        # Asumimos que el primer paso del spec es el nodo trigger
        first = spec["steps"][0]
        
        creds = await self.cred_repo.get_credential(user_id, first.get("default_auth"))

        # Validar y ejecutar handler del trigger para obtener trigger_type y trigger_args
        params = dict(first.get("params", {}))
        params["flow_id"] = flow_id
        result = await execute_node(
            first["node_name"],
            first["action_name"],
            params,
            creds
        )

        output = result.get("output", {}) or {}
        trigger_type = output.get("trigger_type")
        trigger_args = output.get("trigger_args")

        if not trigger_type or not trigger_args:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Handler no devolvió trigger_type o trigger_args válidos",
            )

        # ✅ REFACTORIZADO: Usar registry modular para scheduling
        trigger_registry = get_trigger_registry()
        
        # Preparar parámetros completos para scheduling
        schedule_params = {
            **params,
            "scheduler": self.scheduler,
            "user_id": user_id,
            "first_step": first,
            "creds": creds
        }
        
        # Usar registry para scheduling
        schedule_result = await trigger_registry.schedule_trigger(trigger_type, schedule_params)
        
        if schedule_result.get("status") != "success":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error scheduling trigger: {schedule_result.get('error', 'Unknown error')}",
            )
        
        # Extraer job_id del resultado (flexible para diferentes tipos)
        output = schedule_result.get("output", {})
        job_id = output.get("job_id") or output.get("webhook_id") or str(flow_id)

        # 🔧 FIX: Resolver node_id y action_id para satisfacer constraints de BD
        node_id = None
        action_id = None
        
        # Solo intentar resolver IDs si tenemos los repositorios (contexto manual)
        if self.node_repo is not None and self.action_repo is not None:
            # Resolver node_id desde el nombre del nodo
            node_name = first["node_name"]
            node = await self.node_repo.get_node_by_name(node_name)
            if node:
                node_id = node.node_id
                
                # Resolver action_id desde el nombre de la acción y node_id
                action_name = first["action_name"]
                actions = await self.action_repo.list_actions(node_id)
                for action in actions:
                    if action.name == action_name:
                        action_id = action.action_id
                        break

        # Guardar registro del trigger en base de datos
        await self.trigger_repo.create_trigger(
            flow_id=flow_id,
            node_id=node_id,      # ✅ FIX: Usar node_id resuelto (o None si no se pudo resolver)
            action_id=action_id,  # ✅ FIX: Usar action_id resuelto (o None si no se pudo resolver)
            trigger_type=trigger_type,
            trigger_args=trigger_args,
            job_id=job_id,
        )

    async def unschedule_flow(
        self,
        flow_id: UUID,
        spec: Dict[str, Any],
        user_id: int
    ) -> None:
        # ✅ REFACTORIZADO: Usar registry modular para unscheduling
        trigger_registry = get_trigger_registry()
        triggers = await self.trigger_repo.get_active_triggers(flow_id)

        for trig in triggers:
            try:
                # Usar registry para unscheduling - escalable para cualquier tipo
                result = await trigger_registry.unschedule_trigger(
                    trigger_type=trig.trigger_type,
                    job_id=trig.job_id,
                    scheduler=self.scheduler
                )
                
                # 🔧 FIX: Propagar error si unschedule falla para mantener consistencia BD-Scheduler
                if result.get("status") != "success":
                    import logging
                    logger = logging.getLogger(__name__)
                    error_msg = f"Failed to unschedule trigger {trig.job_id}: {result.get('error')}"
                    logger.error(f"🚨 UNSCHEDULE FAILED: {error_msg}")
                    raise Exception(error_msg)
                        
            except Exception as e:
                # 🔧 FIX: Propagar error en lugar de solo WARNING para mantener consistencia
                import logging
                logger = logging.getLogger(__name__)
                error_msg = f"Error unscheduling trigger {trig.job_id}: {e}"
                logger.error(f"🚨 UNSCHEDULE ERROR: {error_msg}")
                # No continuar - esto previene workflows fantasma
                raise Exception(error_msg)
            
            # 🔧 FIX: Solo eliminar registro de BD si unschedule fue exitoso
            await self.trigger_repo.delete_trigger(trig.trigger_id)
            
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"✅ UNSCHEDULE SUCCESS: Trigger {trig.job_id} unscheduled and removed from BD")

    async def list_scheduled_flows(
        self,
        user_id: int
    ) -> List[UUID]:
        """
        Retorna lista de flow_id que actualmente tienen triggers programados.
        """
        triggers = await self.trigger_repo.list_by_owner(user_id)
        return [t.flow_id for t in triggers]

def get_trigger_orchestrator_service(
    def_service: FlowDefinitionService = Depends(get_flow_definition_service),
    cred_repo: CredentialRepository = Depends(get_credential_repository),
    flow_repo: FlowRepository = Depends(get_flow_repository),
    trigger_repo: TriggerRepository = Depends(get_trigger_repository),
    node_repo: NodeRepository = Depends(get_node_repository),
    action_repo: ActionRepository = Depends(get_action_repository),
    scheduler = Depends(get_scheduler),
) -> TriggerOrchestratorService:
    """
    Factory para inyectar TriggerOrchestratorService en FastAPI.
    """
    # 🔧 FIX: Incluir node_repo y action_repo para activación completa
    return TriggerOrchestratorService(def_service, cred_repo, flow_repo, trigger_repo, node_repo, action_repo, scheduler)

async def create_trigger_orchestrator_manual(db_session) -> TriggerOrchestratorService:
    """
    🔧 MANUAL CREATION: Crear TriggerOrchestratorService sin Depends para uso fuera de FastAPI
    """
    import logging
    logger = logging.getLogger(__name__)
    
    from app.repositories.credential_repository import CredentialRepository
    from app.repositories.trigger_repository import TriggerRepository
    from app.services.flow_definition_service import FlowDefinitionService
    from app.core.scheduler import get_scheduler
    from app.repositories.node_repository import NodeRepository
    from app.repositories.action_repository import ActionRepository
    
    # Crear repositorios manualmente
    from app.repositories.flow_definition_repository import FlowDefinitionRepository
    cred_repo = CredentialRepository(db_session)
    logger.info(f"🔧 MANUAL TRIGGER: Created cred_repo type: {type(cred_repo)}")
    flow_repo = FlowRepository(db_session)
    trigger_repo = TriggerRepository(db_session)
    node_repo = NodeRepository(db_session)  # 🔧 FIX: Agregar node_repo
    action_repo = ActionRepository(db_session)  # 🔧 FIX: Agregar action_repo
    def_repo = FlowDefinitionRepository(db_session)
    def_service = FlowDefinitionService(def_repo)
    scheduler = get_scheduler()
    
    orchestrator = TriggerOrchestratorService(def_service, cred_repo, flow_repo, trigger_repo, node_repo, action_repo, scheduler)
    logger.info(f"🔧 MANUAL TRIGGER: Created orchestrator.cred_repo type: {type(orchestrator.cred_repo)}")
    return orchestrator
