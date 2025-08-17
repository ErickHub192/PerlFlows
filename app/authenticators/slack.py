# app/authenticators/slack.py

import httpx
import logging
from urllib.parse import urlencode
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from app.authenticators.registry import register_authenticator
from sqlalchemy.ext.asyncio import AsyncSession  
from app.authenticators.base_oauth_authenticator import BaseOAuthAuthenticator
from app.core.config import settings
from app.exceptions.api_exceptions import InvalidDataException, WorkflowProcessingException

logger = logging.getLogger(__name__)

@register_authenticator("oauth2", "slack")
class SlackOAuthAuthenticator(BaseOAuthAuthenticator):
    """
    Implementa el flujo OAuth2 para Slack usando V2:
      - save_state() y get_and_delete_state() para manejo de CSRF.
      - upsert_credentials() para guardar/actualizar access_token (y opcional refresh_token).
    Basado en la documentación oficial de Slack. :contentReference[oaicite:6]{index=6}
    """

    # ✅ ELIMINADO: CATALOG_KEY - ahora se usa self.provider desde auth_policy
    # ❌ ELIMINADO: URLs y scopes hardcodeados
    # ✅ AHORA: Todo viene de auth_policy desde BD

    def __init__(
        self,
        user_id: int,
        db: AsyncSession,
        auth_policy: Dict[str, Any],
        chat_id: str = None
    ):
        """
        ✅ MIGRADO: Constructor que usa auth_policy exclusivamente
        """
        super().__init__(user_id=user_id, db=db, service_id=auth_policy.get("service_id"), chat_id=chat_id)
        self.auth_policy = auth_policy
        
        # ✅ MIGRADO: Usar auth_policy exclusivamente
        self.scopes = auth_policy.get("scopes", [])
        self.authorize_url = auth_policy.get("auth_url", "https://slack.com/oauth/v2/authorize")
        self.token_url = "https://slack.com/api/oauth.v2.access"
        self.api_version = auth_policy.get("auth_config", {}).get("api_version", "v2")
        logger.info(f"Using auth_policy: {len(self.scopes)} scopes, API {self.api_version}")
        
        # Metadata adicional de la policy
        self.display_name = auth_policy.get("display_name", "Slack OAuth")
        self.provider = auth_policy.get("provider", "slack")
        self.service = auth_policy.get("service")
        self.service_id = auth_policy.get("service_id")

    async def authorization_url(self) -> str:
        """
        1) Genera y guarda un 'state' para CSRF con save_state().
        2) Construye la URL de autorización de Slack:
             • client_id (settings.SLACK_CLIENT_ID)
             • redirect_uri (settings.OAUTH_CALLBACK_URL)
             • scope (lista de scopes unidos por comas o espacios)
             • state
             • user_scope (opcional, si necesitas scopes de usuario)
        3) Retorna la URL completa para redirigir al usuario.
        """
        state = await self.save_state(self.provider)

        # 🆕 NUEVO: Obtener credenciales OAuth híbridas (usuario o sistema)
        oauth_creds = await self.get_oauth_credentials()
        client_id = oauth_creds["client_id"]
        
        # ✅ MIGRADO: Usar scopes de auth_policy
        params = {
            "client_id":    client_id,  # ✅ Híbrido: usuario o sistema
            "redirect_uri": settings.OAUTH_CALLBACK_URL,
            "scope":        ",".join(self.scopes),  # Ahora viene de auth_policy
            "state":        state,
        }
        query = urlencode(params)
        return f"{self.authorize_url}?{query}"  # URL dinámica

    async def fetch_token(self, code: str, incoming_state: str) -> Dict[str, Any]:
        """
        1) Valida y elimina el 'state' con get_and_delete_state().
        2) Intercambia el 'code' por tokens en TOKEN_URL:
             • grant_type=authorization_code (implícito en Slack)
             • code
             • client_id, client_secret
             • redirect_uri
        3) Slack devuelve JSON que incluye:
             • access_token
             • token_type
             • scope (lista de scopes aprobados)
             • bot_user_id, app_id, authed_user (si aplica)
             • opcional: refresh_token, expires_in (si está activada rotación)
        4) Calcula expires_at si viene expires_in; de lo contrario, lo deja como None.
        5) Guarda en BD usando upsert_credentials():
             payload = {
               "user_id":       self.user_id,
               "provider":      self.provider,
               "client_id":     settings.SLACK_CLIENT_ID,
               "client_secret": settings.SLACK_CLIENT_SECRET,
               "access_token":  tk["access_token"],
               "refresh_token": tk.get("refresh_token"),
               "expires_at":    expires_at_iso,
               "scopes":        self.scopes,  # ✅ MIGRADO: Usar scopes de auth_policy
             }
        6) Retorna el JSON original de Slack con “expires_at” añadido si se calculó.
        """
        # If state is None, it means it was already validated by the OAuth router
        if incoming_state is not None:
            saved_state, _ = await self.get_and_delete_state(self.provider, incoming_state)
            if saved_state != incoming_state:
                raise InvalidDataException("State inválido o expirado para Slack.")

        # 🆕 NUEVO: Obtener credenciales OAuth híbridas (usuario o sistema)
        oauth_creds = await self.get_oauth_credentials()
        client_id = oauth_creds["client_id"]
        client_secret = oauth_creds["client_secret"]
        
        data = {
            "client_id":     client_id,     # ✅ Híbrido: usuario o sistema
            "client_secret": client_secret, # ✅ Híbrido: usuario o sistema
            "code":          code,
            "redirect_uri":  settings.OAUTH_CALLBACK_URL,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self.token_url, data=data, headers=headers)  # ✅ MIGRADO
                resp.raise_for_status()
                tk = resp.json()
        except httpx.HTTPError as e:
            detail = ""
            try:
                detail = e.response.json().get("error", "")
            except Exception:
                detail = str(e)
            raise WorkflowProcessingException(f"Error intercambiando código en Slack: {detail}")

        # Si Slack incluyó "expires_in" (solo con token rotation)
        expires_at_iso: Optional[str] = None
        expires_in = tk.get("expires_in")
        if expires_in is not None:
            try:
                expires_seconds = int(expires_in)
                expires_at_iso = (datetime.utcnow() + timedelta(seconds=expires_seconds)).isoformat()
            except Exception:
                expires_at_iso = None

        payload = {
            "user_id":       self.user_id,
            "chat_id":       None,  # 🌍 GLOBAL: Always save as global credentials
            "service_id":    self.service_id,
            "provider":      self.provider,
            "client_id":     None,  # TODO: En el futuro permitir user-provided OAuth credentials
            "client_secret": None,  # TODO: Por ahora usamos settings.SLACK_CLIENT_ID/SECRET del sistema
            "access_token":  tk.get("access_token"),
            "refresh_token": tk.get("refresh_token"),  # puede ser None si no hay rotación
            "expires_at":    expires_at_iso,
            "scopes":        self.scopes,
        }
        await self.upsert_credentials(self.provider, payload)

        # Añadir expires_at al JSON devuelto
        result = {**tk}
        if expires_at_iso:
            result["expires_at"] = expires_at_iso

        return result

    async def refresh_credentials(self, creds_obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        1) Verifica si 'expires_at' ya pasó y existe 'refresh_token'.
        2) Si expiró y hay refresh_token, llama de nuevo a TOKEN_URL con:
             • grant_type=refresh_token
             • refresh_token, client_id, client_secret
        3) Slack devuelve nuevos access_token y expires_in.
        4) Actualiza BD usando upsert_credentials() y retorna el JSON con nuevo 'expires_at'.
        5) Si no expiró o no hay refresh_token, retorna el mismo objeto.
        """
        exp_str = creds_obj.get("expires_at")
        if not exp_str:
            # Sin expires_at configurado → token de larga duración
            return creds_obj

        exp = datetime.fromisoformat(exp_str)
        if exp <= datetime.utcnow() and creds_obj.get("refresh_token"):
            # 🆕 NUEVO: Obtener credenciales OAuth híbridas para refresh
            oauth_creds = await self.get_oauth_credentials()
            client_id = oauth_creds["client_id"]
            client_secret = oauth_creds["client_secret"]
            
            data = {
                "grant_type":    "refresh_token",
                "refresh_token": creds_obj["refresh_token"],
                "client_id":     client_id,     # ✅ Híbrido: usuario o sistema
                "client_secret": client_secret, # ✅ Híbrido: usuario o sistema
            }
            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(self.token_url, data=data, headers=headers)  # ✅ MIGRADO
                    resp.raise_for_status()
                    tk = resp.json()
            except httpx.HTTPError as e:
                detail = ""
                try:
                    detail = e.response.json().get("error", "")
                except Exception:
                    detail = str(e)
                raise WorkflowProcessingException(f"Error refrescando token Slack: {detail}")

            # Recalcular expires_at
            new_expires_in = tk.get("expires_in")
            new_expires_iso = None
            if new_expires_in is not None:
                try:
                    secs = int(new_expires_in)
                    new_expires_iso = (datetime.utcnow() + timedelta(seconds=secs)).isoformat()
                except Exception:
                    new_expires_iso = None

            payload = {
                "user_id":       self.user_id,
                "chat_id":       None,  # 🌍 GLOBAL: Always save as global credentials
                "service_id":    self.service_id,
                "provider":      self.provider,
                "client_id":     None,  # TODO: En el futuro permitir user-provided OAuth credentials
                "client_secret": None,  # TODO: Por ahora usamos settings.SLACK_CLIENT_ID/SECRET del sistema
                "access_token":  tk.get("access_token"),
                "refresh_token": tk.get("refresh_token", creds_obj["refresh_token"]),
                "expires_at":    new_expires_iso,
                "scopes":        self.scopes,  # ✅ MIGRADO: Usar scopes de auth_policy
            }
            await self.upsert_credentials(self.provider, payload)

            result = {**tk}
            if new_expires_iso:
                result["expires_at"] = new_expires_iso
            return result

        return creds_obj
