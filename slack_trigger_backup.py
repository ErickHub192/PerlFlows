import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from uuid import UUID
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.connectors.factory import register_node, execute_node
from app.core.scheduler import schedule_job, unschedule_job
from .connector_handler import ActionHandler
from .trigger_registry import register_trigger_capability

# Para importar cuando necesites usar Slack SDK
# from slack_sdk import WebClient
# from slack_sdk.errors import SlackApiError


@register_node("Slack_Trigger.poll_messages")
@register_trigger_capability("slack_poll", "Slack_Trigger.poll_messages")
class SlackPollHandler(ActionHandler):
    """
    ✅ Handler para trigger de Slack con polling
    
    Funcionalidades:
    1. Monitorea mensajes nuevos en canales específicos
    2. Detecta menciones, mensajes directos o keywords
    3. Puede filtrar por usuario, canal o contenido
    4. Ejecuta workflow cuando encuentra mensajes relevantes
    
    Parámetros esperados en params:
      • polling_interval: int - Intervalo en segundos (mínimo 60)
      • channel_ids: List[str] - IDs de canales a monitorear
      • keywords: List[str] - Palabras clave a buscar (opcional)
      • user_ids: List[str] - IDs de usuarios específicos (opcional)
      • include_mentions: bool - Incluir cuando mencionan al bot
      • flow_id: UUID del flujo a ejecutar
      • user_id: ID del usuario
      • first_step: Dict con el primer paso del workflow
      • scheduler: AsyncIOScheduler instance
      • creds: Dict con token de Slack
      • last_timestamp: float - Timestamp del último mensaje procesado
    """

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start = time.perf_counter()
        
        # Validar parámetros
        polling_interval = params.get("polling_interval", 60)  # Default 1 min
        channel_ids = params.get("channel_ids", [])
        keywords = params.get("keywords", [])
        user_ids = params.get("user_ids", [])
        include_mentions = params.get("include_mentions", True)
        flow_id = params.get("flow_id")
        user_id = params.get("user_id")
        first_step = params.get("first_step")
        scheduler = params.get("scheduler")
        creds = params.get("creds", {})
        last_timestamp = params.get("last_timestamp", 0)
        
        if not channel_ids and not include_mentions:
            return {
                "status": "error",
                "error": "Debe especificar channel_ids o activar include_mentions",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
        
        # Validación de intervalo
        if polling_interval < 30:
            return {
                "status": "error",
                "error": "El intervalo mínimo de polling es 30 segundos para Slack",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }

        # Si es solo validación/preparación
        if not scheduler or not flow_id or not first_step:
            duration_ms = int((time.perf_counter() - start) * 1000)
            return {
                "status": "success",
                "output": {
                    "trigger_type": "slack_poll",
                    "trigger_args": {
                        "interval": polling_interval,
                        "channel_ids": channel_ids,
                        "keywords": keywords,
                        "include_mentions": include_mentions
                    }
                },
                "duration_ms": duration_ms,
            }

        # ✅ Programar job real con polling
        try:
            job_id = f"slack_{flow_id}"
            
            # Función que ejecutará el polling
            async def check_slack():
                try:
                    # Obtener mensajes nuevos
                    new_messages = await self._get_new_messages(
                        creds,
                        channel_ids,
                        params.get("last_timestamp", 0),
                        include_mentions
                    )
                    
                    # Filtrar mensajes según criterios
                    filtered_messages = await self._filter_messages(
                        new_messages, keywords, user_ids
                    )
                    
                    # Ejecutar workflow para cada mensaje
                    for message in filtered_messages:
                        await execute_node(
                            first_step["node_name"],
                            first_step["action_name"],
                            {
                                **first_step.get("params", {}),
                                "slack_message": message,
                                "trigger_source": "slack"
                            },
                            creds,
                        )
                        
                        # Actualizar timestamp
                        msg_ts = float(message.get("ts", 0))
                        if msg_ts > params.get("last_timestamp", 0):
                            params["last_timestamp"] = msg_ts
                        
                except Exception as e:
                    print(f"Error en Slack polling: {str(e)}")
            
            # Si no hay timestamp, usar tiempo actual menos 1 hora
            if not last_timestamp:
                params["last_timestamp"] = (
                    datetime.now() - timedelta(hours=1)
                ).timestamp()
            
            # Crear trigger con intervalo
            trigger_args = {
                "trigger": "interval",
                "seconds": polling_interval,
            }
            
            # Programar job
            schedule_job(
                scheduler,
                job_id,
                func=check_slack,
                trigger_type="interval",
                trigger_args=trigger_args,
            )
            
            duration_ms = int((time.perf_counter() - start) * 1000)
            return {
                "status": "success",
                "output": {
                    "trigger_type": "slack_poll",
                    "job_id": job_id,
                    "scheduled": True,
                    "polling_interval": polling_interval,
                    "channels": channel_ids,
                    "trigger_args": trigger_args,
                },
                "duration_ms": duration_ms,
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "error": f"Error programando Slack polling: {str(e)}",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
    
    async def _get_new_messages(
        self, 
        creds: Dict[str, Any], 
        channel_ids: List[str],
        last_timestamp: float,
        include_mentions: bool
    ) -> List[Dict[str, Any]]:
        """
        ✅ Obtiene mensajes nuevos de Slack
        """
        # En producción:
        # client = WebClient(token=creds.get("slack_token"))
        # messages = []
        # 
        # for channel_id in channel_ids:
        #     response = client.conversations_history(
        #         channel=channel_id,
        #         oldest=str(last_timestamp),
        #         limit=100
        #     )
        #     messages.extend(response["messages"])
        # 
        # if include_mentions:
        #     # Obtener mensajes donde se menciona al bot
        #     ...
        
        # Simulación
        return [
            {
                "type": "message",
                "channel": "C123456",
                "user": "U123456",
                "text": "Hola @bot, necesito ayuda con el reporte",
                "ts": str(datetime.now().timestamp()),
                "thread_ts": None,
                "mentions": ["bot"],
                "channel_name": "general"
            }
        ]
    
    async def _filter_messages(
        self,
        messages: List[Dict[str, Any]],
        keywords: List[str],
        user_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        ✅ Filtra mensajes según criterios
        """
        filtered = []
        
        for message in messages:
            # Filtrar por usuario si se especifica
            if user_ids and message.get("user") not in user_ids:
                continue
            
            # Filtrar por keywords si se especifican
            if keywords:
                text = message.get("text", "").lower()
                if not any(keyword.lower() in text for keyword in keywords):
                    continue
            
            filtered.append(message)
        
        return filtered
    
    async def unschedule(self, scheduler: AsyncIOScheduler, job_id: str) -> Dict[str, Any]:
        """
        ✅ Cancelar job de polling
        """
        try:
            unschedule_job(scheduler, job_id)
            return {
                "status": "success",
                "message": f"Slack polling job {job_id} cancelado exitosamente"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error cancelando job {job_id}: {str(e)}"
            }


@register_node("Slack_Trigger.event_subscription")
@register_trigger_capability("slack_events", "Slack_Trigger.event_subscription")
class SlackEventHandler(ActionHandler):
    """
    ✅ Handler para Slack Events API (más eficiente que polling)
    
    Nota: Requiere configurar webhook endpoint en Slack App
    """
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start = time.perf_counter()
        
        # Parámetros para eventos
        event_types = params.get("event_types", ["message"])
        webhook_url = params.get("webhook_url")
        
        if not webhook_url:
            return {
                "status": "error",
                "error": "Se requiere webhook_url para Slack Events",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
        
        # En producción, esto registraría el webhook en tu servidor
        # para recibir eventos de Slack en tiempo real
        
        duration_ms = int((time.perf_counter() - start) * 1000)
        return {
            "status": "success",
            "output": {
                "trigger_type": "slack_events",
                "event_types": event_types,
                "webhook_url": webhook_url,
                "message": "Slack Events configurado (simulado)"
            },
            "duration_ms": duration_ms,
        }


@register_node("Slack_Trigger.slash_command")
@register_trigger_capability("slack_slash", "Slack_Trigger.slash_command")
class SlackSlashHandler(ActionHandler):
    """
    ✅ Handler para Slash Commands de Slack
    
    Detecta cuando usuarios ejecutan comandos como /workflow
    """
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start = time.perf_counter()
        
        # Parámetros para slash commands
        command_name = params.get("command_name", "/workflow")
        webhook_url = params.get("webhook_url")
        
        if not webhook_url:
            return {
                "status": "error",
                "error": "Se requiere webhook_url para Slash Commands",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
        
        duration_ms = int((time.perf_counter() - start) * 1000)
        return {
            "status": "success",
            "output": {
                "trigger_type": "slack_slash",
                "command": command_name,
                "webhook_url": webhook_url,
                "message": "Slash Command configurado (simulado)"
            },
            "duration_ms": duration_ms,
        }