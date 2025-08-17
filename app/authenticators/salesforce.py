# app/authenticators/salesforce.py

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

@register_authenticator("oauth2", "salesforce")
class SalesforceOAuthAuthenticator(BaseOAuthAuthenticator):
    """
    Implementa el flujo OAuth2 para Salesforce mediante BaseOAuthAuthenticator:
    - save_state() / get_and_delete_state() para manejo de 'state'
    - upsert_credentials() para guardar/actualizar credenciales en la BD.

    Usa:
      • Authorization URL:  https://login.salesforce.com/services/oauth2/authorize
      • Token URL:          https://login.salesforce.com/services/oauth2/token
      • Scopes:             "api", "refresh_token"
      • Sandbox:            reemplazar login.salesforce.com por test.salesforce.com
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
        self.authorize_url = auth_policy.get("auth_url", "https://login.salesforce.com/services/oauth2/authorize")
        self.token_url = "https://login.salesforce.com/services/oauth2/token"
        self.api_version = auth_policy.get("auth_config", {}).get("api_version", "v59.0")
        logger.info(f"Using auth_policy: {len(self.scopes)} scopes, API {self.api_version}")
        
        # Metadata adicional de la policy
        self.display_name = auth_policy.get("display_name", "Salesforce OAuth")
        self.provider = auth_policy.get("provider", "salesforce")
        self.service = auth_policy.get("service")
        self.service_id = auth_policy.get("service_id")

    async def authorization_url(self) -> str:
        """
        1) Genera y guarda un 'state' (save_state) para protección CSRF.
        2) Construye la URL de autorización de Salesforce con:
           • client_id
           • redirect_uri
           • response_type=code
           • scope=api refresh_token
           • state
        3) Retorna la URL completa.
        """
        state = await self.save_state(self.provider)

        params = {
            "client_id":     settings.SALESFORCE_CLIENT_ID,
            "redirect_uri":  settings.OAUTH_CALLBACK_URL,
            "response_type": "code",
            "scope":         " ".join(self.scopes),  # ✅ MIGRADO
            "state":         state,
        }
        query = urlencode(params)
        return f"{self.authorize_url}?{query}"  # ✅ MIGRADO

    async def fetch_token(self, code: str, incoming_state: str) -> Dict[str, Any]:
        """
        1) Valida y elimina el 'state' con get_and_delete_state().
        2) Intercambia el 'code' por tokens en TOKEN_URL.
        3) Calcula 'expires_at' usando 'expires_in' devuelto (segundos).
        4) Guarda tokens en la BD (upsert_credentials).
        5) Retorna el JSON original enriquecido con 'expires_at' (ISO8601).
        """
        # If state is None, it means it was already validated by the OAuth router
        if incoming_state is not None:
            saved_state, _ = await self.get_and_delete_state(self.provider, incoming_state)
            if saved_state != incoming_state:
                raise InvalidDataException("State inválido o expirado para Salesforce.")

        data = {
            "grant_type":    "authorization_code",
            "code":          code,
            "client_id":     settings.SALESFORCE_CLIENT_ID,
            "client_secret": settings.SALESFORCE_CLIENT_SECRET,
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
                detail = e.response.json().get("error_description", "")
            except Exception:
                detail = str(e)
            raise WorkflowProcessingException(f"Error intercambiando código en Salesforce: {detail}")

        expires_in = int(tk.get("expires_in", 0))
        expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()

        payload = {
            "user_id":       self.user_id,
            "chat_id":       None,  # 🌍 GLOBAL: Always save as global credentials
            "service_id":    self.service_id,
            "provider":      self.provider,
            "client_id":     None,  # TODO: En el futuro permitir user-provided OAuth credentials
            "client_secret": None,  # TODO: Por ahora usamos settings.SALESFORCE_CLIENT_ID/SECRET del sistema
            "access_token":  tk.get("access_token"),
            "refresh_token": tk.get("refresh_token"),
            "expires_at":    expires_at,
            "scopes":        self.scopes,
        }
        await self.upsert_credentials(self.provider, payload)

        return {**tk, "expires_at": expires_at}

    async def refresh_credentials(self, creds_obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        1) Verifica si 'expires_at' ya pasó y existe 'refresh_token'.
        2) Si expiró, envía un POST a TOKEN_URL con:
           • grant_type = "refresh_token"
           • refresh_token
           • client_id, client_secret
        3) Calcula 'new_expires_at', guarda en BD (upsert_credentials).
        4) Retorna el JSON con nuevos tokens y 'expires_at'.
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
                "client_id":     settings.SALESFORCE_CLIENT_ID,
                "client_secret": settings.SALESFORCE_CLIENT_SECRET,
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
                    detail = e.response.json().get("error_description", "")
                except Exception:
                    detail = str(e)
                raise WorkflowProcessingException(f"Error refrescando token Salesforce: {detail}")

            new_expires_in = int(tk.get("expires_in", 0))
            new_expires = (datetime.utcnow() + timedelta(seconds=new_expires_in)).isoformat()

            payload = {
                "user_id":       self.user_id,
                "chat_id":       None,  # 🌍 GLOBAL: Always save as global credentials
                "service_id":    self.service_id,
                "provider":      self.provider,
                "client_id":     None,  # TODO: En el futuro permitir user-provided OAuth credentials
                "client_secret": None,  # TODO: Por ahora usamos settings.SALESFORCE_CLIENT_ID/SECRET del sistema
                "access_token":  tk.get("access_token"),
                "refresh_token": tk.get("refresh_token", creds_obj["refresh_token"]),
                "expires_at":    new_expires,
                "scopes":        self.scopes,  # ✅ MIGRADO
            }
            await self.upsert_credentials(self.provider, payload)
            return {**tk, "expires_at": new_expires}

        return creds_obj
