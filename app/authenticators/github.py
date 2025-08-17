# app/authenticators/github.py

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

@register_authenticator("oauth2", "github")
class GitHubOAuthAuthenticator(BaseOAuthAuthenticator):
    """
    Implementa el flujo OAuth2 para GitHub usando BaseOAuthAuthenticator:
    - save_state() / get_and_delete_state() para manejo de 'state'
    - upsert_credentials() para guardar/actualizar credenciales en la BD.

    Usa:
      • Authorization URL:  https://github.com/login/oauth/authorize
      • Token URL:          https://github.com/login/oauth/access_token
      • Scopes:             "repo", "user", "admin:org", etc.
    """

    # ✅ ELIMINADO: CATALOG_KEY - ahora se usa self.provider desde auth_policy
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
        self.authorize_url = auth_policy.get("auth_url", "https://github.com/login/oauth/authorize")
        self.token_url = "https://github.com/login/oauth/access_token"
        self.api_version = auth_policy.get("auth_config", {}).get("api_version", "v3")
        logger.info(f"Using auth_policy: {len(self.scopes)} scopes, API {self.api_version}")
        
        # Metadata adicional de la policy
        self.display_name = auth_policy.get("display_name", "GitHub OAuth")
        self.provider = auth_policy.get("provider", "github")
        self.service = auth_policy.get("service")
        self.service_id = auth_policy.get("service_id")

    async def authorization_url(self) -> str:
        """
        1) Genera y guarda un 'state' (save_state) para protección CSRF.
        2) Construye la URL de autorización de GitHub con:
           • client_id
           • redirect_uri
           • response_type=code
           • scope=repo user
           • state
        3) Retorna la URL completa.
        """
        state = await self.save_state(self.provider)

        params = {
            "client_id":     settings.GITHUB_CLIENT_ID,
            "redirect_uri":  settings.OAUTH_CALLBACK_URL,
            "response_type": "code",
            "scope":         " ".join(self.scopes),
            "state":         state,
        }
        query = urlencode(params)
        return f"{self.authorize_url}?{query}"

    async def fetch_token(self, code: str, incoming_state: str) -> Dict[str, Any]:
        """
        1) Valida y elimina el 'state' con get_and_delete_state().
        2) Intercambia el 'code' por tokens en TOKEN_URL.
        3) GitHub tokens no expiran automáticamente (access_token de larga duración).
        4) Guarda tokens en la BD (upsert_credentials).
        5) Retorna el JSON original de GitHub.
        """
        # If state is None, it means it was already validated by the OAuth router
        if incoming_state is not None:
            saved_state, _ = await self.get_and_delete_state(self.provider, incoming_state)
            if saved_state != incoming_state:
                raise InvalidDataException("State inválido o expirado para GitHub.")

        data = {
            "client_id":     settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code":          code,
            "redirect_uri":  settings.OAUTH_CALLBACK_URL,
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self.token_url, data=data, headers=headers)
                resp.raise_for_status()
                tk = resp.json()
        except httpx.HTTPError as e:
            detail = ""
            try:
                detail = e.response.json().get("error_description", "")
            except Exception:
                detail = str(e)
            raise WorkflowProcessingException(f"Error intercambiando código en GitHub: {detail}")

        # GitHub tokens no expiran automáticamente
        payload = {
            "user_id":       self.user_id,
            "chat_id":       None,  # 🌍 GLOBAL: Always save as global credentials
            "service_id":    self.service_id,
            "provider":      self.provider,
            "client_id":     None,  # TODO: En el futuro permitir user-provided OAuth credentials
            "client_secret": None,  # TODO: Por ahora usamos settings.GITHUB_CLIENT_ID/SECRET del sistema
            "access_token":  tk.get("access_token"),
            "refresh_token": None,    # GitHub no usa refresh tokens en flujo estándar
            "expires_at":    None,    # Tokens de larga duración
            "scopes":        self.scopes,
        }
        await self.upsert_credentials(self.provider, payload)

        return tk

    async def refresh_credentials(self, creds_obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        GitHub tokens no expiran automáticamente, por lo que este método
        simplemente retorna el mismo objeto sin modificaciones.
        """
        return creds_obj