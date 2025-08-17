# app/authenticators/whatsapp.py

import httpx
from urllib.parse import urlencode
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)
from app.authenticators.registry import register_authenticator
from sqlalchemy.ext.asyncio import AsyncSession
from app.authenticators.base_oauth_authenticator import BaseOAuthAuthenticator
from app.core.config import settings
from app.exceptions.api_exceptions import InvalidDataException, WorkflowProcessingException

@register_authenticator("oauth2", "whatsapp")
class WhatsAppOAuthAuthenticator(BaseOAuthAuthenticator):
    """
    Implementa OAuth2 para WhatsApp Business Cloud API a través de Facebook Login.
    - save_state() / get_and_delete_state() para manejo de CSRF.
    - upsert_credentials() para guardar/actualizar access_token y expires_at.
    Flujo basado en:
      • https://developers.facebook.com/docs/whatsapp/cloud-api/get-started/  :contentReference[oaicite:0]{index=0}
      • https://developers.facebook.com/docs/facebook-login/manually-build-a-login-flow/  
    """

    CATALOG_KEY = "whatsapp"
    # ❌ ELIMINADO: URLs y scopes hardcodeados
    # ✅ AHORA: Todo viene de auth_policy desde BD

    def __init__(
        self,
        user_id: int,
        db: AsyncSession,
        auth_policy: Dict[str, Any]
    ):
        """
        ✅ MIGRADO: Constructor que usa auth_policy
        """
        super().__init__(user_id=user_id, db=db)
        self.auth_policy = auth_policy
        
        # ✅ MIGRADO: Usar auth_policy exclusivamente
        self.scopes = auth_policy.get("scopes", [])
        self.authorize_url = auth_policy.get("auth_url", "https://www.facebook.com/v15.0/dialog/oauth")
        self.token_url = "https://graph.facebook.com/v15.0/oauth/access_token"
        self.api_version = auth_policy.get("auth_config", {}).get("api_version", "v15.0")
        logger.info(f"Using auth_policy: {len(self.scopes)} scopes, API {self.api_version}")
        
        # Metadata adicional de la policy
        self.display_name = auth_policy.get("display_name", "WhatsApp Business OAuth")
        self.provider = auth_policy.get("provider", "whatsapp")
        self.service = auth_policy.get("service")
        self.service_id = auth_policy.get("service_id")

    async def authorization_url(self) -> str:
        """
        1) Genera y guarda un 'state' (save_state) para evitar CSRF.
        2) Construye la URL de autorización de Facebook con scopes de WhatsApp.
        3) Devuelve la URL completa para redirigir al usuario.

        Parámetros obligatorios:
          • client_id: el App ID de Facebook (settings.WHATSAPP_CLIENT_ID).
          • redirect_uri: settings.OAUTH_CALLBACK_URL.
          • scope: “whatsapp_business_messaging whatsapp_business_management”.
          • state: valor aleatorio guardado vía save_state().
          • response_type=code.
        """
        state = await self.save_state(self.CATALOG_KEY)

        params = {
            "client_id":     settings.WHATSAPP_CLIENT_ID,
            "redirect_uri":  settings.OAUTH_CALLBACK_URL,
            "response_type": "code",
            "scope":         " ".join(self.scopes),  # ✅ MIGRADO
            "state":         state,
        }
        query = urlencode(params)
        return f"{self.authorize_url}?{query}"  # ✅ MIGRADO

    async def fetch_token(self, code: str, incoming_state: str) -> Dict[str, Any]:
        """
        1) Valida y elimina el 'state' guardado (get_and_delete_state).
        2) Intercambia el 'code' por un access_token en el endpoint de Facebook.
           Parámetros:
             • grant_type: implícitamente “authorization_code”.
             • code: recibido de Facebook.
             • client_id y client_secret (de settings).
             • redirect_uri (must match).
        3) Facebook devuelve JSON con:
             • access_token
             • token_type
             • expires_in (segundos)
        4) Calcula expires_at = ahora + expires_in segundos.
        5) Guarda en BD: user_id, provider="whatsapp", client_id, client_secret, access_token, expires_at, scopes.
        6) Retorna el JSON original con “expires_at” añadido.
        """
        saved_state, _ = await self.get_and_delete_state(self.CATALOG_KEY, incoming_state)
        if saved_state != incoming_state:
            raise InvalidDataException("State inválido o expirado para WhatsApp.")

        params = {
            "client_id":     settings.WHATSAPP_CLIENT_ID,
            "redirect_uri":  settings.OAUTH_CALLBACK_URL,
            "client_secret": settings.WHATSAPP_CLIENT_SECRET,
            "code":          code,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self.token_url, params=params)  # ✅ MIGRADO
                resp.raise_for_status()
                tk = resp.json()  # { "access_token": "...", "token_type": "bearer", "expires_in": 5184000 }
        except httpx.HTTPError as e:
            detail = ""
            try:
                detail = e.response.json().get("error", {}).get("message", "")
            except Exception:
                detail = str(e)
            raise WorkflowProcessingException(f"Error intercambiando código en WhatsApp: {detail}")

        # Calculamos expires_at a partir de “expires_in” (en segundos) :contentReference[oaicite:2]{index=2}
        expires_in = int(tk.get("expires_in", 0))
        expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()

        payload = {
            "user_id":       self.user_id,
            "provider":      self.CATALOG_KEY,
            "client_id":     settings.WHATSAPP_CLIENT_ID,
            "client_secret": settings.WHATSAPP_CLIENT_SECRET,
            "access_token":  tk.get("access_token"),
            "refresh_token": None,  # El token de Facebook para WhatsApp no ofrece refresh_token; se renueva manualmente en la consola :contentReference[oaicite:3]{index=3}
            "expires_at":    expires_at,
            "scopes":        self.scopes,
        }
        await self.upsert_credentials(self.CATALOG_KEY, payload)

        return {**tk, "expires_at": expires_at}

    async def refresh_credentials(self, creds_obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        Facebook no expide refresh_token para WhatsApp Cloud API (el token es de larga duración),
        por lo que no hay flujo de “grant_type=refresh_token” disponible. Devolvemos el mismo objeto.
        Si en el futuro se habilita refresh automático, aquí se implementaría:
          • Detectar expiración comparando expires_at con datetime.utcnow().
          • Hacer POST a TOKEN_URL con grant_type=refresh_token, refresh_token, client_id, client_secret.
          • Actualizar en BD con upsert_credentials().
        Actualmente simplemente retorna creds_obj tal cual :contentReference[oaicite:4]{index=4}.
        """
        return creds_obj
