# app/authenticators/dropbox.py

import httpx
from urllib.parse import urlencode
from typing import Optional, Any, Dict
import logging

logger = logging.getLogger(__name__)
from app.authenticators.registry import register_authenticator
from sqlalchemy.ext.asyncio import AsyncSession
from app.authenticators.base_oauth_authenticator import BaseOAuthAuthenticator
from app.core.config import settings
from app.exceptions.api_exceptions import InvalidDataException, WorkflowProcessingException

@register_authenticator("oauth2", "dropbox")
class DropboxOAuthAuthenticator(BaseOAuthAuthenticator):
    """
    Implementa el flujo OAuth2 para Dropbox, aprovechando BaseOAuthAuthenticator:
      • save_state() y get_and_delete_state() para CSRF
      • upsert_credentials() para persistir credenciales cifradas
      • refresh_credentials() heredado (no hace nada)
    Puede recibir flavor, aunque Dropbox no lo usa para scopes.
    """

    # ✅ ELIMINADO: CATALOG_KEY - ahora se usa self.provider desde auth_policy
    # ❌ ELIMINADO: URLs hardcodeados
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
        self.client_id = settings.DROPBOX_CLIENT_ID
        self.client_secret = settings.DROPBOX_CLIENT_SECRET
        self.redirect_uri = settings.DROPBOX_REDIRECT_URI
        
        # ✅ MIGRADO: Usar auth_policy exclusivamente
        self.scopes = auth_policy.get("scopes", [])
        self.auth_url = auth_policy.get("auth_url", "https://www.dropbox.com/oauth2/authorize")
        self.token_url = "https://api.dropboxapi.com/oauth2/token"
        self.api_version = auth_policy.get("auth_config", {}).get("api_version", "2")
        logger.info(f"Using auth_policy: {len(self.scopes)} scopes, API v{self.api_version}")
        
        # Metadata adicional de la policy
        self.display_name = auth_policy.get("display_name", "Dropbox OAuth")
        self.provider = auth_policy.get("provider", "dropbox")
        self.service = auth_policy.get("service")
        self.service_id = auth_policy.get("service_id")

    async def authorization_url(self) -> str:
        """
        1) Genera y guarda un 'state' mediante save_state().
        2) Construye la URL de autorización de Dropbox.
        """
        try:
            state = await self.save_state(self.provider)
            params = {
                "client_id":     self.client_id,
                "response_type": "code",
                "redirect_uri":  str(self.redirect_uri),
                "state":         state,
            }
            query = urlencode(params)
            return f"{self.auth_url}?{query}"  # ✅ MIGRADO
        except Exception as e:
            raise WorkflowProcessingException(f"Error generando URL de autorización Dropbox: {e}")

    async def fetch_token(self, code: Optional[str] = None, state: Optional[str] = None) -> Any:
        """
        1) Valida y borra el 'state' con get_and_delete_state().
        2) Intercambia 'code' por 'access_token' en Dropbox.
        3) Persiste el 'access_token' + flavor vía upsert_credentials().
        4) Retorna settings.OAUTH_SUCCESS_URL para redirección.
        """
        if code is None or state is None:
            raise InvalidDataException("Se requiere 'code' y 'state' para completar OAuth Dropbox.")

        # If state is None, it means it was already validated by the OAuth router
        if state is not None:
            saved_state, incoming = await self.get_and_delete_state(self.provider, state)
            if saved_state != incoming:
                raise InvalidDataException("State inválido o expirado para Dropbox.")

        data = {
            "code":          code,
            "grant_type":    "authorization_code",
            "client_id":     self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri":  str(self.redirect_uri),
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self.token_url, data=data)  # ✅ MIGRADO
                resp.raise_for_status()
                token_data = resp.json()
        except httpx.HTTPStatusError as e:
            detail = e.response.json().get("error_description") or str(e)
            raise WorkflowProcessingException(f"Error al obtener token de Dropbox: {detail}")
        except Exception as e:
            raise WorkflowProcessingException(f"Error de red al contactar Dropbox: {e}")

        access_token = token_data.get("access_token")
        if not access_token:
            raise WorkflowProcessingException("Dropbox no devolvió access_token.")

        # Preparamos payload con la información mínima, usando service_id
        payload: Dict[str, Any] = {
            "user_id":       self.user_id,
            "chat_id":       None,  # 🌍 GLOBAL: Always save as global credentials
            "provider":      self.provider,
            "service_id":    self.service_id,
            "client_id":     None,  # TODO: En el futuro permitir user-provided OAuth credentials
            "client_secret": None,  # TODO: Por ahora usamos settings.DROPBOX_CLIENT_ID/SECRET del sistema
            "access_token":  access_token,
            "refresh_token": None,    # Dropbox no envía refresh_token en flujo estándar
            "expires_at":    None,    # Tokens de larga duración
            "scopes":        None,    # No se provee scopes aquí
        }

        try:
            await self.upsert_credentials(self.provider, payload)
        except Exception as e:
            raise WorkflowProcessingException(f"No se pudo guardar credenciales de Dropbox: {e}")

        return str(settings.OAUTH_SUCCESS_URL)

    # No es necesario sobrescribir `refresh_credentials`:
    # hereda el método que retorna el mismo `creds_obj` sin modificaciones.
