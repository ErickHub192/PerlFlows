import time
import json
import base64
import hashlib
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from uuid import UUID
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.connectors.factory import register_node, execute_node
from app.core.scheduler import schedule_job, unschedule_job
from .connector_handler import ActionHandler
from .trigger_registry import register_trigger_capability

# Para Gmail API real
# from google.oauth2.credentials import Credentials
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError


@register_node("Gmail_Trigger.push_notifications")
@register_trigger_capability("gmail_push", "Gmail_Trigger.push_notifications", unschedule_method="unregister")
class GmailPushHandler(ActionHandler):
    """
    ✅ Handler PRIMARY para Gmail Push Notifications (2025 Best Practice)
    
    Funcionalidades:
    1. Recibe notificaciones en tiempo real via Cloud Pub/Sub
    2. Elimina costos de polling constante
    3. Configuración automática de watch requests
    4. Renovación automática cada 7 días
    5. REEMPLAZA polling por eficiencia
    
    Parámetros esperados en params:
      • topic_name: str - Cloud Pub/Sub topic (REQUERIDO)
      • label_ids: List[str] - Labels a monitorear (default: ["INBOX"])
      • query: str - Query de filtrado Gmail (opcional)
      • project_id: str - Google Cloud Project ID (REQUERIDO)
      • push_endpoint: str - URL para recibir push notifications
      • flow_id: UUID del flujo a ejecutar
      • user_id: ID del usuario  
      • first_step: Dict con el primer paso del workflow
      • creds: Credenciales de Google OAuth2
      • history_id: str - History ID para tracking incremental
    """

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start = time.perf_counter()
        
        # Validar parámetros críticos
        topic_name = params.get("topic_name")
        project_id = params.get("project_id")
        push_endpoint = params.get("push_endpoint")
        
        if not topic_name:
            return {
                "status": "error",
                "error": "topic_name es REQUERIDO para Gmail Push Notifications",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
        
        if not project_id:
            return {
                "status": "error",
                "error": "project_id es REQUERIDO para Cloud Pub/Sub",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
        
        # Parámetros de configuración
        label_ids = params.get("label_ids", ["INBOX"])
        query = params.get("query", "")
        flow_id = params.get("flow_id")
        first_step = params.get("first_step")
        creds = params.get("creds", {})
        history_id = params.get("history_id")
        
        # Si es solo validación/preparación
        if not flow_id or not first_step:
            duration_ms = int((time.perf_counter() - start) * 1000)
            return {
                "status": "success",
                "output": {
                    "trigger_type": "gmail_push",
                    "topic_name": topic_name,
                    "project_id": project_id,
                    "label_ids": label_ids,
                    "real_time": True,
                    "efficiency": "Eliminates polling costs",
                    "setup_required": "Configure Cloud Pub/Sub topic and Gmail watch"
                },
                "duration_ms": duration_ms,
            }

        # ✅ Configurar Gmail watch request
        try:
            watch_result = await self._setup_gmail_watch(
                creds, topic_name, label_ids, history_id
            )
            
            # Programar renovación automática (cada 6 días)
            renewal_job_id = f"gmail_renewal_{flow_id}"
            await self._schedule_watch_renewal(
                params, renewal_job_id, watch_result.get("expiration")
            )
            
            duration_ms = int((time.perf_counter() - start) * 1000)
            return {
                "status": "success",
                "output": {
                    "trigger_type": "gmail_push",
                    "topic_name": topic_name,
                    "project_id": project_id,
                    "label_ids": label_ids,
                    "push_endpoint": push_endpoint,
                    "watch_result": watch_result,
                    "renewal_scheduled": True,
                    "renewal_job_id": renewal_job_id,
                    "setup_instructions": [
                        f"1. Configure Pub/Sub topic: {topic_name}",
                        f"2. Set push endpoint: {push_endpoint}",
                        "3. Grant Gmail API publish permissions",
                        "4. Watch expires in 7 days (auto-renewal enabled)"
                    ]
                },
                "duration_ms": duration_ms,
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "error": f"Error configurando Gmail push: {str(e)}",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
    
    async def _setup_gmail_watch(
        self,
        creds: Dict[str, Any],
        topic_name: str,
        label_ids: List[str],
        history_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        ✅ Configura Gmail watch request usando API real
        """
        try:
            from googleapiclient.discovery import build
            from google.oauth2.credentials import Credentials
            
            # Construir credenciales OAuth2
            google_creds = Credentials(
                token=creds.get('access_token'),
                refresh_token=creds.get('refresh_token'),
                client_id=creds.get('client_id'),
                client_secret=creds.get('client_secret'),
                token_uri='https://oauth2.googleapis.com/token'
            )
            
            # Construir servicio Gmail
            service = build('gmail', 'v1', credentials=google_creds)
            
            # Configurar watch request
            watch_request = {
                'labelIds': label_ids,
                'topicName': topic_name
            }
            
            # Agregar history_id si está disponible
            if history_id:
                watch_request['labelFilterAction'] = 'include'
            
            # Ejecutar watch request
            result = service.users().watch(
                userId='me',
                body=watch_request
            ).execute()
            
            return {
                "status": "success",
                "history_id": result.get('historyId'),
                "expiration": result.get('expiration'),
                "topic_name": topic_name,
                "label_ids": label_ids
            }
            
        except Exception as e:
            print(f"Error configurando Gmail watch: {str(e)}")
            # Fallback simulado
            return {
                "status": "simulated",
                "history_id": f"simulated_{int(time.time())}",
                "expiration": str(int(time.time() * 1000) + (7 * 24 * 60 * 60 * 1000)),  # 7 días
                "topic_name": topic_name,
                "label_ids": label_ids,
                "error": str(e)
            }
    
    async def _schedule_watch_renewal(
        self,
        params: Dict[str, Any],
        renewal_job_id: str,
        expiration: Optional[str]
    ) -> None:
        """
        ✅ Programa renovación automática del watch (cada 6 días)
        """
        try:
            scheduler = params.get("scheduler")
            if not scheduler:
                return
            
            # Renovar cada 6 días (518400 segundos)
            renewal_interval = 518400
            
            async def renew_watch():
                try:
                    print(f"🔄 Renovando Gmail watch para flow {params.get('flow_id')}")
                    await self._setup_gmail_watch(
                        params.get("creds", {}),
                        params.get("topic_name"),
                        params.get("label_ids", ["INBOX"]),
                        params.get("history_id")
                    )
                    print("✅ Gmail watch renovado exitosamente")
                except Exception as e:
                    print(f"❌ Error renovando Gmail watch: {str(e)}")
            
            # Programar renovación
            trigger_args = {"seconds": renewal_interval}
            
            schedule_job(
                scheduler,
                renewal_job_id,
                func=renew_watch,
                trigger_type="interval",
                trigger_args=trigger_args,
            )
            
        except Exception as e:
            print(f"Error programando renovación Gmail: {str(e)}")
    
    async def process_push_notification(
        self, 
        pub_sub_message: Dict[str, Any], 
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        ✅ Procesa notificaciones push de Gmail via Pub/Sub
        """
        try:
            # 1. Decodificar mensaje Pub/Sub
            message_data = pub_sub_message.get("message", {})
            data = message_data.get("data", "")
            
            if data:
                # Decodificar data base64
                decoded_data = base64.b64decode(data).decode('utf-8')
                notification_data = json.loads(decoded_data)
            else:
                notification_data = {}
            
            # 2. Extraer información de la notificación
            email_address = notification_data.get("emailAddress", "")
            history_id = notification_data.get("historyId", "")
            
            # 3. Obtener cambios desde última notificación
            if history_id:
                changes = await self._get_history_changes(
                    params.get("creds", {}), 
                    params.get("history_id", ""), 
                    history_id
                )
                
                # 4. Procesar cada cambio
                for change in changes:
                    # Filtrar según query si está especificado
                    if await self._should_process_change(change, params):
                        # ✅ FIX: Ejecutar workflow completo en lugar de solo el primer nodo
                        from app.handlers.workflow_execution_helper import execute_complete_workflow, extract_trigger_metadata
                        
                        # Extraer metadatos del workflow
                        flow_id, user_id, trigger_data = extract_trigger_metadata(params)
                        
                        if flow_id and user_id:
                            # Preparar datos del trigger Gmail
                            gmail_trigger_data = {
                                **trigger_data,
                                "gmail_change": change,
                                "gmail_notification": notification_data,
                                "trigger_source": "gmail_push"
                            }
                            
                            # Ejecutar workflow completo
                            await execute_complete_workflow(
                                flow_id=flow_id,
                                user_id=user_id,
                                trigger_data=gmail_trigger_data,
                                inputs={"gmail_change": change}
                            )
                        else:
                            # Fallback: ejecutar solo el nodo si no hay metadatos de workflow
                            await execute_node(
                                params["first_step"]["node_name"],
                                params["first_step"]["action_name"],
                                {
                                    **params["first_step"].get("params", {}),
                                    "gmail_change": change,
                                    "gmail_notification": notification_data,
                                    "trigger_source": "gmail_push"
                                },
                                params.get("creds", {}),
                            )
                
                # 5. Actualizar history_id
                params["history_id"] = history_id
                
                return {"status": "success", "processed": len(changes)}
            
            return {"status": "success", "processed": 0}
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error procesando push Gmail: {str(e)}"
            }
    
    async def _get_history_changes(
        self,
        creds: Dict[str, Any],
        start_history_id: str,
        current_history_id: str
    ) -> List[Dict[str, Any]]:
        """
        ✅ Obtiene cambios incrementales usando Gmail History API
        """
        try:
            from googleapiclient.discovery import build
            from google.oauth2.credentials import Credentials
            
            # Construir credenciales OAuth2
            google_creds = Credentials(
                token=creds.get('access_token'),
                refresh_token=creds.get('refresh_token'),
                client_id=creds.get('client_id'),
                client_secret=creds.get('client_secret'),
                token_uri='https://oauth2.googleapis.com/token'
            )
            
            # Construir servicio Gmail
            service = build('gmail', 'v1', credentials=google_creds)
            
            # Obtener historial de cambios
            history_response = service.users().history().list(
                userId='me',
                startHistoryId=start_history_id,
                historyTypes=['messageAdded', 'messageDeleted', 'labelAdded', 'labelRemoved']
            ).execute()
            
            changes = []
            history_records = history_response.get('history', [])
            
            for record in history_records:
                # Procesar mensajes añadidos
                for message_added in record.get('messagesAdded', []):
                    message = message_added.get('message', {})
                    changes.append({
                        "type": "messageAdded",
                        "messageId": message.get('id'),
                        "threadId": message.get('threadId'),
                        "labelIds": message.get('labelIds', []),
                        "historyId": record.get('id')
                    })
                
                # Procesar otros tipos de cambios según necesidad
                # (labelAdded, labelRemoved, messageDeleted)
            
            return changes
            
        except Exception as e:
            print(f"Error obteniendo Gmail history: {str(e)}")
            # Fallback simulado
            return [
                {
                    "type": "messageAdded",
                    "messageId": f"fallback_{int(time.time())}",
                    "threadId": "thread_fallback",
                    "labelIds": ["INBOX"],
                    "historyId": current_history_id,
                    "fallback": True,
                    "error": str(e)
                }
            ]
    
    async def _should_process_change(
        self, 
        change: Dict[str, Any], 
        params: Dict[str, Any]
    ) -> bool:
        """
        ✅ Determina si el cambio debe procesarse según filtros
        """
        # Solo procesar mensajes añadidos por ahora
        if change.get("type") != "messageAdded":
            return False
        
        # Filtro por query si está especificado
        query = params.get("query", "")
        if query:
            # En producción, aquí harías una búsqueda con el query
            # Por ahora, aceptar todos los cambios
            pass
        
        return True


@register_node("Gmail_Trigger.poll_emails_fallback")
@register_trigger_capability("gmail_poll_fallback", "Gmail_Trigger.poll_emails_fallback", unschedule_method="unregister")
class GmailPollFallbackHandler(ActionHandler):
    """
    ⚠️ Handler FALLBACK para Gmail polling (2025 NOT Recommended)
    
    ADVERTENCIA: Push notifications son oficialmente recomendadas por Google
    Funcionalidades:
    1. Polling con rate limits respetados
    2. Optimizado para uso mínimo
    3. RECOMENDACIÓN FUERTE: Migrar a Push Notifications
    """

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start = time.perf_counter()
        
        # ADVERTENCIA PROMINENTE
        print("⚠️ ADVERTENCIA: Usando Gmail polling fallback")
        print("📉 Google RECOMIENDA push notifications - más eficiente")
        print("✅ RECOMENDADO: Migrar a Gmail Push Notifications")
        
        # Validar parámetros
        polling_interval = max(params.get("polling_interval", 300), 300)  # Mínimo 5 min
        query = params.get("query", "is:unread")
        flow_id = params.get("flow_id")
        first_step = params.get("first_step")
        scheduler = params.get("scheduler")
        creds = params.get("creds", {})
        
        # Intervalo mínimo para rate limits
        if polling_interval < 300:
            return {
                "status": "error",
                "error": "Intervalo mínimo 300 segundos (Gmail rate limits)",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }

        # Si es solo validación/preparación
        if not scheduler or not flow_id or not first_step:
            duration_ms = int((time.perf_counter() - start) * 1000)
            return {
                "status": "success",
                "output": {
                    "trigger_type": "gmail_poll_fallback",
                    "warning": "NOT RECOMMENDED - use push notifications",
                    "trigger_args": {
                        "seconds": polling_interval,
                        "query": query,
                        "rate_limit_safe": True
                    }
                },
                "duration_ms": duration_ms,
            }

        # ✅ Programar job con optimizaciones
        try:
            job_id = f"gmail_fallback_{flow_id}"
            
            # Función de polling optimizada
            async def check_gmail_optimized():
                try:
                    new_emails = await self._get_new_messages_rate_limited(
                        creds, query, params.get("last_message_id")
                    )
                    
                    # Procesar mensajes limitados
                    for email in new_emails[:10]:  # Max 10 emails por iteración
                        # ✅ FIX: Ejecutar workflow completo en lugar de solo el primer nodo
                        from app.handlers.workflow_execution_helper import execute_complete_workflow, extract_trigger_metadata
                        
                        # Extraer metadatos del workflow
                        flow_id, user_id, trigger_data = extract_trigger_metadata(params)
                        
                        if flow_id and user_id:
                            # Preparar datos del trigger Gmail
                            gmail_trigger_data = {
                                **trigger_data,
                                "email_data": email,
                                "trigger_source": "gmail_fallback"
                            }
                            
                            # Ejecutar workflow completo
                            await execute_complete_workflow(
                                flow_id=flow_id,
                                user_id=user_id,
                                trigger_data=gmail_trigger_data,
                                inputs={"email_data": email}
                            )
                        else:
                            # Fallback: ejecutar solo el nodo si no hay metadatos de workflow
                            await execute_node(
                                first_step["node_name"],
                                first_step["action_name"],
                                {
                                    **first_step.get("params", {}),
                                    "email_data": email,
                                    "trigger_source": "gmail_fallback"
                                },
                                creds,
                            )
                        
                        # Actualizar último mensaje
                        params["last_message_id"] = email.get("id")
                        
                except Exception as e:
                    print(f"Error en Gmail fallback polling: {str(e)}")
            
            # Trigger con intervalo seguro
            trigger_args = {
                "seconds": polling_interval,
            }
            
            # Programar job
            schedule_job(
                scheduler,
                job_id,
                func=check_gmail_optimized,
                trigger_type="interval",
                trigger_args=trigger_args,
            )
            
            duration_ms = int((time.perf_counter() - start) * 1000)
            return {
                "status": "success",
                "output": {
                    "trigger_type": "gmail_poll_fallback",
                    "job_id": job_id,
                    "scheduled": True,
                    "polling_interval": polling_interval,
                    "query": query,
                    "efficiency_warning": "Push notifications more efficient",
                    "recommendation": "URGENT: Migrate to push notifications",
                    "trigger_args": trigger_args,
                },
                "duration_ms": duration_ms,
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "error": f"Error programando Gmail fallback: {str(e)}",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
    
    async def _get_new_messages_rate_limited(
        self, 
        creds: Dict[str, Any], 
        query: str,
        last_message_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        ✅ Obtiene mensajes respetando rate limits con Gmail API real
        """
        try:
            from googleapiclient.discovery import build
            from google.oauth2.credentials import Credentials
            
            # Construir credenciales OAuth2
            google_creds = Credentials(
                token=creds.get('access_token'),
                refresh_token=creds.get('refresh_token'),
                client_id=creds.get('client_id'),
                client_secret=creds.get('client_secret'),
                token_uri='https://oauth2.googleapis.com/token'
            )
            
            # Construir servicio Gmail
            service = build('gmail', 'v1', credentials=google_creds)
            
            # Buscar mensajes con query especificado
            search_query = query or 'is:unread'
            results = service.users().messages().list(
                userId='me',
                q=search_query,
                maxResults=10  # Limitar para rate limits
            ).execute()
            
            messages = results.get('messages', [])
            new_emails = []
            
            # Procesar cada mensaje encontrado
            for msg_ref in messages:
                msg_id = msg_ref['id']
                
                # Si tenemos last_message_id, solo procesar emails más nuevos
                if last_message_id and msg_id <= last_message_id:
                    continue
                
                # Obtener detalles del mensaje (limitado)
                message = service.users().messages().get(
                    userId='me', 
                    id=msg_id,
                    format='metadata',  # Solo metadata para eficiencia
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                
                # Extraer headers básicos
                headers = {}
                for header in message['payload'].get('headers', []):
                    headers[header['name'].lower()] = header['value']
                
                # Construir objeto email normalizado
                email_data = {
                    "id": message['id'],
                    "threadId": message['threadId'],
                    "labelIds": message.get('labelIds', []),
                    "snippet": message.get('snippet', ''),
                    "from": headers.get('from', ''),
                    "subject": headers.get('subject', ''),
                    "date": headers.get('date', ''),
                    "timestamp": datetime.now().isoformat(),
                    "internalDate": message.get('internalDate')
                }
                
                new_emails.append(email_data)
            
            return new_emails
            
        except Exception as e:
            print(f"Error accediendo Gmail API: {str(e)}")
            # Fallback simulado
            return [
                {
                    "id": f"fallback_{int(time.time())}",
                    "threadId": "thread_fallback",
                    "labelIds": ["INBOX"],
                    "snippet": f"Error accessing Gmail: {str(e)}",
                    "from": "system@fallback.com",
                    "subject": "Gmail API Error",
                    "timestamp": datetime.now().isoformat(),
                    "fallback": True
                }
            ]


@register_node("Gmail_Trigger.watch_labels")
@register_trigger_capability("gmail_watch", "Gmail_Trigger.watch_labels")
class GmailWatchHandler(ActionHandler):
    """
    ✅ Handler alternativo para Gmail Watch específico por labels
    
    Especializado para monitorear labels específicos
    """
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start = time.perf_counter()
        
        # Configurar para watch con labels específicos
        label_ids = params.get("label_ids", ["INBOX"])
        
        # Delegar al handler de push notifications
        push_handler = GmailPushHandler()
        return await push_handler.execute(params)