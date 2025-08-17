import time
from uuid import uuid4, UUID
from typing import Any, Dict
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.connectors.factory import register_node
from app.routers.webhook_router import register_webhook, unregister_webhook
from .connector_handler import ActionHandler
from .trigger_registry import register_trigger_capability


@register_node("Webhook.trigger")
@register_trigger_capability("webhook", "Webhook.trigger", unschedule_method="unregister")
class WebhookTriggerHandler(ActionHandler):
    """
    ✅ REFACTORIZADO: Handler completo para webhooks triggers
    
    Funcionalidades:
    1. Genera token único para webhook
    2. Registra webhook dinámico en router
    3. Retorna URLs de producción y test
    
    Parámetros esperados en params:
      • flow_id: UUID del flujo a ejecutar
      • user_id: ID del usuario
      • first_step: Dict con el primer paso del workflow
      • scheduler: AsyncIOScheduler instance (opcional)
      • creds: Credenciales del usuario
      • respond: Tipo de respuesta ("immediate", "delayed")
      • headers_to_forward: Lista de headers a reenviar
      • auth_type: Tipo de auth ("none", "token", "signature")
      • allowed_origins: Lista de orígenes permitidos
      • methods: Lista de métodos HTTP permitidos
    """

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start = time.perf_counter()
        
        # Validar parámetros requeridos
        flow_id = params.get("flow_id")
        user_id = params.get("user_id")
        first_step = params.get("first_step")
        scheduler = params.get("scheduler")
        creds = params.get("creds", {})
        
        if not flow_id:
            return {
                "status": "error",
                "error": "flow_id requerido",
                "duration_ms": int((time.perf_counter() - start) * 1000),
            }

        # Generar token único para el webhook
        token = uuid4().hex
        
        # Preparar trigger_args con configuración
        trigger_args = {
            "production_path": f"/api/webhooks/{token}",
            "test_path": f"/api/webhooks-test/{token}",
            "respond": params.get("respond", "immediate"),
            "headers_to_forward": params.get("headers_to_forward", []),
            "auth_type": params.get("auth_type", "none"),
            "allowed_origins": params.get("allowed_origins", []),
            "methods": params.get("methods", ["POST"]),
            "token": token
        }

        # Si es solo validación/preparación, retornar trigger_args
        if not scheduler or not user_id or not first_step:
            duration_ms = int((time.perf_counter() - start) * 1000)
            return {
                "status": "success",
                "output": {
                    "trigger_type": "webhook",
                    "trigger_args": trigger_args,
                    "webhook_url": trigger_args["production_path"],
                    "test_url": trigger_args["test_path"]
                },
                "duration_ms": duration_ms,
            }

        # ✅ NUEVA FUNCIONALIDAD: Registrar webhook real
        try:
            # Registrar webhook dinámico en el router
            webhook_id = register_webhook(
                flow_id=UUID(flow_id) if isinstance(flow_id, str) else flow_id,
                user_id=user_id,
                trigger_args=trigger_args
            )
            
            duration_ms = int((time.perf_counter() - start) * 1000)
            return {
                "status": "success",
                "output": {
                    "trigger_type": "webhook",
                    "webhook_id": webhook_id,
                    "registered": True,
                    "trigger_args": trigger_args,
                    "webhook_url": trigger_args["production_path"],
                    "test_url": trigger_args["test_path"],
                    "token": token
                },
                "duration_ms": duration_ms,
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error registrando webhook: {str(e)}",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
    
    async def unregister(self, webhook_id: str) -> Dict[str, Any]:
        """
        ✅ NUEVA: Funcionalidad para cancelar webhooks registrados
        """
        try:
            unregister_webhook(webhook_id)
            return {
                "status": "success",
                "message": f"Webhook {webhook_id} cancelado exitosamente"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error cancelando webhook {webhook_id}: {str(e)}"
            }