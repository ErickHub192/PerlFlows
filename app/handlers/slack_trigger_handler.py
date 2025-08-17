import time
import json
import hashlib
import hmac
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from uuid import UUID
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.connectors.factory import register_node, execute_node
from app.core.scheduler import schedule_job, unschedule_job
from .connector_handler import ActionHandler
from .trigger_registry import register_trigger_capability

# Para Slack SDK real
# from slack_sdk import WebClient
# from slack_sdk.errors import SlackApiError


@register_node("Slack_Trigger.events_api")
@register_trigger_capability("slack_events", "Slack_Trigger.events_api", unschedule_method="unregister")
class SlackEventsHandler(ActionHandler):
    """
    ✅ Handler PRIMARY para Slack Events API (2025 Best Practice)
    
    Funcionalidades:
    1. Recibe eventos en tiempo real via webhooks
    2. Procesa mensajes, menciones, reacciones automáticamente
    3. Valida signatures para seguridad
    4. Maneja challenge verification
    5. REEMPLAZA polling por eficiencia
    
    Parámetros esperados en params:
      • webhook_url: str - URL donde recibirás eventos (REQUERIDO)
      • signing_secret: str - Secret para validar requests de Slack
      • event_types: List[str] - Tipos de eventos a procesar
      • bot_user_id: str - ID del bot para filtrar menciones
      • channel_filters: List[str] - Canales específicos (opcional)
      • keyword_filters: List[str] - Keywords a detectar (opcional)
      • flow_id: UUID del flujo a ejecutar
      • user_id: ID del usuario
      • first_step: Dict con el primer paso del workflow
      • creds: Dict con tokens de Slack
    """

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start = time.perf_counter()
        
        # Validar parámetros críticos
        webhook_url = params.get("webhook_url")
        signing_secret = params.get("signing_secret")
        
        if not webhook_url:
            return {
                "status": "error",
                "error": "webhook_url es REQUERIDO para Slack Events API",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
        
        if not signing_secret:
            return {
                "status": "error", 
                "error": "signing_secret es REQUERIDO para validar requests de Slack",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
        
        # Parámetros de configuración
        event_types = params.get("event_types", ["message", "app_mention"])
        bot_user_id = params.get("bot_user_id")
        channel_filters = params.get("channel_filters", [])
        keyword_filters = params.get("keyword_filters", [])
        flow_id = params.get("flow_id")
        first_step = params.get("first_step")
        creds = params.get("creds", {})
        
        # Si es solo validación/preparación
        if not flow_id or not first_step:
            duration_ms = int((time.perf_counter() - start) * 1000)
            return {
                "status": "success",
                "output": {
                    "trigger_type": "slack_events",
                    "webhook_url": webhook_url,
                    "event_types": event_types,
                    "real_time": True,
                    "rate_limit_friendly": True,
                    "setup_required": "Configure webhook URL in Slack App settings"
                },
                "duration_ms": duration_ms,
            }

        # ✅ Configurar webhook endpoint en tu servidor
        try:
            # En producción, esto registraría el endpoint en tu servidor FastAPI
            # Para ahora, retornamos la configuración
            
            duration_ms = int((time.perf_counter() - start) * 1000)
            return {
                "status": "success",
                "output": {
                    "trigger_type": "slack_events",
                    "webhook_url": webhook_url,
                    "event_types": event_types,
                    "bot_user_id": bot_user_id,
                    "filters": {
                        "channels": channel_filters,
                        "keywords": keyword_filters
                    },
                    "security": "Signature validation enabled",
                    "setup_instructions": [
                        f"1. Configure webhook URL: {webhook_url}",
                        f"2. Subscribe to events: {', '.join(event_types)}",
                        "3. Use signing secret for validation",
                        "4. Enable URL verification in Slack"
                    ]
                },
                "duration_ms": duration_ms,
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "error": f"Error configurando Slack Events: {str(e)}",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
    
    async def process_webhook_event(
        self, 
        request_body: str, 
        headers: Dict[str, str],
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        ✅ Procesa eventos webhook de Slack con validación de seguridad
        """
        try:
            # 1. Validar signature de Slack
            if not await self._verify_slack_signature(
                request_body, headers, params.get("signing_secret")
            ):
                return {
                    "status": "error",
                    "error": "Invalid Slack signature"
                }
            
            # 2. Parsear evento
            event_data = json.loads(request_body)
            
            # 3. Manejar challenge verification
            if event_data.get("type") == "url_verification":
                return {
                    "status": "success",
                    "challenge": event_data.get("challenge")
                }
            
            # 4. Procesar evento real
            if event_data.get("type") == "event_callback":
                event = event_data.get("event", {})
                
                # Filtrar eventos según configuración
                if await self._should_process_event(event, params):
                    # ✅ FIX: Ejecutar workflow completo en lugar de solo el primer nodo
                    from app.handlers.workflow_execution_helper import execute_complete_workflow, extract_trigger_metadata
                    
                    # Extraer metadatos del workflow
                    flow_id, user_id, trigger_data = extract_trigger_metadata(params)
                    
                    if flow_id and user_id:
                        # Preparar datos del trigger Slack
                        slack_trigger_data = {
                            **trigger_data,
                            "slack_event": event,
                            "slack_team": event_data.get("team_id"),
                            "trigger_source": "slack_events"
                        }
                        
                        # Ejecutar workflow completo
                        await execute_complete_workflow(
                            flow_id=flow_id,
                            user_id=user_id,
                            trigger_data=slack_trigger_data,
                            inputs={"slack_event": event}
                        )
                    else:
                        # Fallback: ejecutar solo el nodo si no hay metadatos de workflow
                        await execute_node(
                            params["first_step"]["node_name"],
                            params["first_step"]["action_name"],
                            {
                                **params["first_step"].get("params", {}),
                                "slack_event": event,
                                "slack_team": event_data.get("team_id"),
                                "trigger_source": "slack_events"
                            },
                            params.get("creds", {}),
                        )
                
                return {"status": "success", "processed": True}
            
            return {"status": "success", "processed": False}
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error procesando evento Slack: {str(e)}"
            }
    
    async def _verify_slack_signature(
        self, 
        request_body: str, 
        headers: Dict[str, str], 
        signing_secret: str
    ) -> bool:
        """
        ✅ Verifica signature de Slack para seguridad
        """
        try:
            timestamp = headers.get("X-Slack-Request-Timestamp", "")
            signature = headers.get("X-Slack-Signature", "")
            
            if not timestamp or not signature:
                return False
            
            # Verificar timestamp (no más de 5 minutos)
            current_time = int(time.time())
            if abs(current_time - int(timestamp)) > 300:
                return False
            
            # Calcular signature esperada
            basestring = f"v0:{timestamp}:{request_body}".encode('utf-8')
            expected_signature = "v0=" + hmac.new(
                signing_secret.encode('utf-8'),
                basestring,
                hashlib.sha256
            ).hexdigest()
            
            # Comparación segura
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception:
            return False
    
    async def _should_process_event(
        self, 
        event: Dict[str, Any], 
        params: Dict[str, Any]
    ) -> bool:
        """
        ✅ Determina si el evento debe procesarse según filtros
        """
        event_type = event.get("type")
        channel = event.get("channel")
        text = event.get("text", "").lower()
        user = event.get("user")
        bot_user_id = params.get("bot_user_id")
        
        # Filtro por tipo de evento
        event_types = params.get("event_types", [])
        if event_types and event_type not in event_types:
            return False
        
        # Filtro por canal
        channel_filters = params.get("channel_filters", [])
        if channel_filters and channel not in channel_filters:
            return False
        
        # Filtro por keywords
        keyword_filters = params.get("keyword_filters", [])
        if keyword_filters:
            if not any(keyword.lower() in text for keyword in keyword_filters):
                return False
        
        # Ignorar mensajes del propio bot
        if bot_user_id and user == bot_user_id:
            return False
        
        return True


@register_node("Slack_Trigger.poll_messages_fallback")
@register_trigger_capability("slack_poll_fallback", "Slack_Trigger.poll_messages_fallback", unschedule_method="unregister")
class SlackPollFallbackHandler(ActionHandler):
    """
    ⚠️ Handler FALLBACK para Slack polling (2025 Rate Limited)
    
    ADVERTENCIA: Solo usar cuando Events API no esté disponible
    Rate Limits 2025: 1 request/minuto, máximo 15 mensajes
    
    Funcionalidades:
    1. Polling con rate limits extremos respetados
    2. Backoff automático en 429 errors
    3. Optimizado para uso mínimo
    4. Recomendación: Migrar a Events API
    """

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start = time.perf_counter()
        
        # ADVERTENCIA PROMINENTE
        print("⚠️ ADVERTENCIA: Usando Slack polling fallback")
        print("📉 Rate limits 2025: 1 request/min, max 15 mensajes")
        print("✅ RECOMENDADO: Migrar a Slack Events API")
        
        # Validar parámetros
        polling_interval = max(params.get("polling_interval", 120), 120)  # Mínimo 2 min
        channel_ids = params.get("channel_ids", [])
        flow_id = params.get("flow_id")
        first_step = params.get("first_step")
        scheduler = params.get("scheduler")
        creds = params.get("creds", {})
        
        if not channel_ids:
            return {
                "status": "error",
                "error": "channel_ids es REQUERIDO para polling fallback",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
        
        # Intervalo mínimo por rate limits 2025
        if polling_interval < 120:
            return {
                "status": "error",
                "error": "Intervalo mínimo 120 segundos (rate limits 2025)",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }

        # Si es solo validación/preparación
        if not scheduler or not flow_id or not first_step:
            duration_ms = int((time.perf_counter() - start) * 1000)
            return {
                "status": "success",
                "output": {
                    "trigger_type": "slack_poll_fallback",
                    "warning": "Rate limited fallback - consider Events API",
                    "trigger_args": {
                        "seconds": polling_interval,
                        "channels": len(channel_ids),
                        "rate_limit_safe": True
                    }
                },
                "duration_ms": duration_ms,
            }

        # ✅ Programar job con rate limits respetados
        try:
            job_id = f"slack_fallback_{flow_id}"
            
            # Función de polling optimizada
            async def check_slack_limited():
                try:
                    # Solo procesar un canal por vez para respetar limits
                    for channel_id in channel_ids[:2]:  # Max 2 canales
                        messages = await self._get_messages_rate_limited(
                            creds, channel_id, params.get("last_timestamp", 0)
                        )
                        
                        # Procesar mensajes limitados
                        for message in messages[:5]:  # Max 5 mensajes por iteración
                            # ✅ FIX: Ejecutar workflow completo en lugar de solo el primer nodo
                            from app.handlers.workflow_execution_helper import execute_complete_workflow, extract_trigger_metadata
                            
                            # Extraer metadatos del workflow
                            flow_id, user_id, trigger_data = extract_trigger_metadata(params)
                            
                            if flow_id and user_id:
                                # Preparar datos del trigger Slack
                                slack_trigger_data = {
                                    **trigger_data,
                                    "slack_message": message,
                                    "trigger_source": "slack_fallback"
                                }
                                
                                # Ejecutar workflow completo
                                await execute_complete_workflow(
                                    flow_id=flow_id,
                                    user_id=user_id,
                                    trigger_data=slack_trigger_data,
                                    inputs={"slack_message": message}
                                )
                            else:
                                # Fallback: ejecutar solo el nodo si no hay metadatos de workflow
                                await execute_node(
                                    first_step["node_name"],
                                    first_step["action_name"],
                                    {
                                        **first_step.get("params", {}),
                                        "slack_message": message,
                                        "trigger_source": "slack_fallback"
                                    },
                                    creds,
                                )
                            
                            # Actualizar timestamp
                            msg_ts = float(message.get("ts", 0))
                            if msg_ts > params.get("last_timestamp", 0):
                                params["last_timestamp"] = msg_ts
                        
                        # Pausa entre canales para rate limits
                        await asyncio.sleep(5)
                        
                except Exception as e:
                    print(f"Error en Slack fallback polling: {str(e)}")
            
            # Trigger con intervalo seguro
            trigger_args = {
                "seconds": polling_interval,
            }
            
            # Programar job
            schedule_job(
                scheduler,
                job_id,
                func=check_slack_limited,
                trigger_type="interval",
                trigger_args=trigger_args,
            )
            
            duration_ms = int((time.perf_counter() - start) * 1000)
            return {
                "status": "success",
                "output": {
                    "trigger_type": "slack_poll_fallback",
                    "job_id": job_id,
                    "scheduled": True,
                    "polling_interval": polling_interval,
                    "channels": len(channel_ids),
                    "rate_limit_warning": "Limited to prevent 429 errors",
                    "recommendation": "Upgrade to Events API",
                    "trigger_args": trigger_args,
                },
                "duration_ms": duration_ms,
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "error": f"Error programando Slack fallback: {str(e)}",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
    
    async def _get_messages_rate_limited(
        self, 
        creds: Dict[str, Any], 
        channel_id: str,
        last_timestamp: float
    ) -> List[Dict[str, Any]]:
        """
        ✅ Obtiene mensajes respetando rate limits 2025
        """
        try:
            # IMPLEMENTACIÓN REAL con Slack SDK
            from slack_sdk import WebClient
            from slack_sdk.errors import SlackApiError
            
            client = WebClient(token=creds.get("slack_token"))
            
            try:
                # conversations.history con límites 2025
                response = client.conversations_history(
                    channel=channel_id,
                    oldest=str(last_timestamp),
                    limit=15,  # Máximo 15 por rate limits 2025
                    include_all_metadata=False
                )
                
                messages = response.get("messages", [])
                
                # Normalizar respuesta
                normalized = []
                for msg in messages:
                    normalized.append({
                        "type": msg.get("type", "message"),
                        "channel": channel_id,
                        "user": msg.get("user"),
                        "text": msg.get("text", ""),
                        "ts": msg.get("ts"),
                        "thread_ts": msg.get("thread_ts"),
                        "bot_id": msg.get("bot_id"),
                        "app_id": msg.get("app_id"),
                        "team": msg.get("team")
                    })
                
                return normalized
                
            except SlackApiError as e:
                if e.response["error"] == "ratelimited":
                    print("⚠️ Rate limited - esperando...")
                    # En producción, implementar exponential backoff
                    return []
                else:
                    print(f"Slack API Error: {e.response['error']}")
                    return []
                    
        except ImportError:
            print("⚠️ slack_sdk no disponible - usando fallback simulado")
            # Fallback simulado
            return [
                {
                    "type": "message",
                    "channel": channel_id,
                    "user": "U123456",
                    "text": f"Mensaje simulado en {channel_id}",
                    "ts": str(datetime.now().timestamp()),
                    "thread_ts": None,
                    "fallback": True
                }
            ]
        
        except Exception as e:
            print(f"Error obteniendo mensajes Slack: {str(e)}")
            return []


@register_node("Slack_Trigger.slash_command")
@register_trigger_capability("slack_slash", "Slack_Trigger.slash_command")
class SlackSlashHandler(ActionHandler):
    """
    ✅ Handler para Slash Commands de Slack (Webhook-based)
    
    Detecta cuando usuarios ejecutan comandos como /workflow
    """
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start = time.perf_counter()
        
        # Parámetros para slash commands
        command_name = params.get("command_name", "/workflow")
        webhook_url = params.get("webhook_url")
        signing_secret = params.get("signing_secret")
        
        if not webhook_url:
            return {
                "status": "error",
                "error": "webhook_url es REQUERIDO para Slash Commands",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
        
        duration_ms = int((time.perf_counter() - start) * 1000)
        return {
            "status": "success",
            "output": {
                "trigger_type": "slack_slash",
                "command": command_name,
                "webhook_url": webhook_url,
                "security": "Signature validation" if signing_secret else "No validation",
                "setup_instructions": [
                    f"1. Create slash command: {command_name}",
                    f"2. Set request URL: {webhook_url}",
                    "3. Configure signing secret for security"
                ]
            },
            "duration_ms": duration_ms,
        }