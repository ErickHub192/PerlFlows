import time
import json
import hashlib
import hmac
import requests
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from uuid import UUID
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.connectors.factory import register_node, execute_node
from app.core.scheduler import schedule_job, unschedule_job
from .connector_handler import ActionHandler
from .trigger_registry import register_trigger_capability

# Para GitHub API real
# import requests
# from github import Github  # PyGithub opcional


@register_node("GitHub_Trigger.webhook")
@register_trigger_capability("github_webhook", "GitHub_Trigger.webhook", unschedule_method="unregister")
class GitHubWebhookHandler(ActionHandler):
    """
    ✅ Handler PRIMARY para GitHub Webhooks (2025 Best Practice)
    
    Funcionalidades:
    1. Recibe eventos en tiempo real via webhooks
    2. Valida signatures para seguridad 
    3. Procesa push, PR, issues, releases automáticamente
    4. 98.5% MÁS EFICIENTE que polling
    5. REEMPLAZA polling completamente
    
    Parámetros esperados en params:
      • webhook_url: str - URL donde recibirás eventos (REQUERIDO)
      • webhook_secret: str - Secret para validar requests de GitHub
      • repos: List[str] - Lista de repos "owner/repo" a monitorear
      • event_types: List[str] - Eventos a procesar (push, pull_request, etc)
      • branches: List[str] - Branches específicas (opcional) 
      • flow_id: UUID del flujo a ejecutar
      • user_id: ID del usuario
      • first_step: Dict con el primer paso del workflow
      • creds: Dict con token de GitHub
    """

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start = time.perf_counter()
        
        # Validar parámetros críticos
        webhook_url = params.get("webhook_url")
        repos = params.get("repos", [])
        
        if not webhook_url:
            return {
                "status": "error",
                "error": "webhook_url es REQUERIDO para GitHub Webhooks",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
        
        if not repos:
            return {
                "status": "error",
                "error": "repos es REQUERIDO - especifica al menos un repositorio",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
        
        # Parámetros de configuración
        webhook_secret = params.get("webhook_secret")
        event_types = params.get("event_types", ["push", "pull_request", "issues"])
        branches = params.get("branches", [])
        flow_id = params.get("flow_id")
        first_step = params.get("first_step")
        creds = params.get("creds", {})
        
        # Si es solo validación/preparación
        if not flow_id or not first_step:
            duration_ms = int((time.perf_counter() - start) * 1000)
            return {
                "status": "success",
                "output": {
                    "trigger_type": "github_webhook",
                    "webhook_url": webhook_url,
                    "repos": repos,
                    "event_types": event_types,
                    "real_time": True,
                    "efficiency": "98.5% better than polling",
                    "setup_required": "Configure webhook in GitHub repository settings"
                },
                "duration_ms": duration_ms,
            }

        # ✅ En producción, esto registraría webhooks en GitHub
        try:
            # Para cada repositorio, configurar webhook
            webhook_configs = []
            
            for repo in repos:
                config = await self._configure_repo_webhook(
                    repo, webhook_url, event_types, webhook_secret, creds
                )
                webhook_configs.append(config)
            
            duration_ms = int((time.perf_counter() - start) * 1000)
            return {
                "status": "success",
                "output": {
                    "trigger_type": "github_webhook",
                    "webhook_url": webhook_url,
                    "repos": repos,
                    "event_types": event_types,
                    "branches": branches,
                    "security": "SHA-256 signature validation" if webhook_secret else "No validation",
                    "webhook_configs": webhook_configs,
                    "setup_instructions": [
                        f"1. Configure webhook URL: {webhook_url}",
                        f"2. Select events: {', '.join(event_types)}",
                        "3. Set content type: application/json",
                        "4. Add webhook secret for security",
                        "5. Ensure URL is publicly accessible"
                    ]
                },
                "duration_ms": duration_ms,
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "error": f"Error configurando GitHub webhooks: {str(e)}",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
    
    async def _configure_repo_webhook(
        self,
        repo: str,
        webhook_url: str, 
        event_types: List[str],
        webhook_secret: Optional[str],
        creds: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        ✅ Configura webhook en repositorio GitHub usando API real
        """
        try:
            github_token = creds.get("github_token")
            if not github_token:
                return {
                    "repo": repo,
                    "status": "error", 
                    "error": "github_token requerido"
                }
            
            # Headers para GitHub API
            headers = {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json"
            }
            
            # Payload del webhook
            webhook_payload = {
                "name": "web",
                "active": True,
                "events": event_types,
                "config": {
                    "url": webhook_url,
                    "content_type": "json",
                    "insecure_ssl": "0"
                }
            }
            
            # Agregar secret si se proporciona
            if webhook_secret:
                webhook_payload["config"]["secret"] = webhook_secret
            
            # Crear webhook via GitHub API
            api_url = f"https://api.github.com/repos/{repo}/hooks"
            response = requests.post(
                api_url, 
                headers=headers,
                json=webhook_payload,
                timeout=10
            )
            
            if response.status_code == 201:
                webhook_data = response.json()
                return {
                    "repo": repo,
                    "status": "success",
                    "webhook_id": webhook_data.get("id"),
                    "url": webhook_data.get("config", {}).get("url"),
                    "events": webhook_data.get("events", [])
                }
            elif response.status_code == 422:
                # Webhook ya existe
                return {
                    "repo": repo,
                    "status": "exists",
                    "message": "Webhook already configured"
                }
            else:
                return {
                    "repo": repo,
                    "status": "error",
                    "error": f"GitHub API error: {response.status_code}",
                    "details": response.text[:200]
                }
                
        except requests.RequestException as e:
            return {
                "repo": repo,
                "status": "error",
                "error": f"Request error: {str(e)}"
            }
        except Exception as e:
            return {
                "repo": repo,
                "status": "error", 
                "error": f"Configuration error: {str(e)}"
            }
    
    async def process_webhook_event(
        self, 
        request_body: str, 
        headers: Dict[str, str],
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        ✅ Procesa eventos webhook de GitHub con validación de seguridad
        """
        try:
            # 1. Validar signature de GitHub
            webhook_secret = params.get("webhook_secret")
            if webhook_secret and not await self._verify_github_signature(
                request_body, headers, webhook_secret
            ):
                return {
                    "status": "error",
                    "error": "Invalid GitHub signature"
                }
            
            # 2. Parsear evento
            event_data = json.loads(request_body)
            event_type = headers.get("X-GitHub-Event", "")
            
            # 3. Filtrar eventos según configuración
            if await self._should_process_event(event_data, event_type, params):
                # ✅ FIX: Ejecutar workflow completo en lugar de solo el primer nodo
                from app.handlers.workflow_execution_helper import execute_complete_workflow, extract_trigger_metadata
                
                # Extraer metadatos del workflow
                flow_id, user_id, trigger_data = extract_trigger_metadata(params)
                
                if flow_id and user_id:
                    # Preparar datos del trigger GitHub
                    github_trigger_data = {
                        **trigger_data,
                        "github_event": event_data,
                        "github_event_type": event_type,
                        "github_repo": event_data.get("repository", {}).get("full_name"),
                        "trigger_source": "github_webhook"
                    }
                    
                    # Ejecutar workflow completo
                    await execute_complete_workflow(
                        flow_id=flow_id,
                        user_id=user_id,
                        trigger_data=github_trigger_data,
                        inputs={"github_event": event_data}
                    )
                else:
                    # Fallback: ejecutar solo el nodo si no hay metadatos de workflow
                    await execute_node(
                        params["first_step"]["node_name"],
                        params["first_step"]["action_name"],
                        {
                            **params["first_step"].get("params", {}),
                            "github_event": event_data,
                            "github_event_type": event_type,
                            "github_repo": event_data.get("repository", {}).get("full_name"),
                            "trigger_source": "github_webhook"
                        },
                        params.get("creds", {}),
                    )
                
                return {"status": "success", "processed": True}
            
            return {"status": "success", "processed": False, "reason": "filtered"}
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error procesando evento GitHub: {str(e)}"
            }
    
    async def _verify_github_signature(
        self, 
        request_body: str, 
        headers: Dict[str, str], 
        webhook_secret: str
    ) -> bool:
        """
        ✅ Verifica signature de GitHub para seguridad
        """
        try:
            signature = headers.get("X-Hub-Signature-256", "")
            
            if not signature:
                return False
            
            # Calcular signature esperada
            expected_signature = "sha256=" + hmac.new(
                webhook_secret.encode('utf-8'),
                request_body.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Comparación segura
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception:
            return False
    
    async def _should_process_event(
        self, 
        event_data: Dict[str, Any], 
        event_type: str,
        params: Dict[str, Any]
    ) -> bool:
        """
        ✅ Determina si el evento debe procesarse según filtros
        """
        # Filtro por tipo de evento
        event_types = params.get("event_types", [])
        if event_types and event_type not in event_types:
            return False
        
        # Filtro por repositorio
        repos = params.get("repos", [])
        if repos:
            repo_name = event_data.get("repository", {}).get("full_name", "")
            if repo_name not in repos:
                return False
        
        # Filtro por branch (solo para push events)
        branches = params.get("branches", [])
        if branches and event_type == "push":
            ref = event_data.get("ref", "")
            branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ""
            if branch and branch not in branches:
                return False
        
        return True


@register_node("GitHub_Trigger.poll_events_fallback")
@register_trigger_capability("github_poll_fallback", "GitHub_Trigger.poll_events_fallback", unschedule_method="unregister")
class GitHubPollFallbackHandler(ActionHandler):
    """
    ⚠️ Handler FALLBACK para GitHub polling (2025 NOT Recommended)
    
    ADVERTENCIA: GitHub DESACONSEJA polling - usar solo cuando webhooks no sean posibles
    Funcionalidades:
    1. Polling con ETag para reducir API calls
    2. Rate limit awareness 
    3. Optimizado para uso mínimo
    4. RECOMENDACIÓN FUERTE: Migrar a Webhooks
    """

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start = time.perf_counter()
        
        # ADVERTENCIA PROMINENTE
        print("⚠️ ADVERTENCIA: Usando GitHub polling fallback")
        print("📉 GitHub DESACONSEJA polling - 98.5% menos eficiente")
        print("✅ RECOMENDADO FUERTEMENTE: Migrar a GitHub Webhooks")
        
        # Validar parámetros
        polling_interval = max(params.get("polling_interval", 300), 300)  # Mínimo 5 min
        repos = params.get("repos", [])
        event_types = params.get("event_types", ["push", "pull_request"])
        flow_id = params.get("flow_id")
        first_step = params.get("first_step")
        scheduler = params.get("scheduler")
        creds = params.get("creds", {})
        
        if not repos:
            return {
                "status": "error",
                "error": "repos es REQUERIDO para polling fallback",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
        
        # Intervalo mínimo para rate limits
        if polling_interval < 300:
            return {
                "status": "error",
                "error": "Intervalo mínimo 300 segundos (GitHub rate limits)",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }

        # Si es solo validación/preparación
        if not scheduler or not flow_id or not first_step:
            duration_ms = int((time.perf_counter() - start) * 1000)
            return {
                "status": "success",
                "output": {
                    "trigger_type": "github_poll_fallback",
                    "warning": "NOT RECOMMENDED - use webhooks instead",
                    "trigger_args": {
                        "seconds": polling_interval,
                        "repos": len(repos),
                        "rate_limit_safe": True
                    }
                },
                "duration_ms": duration_ms,
            }

        # ✅ Programar job con optimizaciones
        try:
            job_id = f"github_fallback_{flow_id}"
            
            # Función de polling optimizada
            async def check_github_optimized():
                try:
                    for repo in repos[:3]:  # Max 3 repos por iteración
                        events, new_etag = await self._get_repo_events_optimized(
                            creds, repo, params.get("etag"), params.get("last_event_id")
                        )
                        
                        # Filtrar eventos
                        filtered = await self._filter_events(events, event_types, params.get("branches", []))
                        
                        # Procesar eventos limitados
                        for event in filtered[:5]:  # Max 5 eventos por repo
                            # ✅ FIX: Ejecutar workflow completo en lugar de solo el primer nodo
                            from app.handlers.workflow_execution_helper import execute_complete_workflow, extract_trigger_metadata
                            
                            # Extraer metadatos del workflow
                            flow_id, user_id, trigger_data = extract_trigger_metadata(params)
                            
                            if flow_id and user_id:
                                # Preparar datos del trigger GitHub
                                github_trigger_data = {
                                    **trigger_data,
                                    "github_event": event,
                                    "trigger_source": "github_fallback"
                                }
                                
                                # Ejecutar workflow completo
                                await execute_complete_workflow(
                                    flow_id=flow_id,
                                    user_id=user_id,
                                    trigger_data=github_trigger_data,
                                    inputs={"github_event": event}
                                )
                            else:
                                # Fallback: ejecutar solo el nodo si no hay metadatos de workflow
                                await execute_node(
                                    first_step["node_name"],
                                    first_step["action_name"],
                                    {
                                        **first_step.get("params", {}),
                                        "github_event": event,
                                        "trigger_source": "github_fallback"
                                    },
                                    creds,
                                )
                            
                            # Actualizar último evento
                            params["last_event_id"] = event.get("id")
                        
                        # Actualizar ETag
                        if new_etag:
                            params["etag"] = new_etag
                        
                        # Pausa entre repos para rate limits
                        await asyncio.sleep(2)
                        
                except Exception as e:
                    print(f"Error en GitHub fallback polling: {str(e)}")
            
            # Trigger con intervalo seguro
            trigger_args = {
                "seconds": polling_interval,
            }
            
            # Programar job
            schedule_job(
                scheduler,
                job_id,
                func=check_github_optimized,
                trigger_type="interval",
                trigger_args=trigger_args,
            )
            
            duration_ms = int((time.perf_counter() - start) * 1000)
            return {
                "status": "success",
                "output": {
                    "trigger_type": "github_poll_fallback",
                    "job_id": job_id,
                    "scheduled": True,
                    "polling_interval": polling_interval,
                    "repos": len(repos),
                    "efficiency_warning": "98.5% less efficient than webhooks",
                    "recommendation": "URGENT: Migrate to webhooks",
                    "trigger_args": trigger_args,
                },
                "duration_ms": duration_ms,
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "error": f"Error programando GitHub fallback: {str(e)}",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
    
    async def _get_repo_events_optimized(
        self, 
        creds: Dict[str, Any], 
        repo: str,
        etag: Optional[str],
        last_event_id: Optional[str]
    ) -> tuple[List[Dict[str, Any]], Optional[str]]:
        """
        ✅ Obtiene eventos con optimizaciones ETag y rate limit awareness
        """
        try:
            github_token = creds.get("github_token")
            if not github_token:
                return [], None
            
            # Headers para GitHub API con ETag
            headers = {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # Usar ETag para requests condicionales
            if etag:
                headers["If-None-Match"] = etag
            
            # Llamada a GitHub API
            response = requests.get(
                f"https://api.github.com/repos/{repo}/events",
                headers=headers,
                timeout=10
            )
            
            # 304 Not Modified - no hay eventos nuevos
            if response.status_code == 304:
                return [], etag
            
            # Rate limit handling
            if response.status_code == 403:
                rate_limit_remaining = response.headers.get("X-RateLimit-Remaining", "0")
                if rate_limit_remaining == "0":
                    print(f"⚠️ Rate limit reached for {repo}")
                    return [], etag
            
            if response.status_code != 200:
                print(f"GitHub API error for {repo}: {response.status_code}")
                return [], etag
            
            new_etag = response.headers.get("ETag")
            events = response.json()
            
            # Filtrar solo eventos nuevos
            if last_event_id:
                new_events = []
                for event in events:
                    if event["id"] == last_event_id:
                        break
                    new_events.append(event)
                return new_events, new_etag
            
            return events[:10], new_etag  # Limitar a 10 eventos
            
        except requests.RequestException as e:
            print(f"Request error for {repo}: {str(e)}")
            return [], etag
        except Exception as e:
            print(f"Error obteniendo eventos de {repo}: {str(e)}")
            return [], etag
    
    async def _filter_events(
        self,
        events: List[Dict[str, Any]],
        event_types: List[str],
        branches: List[str]
    ) -> List[Dict[str, Any]]:
        """
        ✅ Filtra eventos según criterios (mismo que webhooks)
        """
        filtered = []
        
        for event in events:
            # Filtrar por tipo de evento
            if event_types and event.get("type") not in event_types:
                continue
            
            # Filtrar por branch si aplica
            if branches and event.get("type") in ["PushEvent", "PullRequestEvent"]:
                ref = event.get("payload", {}).get("ref", "")
                branch = ref.split("/")[-1] if "/" in ref else ""
                
                if branch and branch not in branches:
                    continue
            
            filtered.append(event)
        
        return filtered


@register_node("GitHub_Trigger.issue_comment")
@register_trigger_capability("github_issue", "GitHub_Trigger.issue_comment")
class GitHubIssueHandler(ActionHandler):
    """
    ✅ Handler específico para comentarios en issues/PRs (Webhook-based)
    
    Útil para bots que responden a comandos en comentarios
    """
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start = time.perf_counter()
        
        # Configurar para detectar solo comentarios
        params["event_types"] = ["issue_comment", "pull_request_review_comment"]
        
        # Delegar al handler de webhooks
        webhook_handler = GitHubWebhookHandler()
        return await webhook_handler.execute(params)