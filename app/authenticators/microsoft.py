# app/authenticators/microsoft.py

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

@register_authenticator("oauth2", "microsoft")
@register_authenticator("oauth2", "outlook") 
class MicrosoftOAuthAuthenticator(BaseOAuthAuthenticator):
    """
    Maneja OAuth2 para Microsoft, distinguiendo posibles flavors como:
      • "mail"     → scope para enviar correo (Mail.Send)
      • "calendar" → scope para gestionar calendarios (Calendars.ReadWrite)
      • flavor=None → usa scopes por defecto (Mail.Send)
    Hereda BaseOAuthAuthenticator para CSRF y persistencia de credenciales.
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
        - user_id:      ID entero del usuario.
        - db:           sesión asíncrona de SQLAlchemy.
        - auth_policy:  Política de auth desde BD (requerida)
        - chat_id:      ID del chat para credentials
        """
        super().__init__(user_id=user_id, db=db, service_id=auth_policy.get("service_id"), chat_id=chat_id)
        self.auth_policy = auth_policy
        
        # ✅ MIGRADO: Usar auth_policy exclusivamente
        self.scopes = auth_policy.get("scopes", [])
        self.authorize_url = auth_policy.get("auth_url", "https://login.microsoftonline.com/common/oauth2/v2.0/authorize")
        self.token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        self.api_version = auth_policy.get("auth_config", {}).get("api_version", "v1.0")
        logger.info(f"Using auth_policy: {len(self.scopes)} scopes, API {self.api_version}")
        
        # Metadata adicional de la policy
        self.display_name = auth_policy.get("display_name", f"Microsoft {auth_policy.get('service', 'OAuth')}")
        self.provider = auth_policy.get("provider", "microsoft")
        self.service = auth_policy.get("service")
        self.service_id = auth_policy.get("service_id")

    async def authorization_url(self) -> str:
        """
        1) Genera y guarda un 'state' único para CSRF.
        2) Construye la URL de autorización de Microsoft con los scopes de self.flavor.
        """
        state = await self.save_state(self.provider)
        params = {
            "client_id":     settings.MICROSOFT_CLIENT_ID,
            "redirect_uri":  settings.OAUTH_CALLBACK_URL,
            "response_type": "code",
            "response_mode": "query",
            "scope":         " ".join(self.scopes),
            "state":         state,
        }
        query = urlencode(params)
        return f"{self.authorize_url}?{query}"

    async def fetch_token(self, code: str, incoming_state: str) -> Dict[str, Any]:
        """
        1) Valida y elimina el 'state' guardado.
        2) Intercambia el 'code' por tokens en TOKEN_URL.
        3) Calcula expires_at y persiste credenciales (incluye flavor).
        4) Retorna el JSON original con 'expires_at'.
        """
        # If state is None, it means it was already validated by the OAuth router
        if incoming_state is not None:
            saved_state, _ = await self.get_and_delete_state(self.provider, incoming_state)
            if saved_state != incoming_state:
                raise InvalidDataException("State inválido o expirado para Microsoft.")

        data = {
            "client_id":     settings.MICROSOFT_CLIENT_ID,
            "client_secret": settings.MICROSOFT_CLIENT_SECRET,
            "code":          code,
            "redirect_uri":  settings.OAUTH_CALLBACK_URL,
            "grant_type":    "authorization_code",
            "scope":         " ".join(self.scopes),
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self.token_url, data=data)
                resp.raise_for_status()
                tk = resp.json()
        except httpx.HTTPError as e:
            raise WorkflowProcessingException(f"Error intercambiando código por token en Microsoft: {e}")

        expires_at = (datetime.utcnow() + timedelta(seconds=int(tk.get("expires_in", 0)))).isoformat()

        payload = {
            "user_id":       self.user_id,
            "chat_id":       None,  # 🌍 GLOBAL: Always save as global credentials
            "service_id":    self.service_id,
            "provider":      self.provider,
            "client_id":     None,  # TODO: En el futuro permitir user-provided OAuth credentials
            "client_secret": None,  # TODO: Por ahora usamos settings.MICROSOFT_CLIENT_ID/SECRET del sistema
            "access_token":  tk.get("access_token"),
            "refresh_token": tk.get("refresh_token"),
            "expires_at":    expires_at,
            "scopes":        self.scopes,
        }
        await self.upsert_credentials(self.provider, payload)
        return {**tk, "expires_at": expires_at}

    async def refresh_credentials(self, creds_obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        1) Verifica si 'expires_at' ya pasó y hay 'refresh_token'.
        2) Si expiró, envía POST a TOKEN_URL con grant_type=refresh_token.
        3) Calcula new_expires, actualiza BD (incluye flavor) y retorna {…,"expires_at"}.
        4) Si no expiró o no hay refresh_token, devuelve creds_obj sin cambios.
        """
        exp_str = creds_obj.get("expires_at")
        if not exp_str:
            return creds_obj

        try:
            exp = datetime.fromisoformat(exp_str)
        except Exception:
            return creds_obj

        if exp <= datetime.utcnow() and creds_obj.get("refresh_token"):
            data = {
                "grant_type":    "refresh_token",
                "refresh_token": creds_obj["refresh_token"],
                "client_id":     settings.MICROSOFT_CLIENT_ID,
                "client_secret": settings.MICROSOFT_CLIENT_SECRET,
                "scope":         " ".join(self.scopes),
            }
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(self.token_url, data=data)
                    resp.raise_for_status()
                    tk = resp.json()
            except httpx.HTTPError as e:
                raise WorkflowProcessingException(f"Error refrescando token de Microsoft: {e}")

            new_expires = (datetime.utcnow() + timedelta(seconds=int(tk.get("expires_in", 0)))).isoformat()
            payload = {
                "user_id":       self.user_id,
                "chat_id":       None,  # 🌍 GLOBAL: Always save as global credentials
                "service_id":    self.service_id,
                "provider":      self.provider,
                "client_id":     None,  # TODO: En el futuro permitir user-provided OAuth credentials
                "client_secret": None,  # TODO: Por ahora usamos settings.MICROSOFT_CLIENT_ID/SECRET del sistema
                "access_token":  tk.get("access_token"),
                "refresh_token": tk.get("refresh_token", creds_obj["refresh_token"]),
                "expires_at":    new_expires,
                "scopes":        self.scopes,
            }
            await self.upsert_credentials(self.provider, payload)
            return {**tk, "expires_at": new_expires}

        return creds_obj
