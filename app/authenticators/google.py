# app/authenticators/google.py

import httpx
import logging
from urllib.parse import urlencode
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from app.authenticators.registry import register_authenticator
from app.authenticators.base_oauth_authenticator import BaseOAuthAuthenticator
from app.core.config import settings
from app.exceptions.api_exceptions import InvalidDataException, WorkflowProcessingException

logger = logging.getLogger(__name__)

@register_authenticator("oauth2", "google")
@register_authenticator("oauth2", "gmail")
class GoogleOAuthAuthenticator(BaseOAuthAuthenticator):
    """
    Maneja OAuth2 para Google, distinguiendo flavors como:
      • "gmail"    → scope gmail.send
      • "sheets"   → scope spreadsheets
      • "calendar" → scope calendar.events
      • "drive"    → scope drive
      • flavor=None (o desconocido) → scopes amplios
    Hereda de BaseOAuthAuthenticator para CSRF y persistencia de credenciales.
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
        - user_id: ID entero del usuario.
        - db: sesión asíncrona de SQLAlchemy.
        - auth_policy: Política de auth desde BD (requerida)
        - chat_id: ID del chat para credentials
        """
        super().__init__(user_id=user_id, db=db, service_id=auth_policy.get("service_id"), chat_id=chat_id)
        self.auth_policy = auth_policy
        
        # ✅ MIGRADO: Usar auth_policy exclusivamente
        self.scopes = auth_policy.get("scopes", [])
        self.auth_base_url = auth_policy.get("auth_url", "https://accounts.google.com/o/oauth2/v2/auth")
        self.token_url = "https://oauth2.googleapis.com/token"  # URL estándar de Google
        self.api_version = auth_policy.get("auth_config", {}).get("api_version", "v3")
        logger.info(f"Using auth_policy: {len(self.scopes)} scopes, API {self.api_version}")
        
        # Metadata adicional de la policy
        self.display_name = auth_policy.get("display_name", f"Google {auth_policy.get('service', 'OAuth')}")
        self.provider = auth_policy.get("provider", "google")
        self.service = auth_policy.get("service")
        self.service_id = auth_policy.get("service_id")

    async def authorization_url(self) -> str:
        """
        1) Genera y guarda un 'state' único para protección CSRF.
        2) Construye la URL de autorización de Google con los scopes de this.flavor.
        3) 🆕 USA CREDENCIALES HÍBRIDAS: OAuth app del usuario o sistema.
        """
        state = await self.save_state(self.provider)
        
        # 🆕 NUEVO: Obtener credenciales OAuth híbridas
        oauth_creds = await self.get_oauth_credentials()
        client_id = oauth_creds["client_id"]

        params = {
            "client_id":     client_id,  # ✅ Híbrido: usuario o sistema
            "redirect_uri":  settings.OAUTH_CALLBACK_URL,
            "response_type": "code",
            "scope":         " ".join(self.scopes),
            "state":         state,
            "access_type":   "offline",
            "prompt":        "consent",
        }
        query = urlencode(params)
        return f"{self.auth_base_url}?{query}"

    async def fetch_token(self, code: str, incoming_state: str) -> Dict[str, Any]:
        """
        1) Verifica y elimina el 'state' guardado.
        2) Intercambia el 'code' por tokens en Google.
        3) 🆕 USA CREDENCIALES HÍBRIDAS para token exchange.
        4) Calcula expires_at y persiste credenciales con payload que incluye flavor.
        5) Retorna {access_token, refresh_token, expires_at, scopes}.
        """
        # If state is None, it means it was already validated by the OAuth router
        if incoming_state is not None:
            saved_state, _ = await self.get_and_delete_state(self.provider, incoming_state)
            if saved_state != incoming_state:
                raise InvalidDataException("State inválido o expirado para Google.")

        # 🆕 NUEVO: Obtener credenciales OAuth híbridas
        oauth_creds = await self.get_oauth_credentials()
        client_id = oauth_creds["client_id"]
        client_secret = oauth_creds["client_secret"]

        data = {
            "code":          code,
            "client_id":     client_id,     # ✅ Híbrido: usuario o sistema
            "client_secret": client_secret, # ✅ Híbrido: usuario o sistema
            "redirect_uri":  settings.OAUTH_CALLBACK_URL,
            "grant_type":    "authorization_code",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self.token_url, data=data)
                resp.raise_for_status()
                tk = resp.json()
        except httpx.HTTPError as e:
            raise WorkflowProcessingException(f"Error fetch_token Google: {e}")

        # Reconstruir Credentials para calcular expiry y refresh
        creds = Credentials(
            token=tk["access_token"],
            refresh_token=tk.get("refresh_token"),
            token_uri=self.token_url,
            client_id=client_id,     # ✅ Usa credenciales híbridas
            client_secret=client_secret, # ✅ Usa credenciales híbridas
            scopes=self.scopes
        )

        expires_at = creds.expiry.isoformat() if creds.expiry else None

        payload = {
            "user_id":       self.user_id,
            "chat_id":       None,  # 🌍 GLOBAL: Always save as global credentials
            "service_id":    self.service_id,
            "provider":      self.provider,
            "client_id":     client_id,     # ✅ GUARDAMOS las credenciales usadas
            "client_secret": client_secret, # ✅ GUARDAMOS las credenciales usadas (se encripta automáticamente)
            "access_token":  creds.token,
            "refresh_token": creds.refresh_token,
            "expires_at":    expires_at,
            "scopes":        self.scopes,
        }
        
        logger.info(f"🎯 GOOGLE: About to call upsert_credentials...")
        await self.upsert_credentials(self.provider, payload)
        logger.info(f"🎯 GOOGLE: upsert_credentials completed successfully")

        logger.info(f"🎯 GOOGLE: Preparing return data...")
        result = {
            "access_token":  creds.token,
            "refresh_token": creds.refresh_token,
            "expires_at":    expires_at,
            "scopes":        self.scopes
        }
        logger.info(f"🎯 GOOGLE: fetch_token completed successfully")
        return result

    async def refresh_credentials(self, creds_obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        1) Verifica si 'expires_at' ha pasado y hay 'refresh_token'.
        2) Si expiró, reconstruye Credentials con valores previos y solicita refresh.
        3) 🆕 USA CREDENCIALES HÍBRIDAS para refresh token.
        4) Actualiza BD con nuevos tokens y retorna {access_token, refresh_token, expires_at, scopes}.
        5) Si no expiró o no hay refresh_token, retorna creds_obj tal cual.
        """
        exp_str = creds_obj.get("expires_at")
        if exp_str:
            try:
                exp = datetime.fromisoformat(exp_str)
            except Exception:
                return creds_obj

            if exp <= datetime.utcnow() and creds_obj.get("refresh_token"):
                # 🆕 NUEVO: Usar client_id/secret de las credenciales almacenadas si existen
                # Fallback a credenciales híbridas si no están en las credenciales actuales
                client_id = creds_obj.get("client_id")
                client_secret = creds_obj.get("client_secret")
                
                if not client_id or not client_secret:
                    # Fallback a credenciales híbridas
                    oauth_creds = await self.get_oauth_credentials()
                    client_id = oauth_creds["client_id"]
                    client_secret = oauth_creds["client_secret"]
                
                # Reconstruir Credentials usando las credenciales correctas
                creds = Credentials(
                    token=creds_obj["access_token"],
                    refresh_token=creds_obj["refresh_token"],
                    token_uri=self.token_url,
                    client_id=client_id,     # ✅ Híbridas o almacenadas
                    client_secret=client_secret, # ✅ Híbridas o almacenadas
                    scopes=self.scopes
                )
                try:
                    creds.refresh(Request())
                except Exception as e:
                    raise WorkflowProcessingException(f"Error refrescando token Google: {e}")

                new_access = creds.token
                new_refresh = creds.refresh_token
                new_expires = creds.expiry.isoformat() if creds.expiry else None

                payload = {
                    "user_id":       self.user_id,
                    "chat_id":       None,  # 🌍 GLOBAL: Always save as global credentials
                    "service_id":    self.service_id,
                    "provider":      self.provider,
                    "client_id":     client_id,     # ✅ GUARDAMOS las credenciales usadas
                    "client_secret": client_secret, # ✅ GUARDAMOS las credenciales usadas (se encripta automáticamente)
                    "access_token":  new_access,
                    "refresh_token": new_refresh,
                    "expires_at":    new_expires,
                    "scopes":        self.scopes,
                }
                await self.upsert_credentials(self.provider, payload)

                return {
                    "access_token":  new_access,
                    "refresh_token": new_refresh,
                    "expires_at":    new_expires,
                    "scopes":        self.scopes
                }

        return creds_obj
