# app/authenticators/hubspot.py

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

@register_authenticator("oauth2", "hubspot")
class HubSpotOAuthAuthenticator(BaseOAuthAuthenticator):
    """
    Implementa el flujo OAuth2 para HubSpot:
    - save_state() / get_and_delete_state() para CSRF
    - upsert_credentials() para guardar/actualizar tokens
    """
    CATALOG_KEY = "hubspot"
    # ❌ ELIMINADO: URLs y scopes hardcodeados
    # ✅ AHORA: Todo viene de auth_policy desde BD

    def __init__(
        self,
        user_id: int,
        db: AsyncSession,
        auth_policy: Dict[str, Any],
        chat_id: Optional[str] = None
    ):
        """
        ✅ MIGRADO: Constructor que usa auth_policy
        """
        super().__init__(user_id=user_id, db=db)
        self.auth_policy = auth_policy
        self.chat_id = chat_id
        
        # ✅ MIGRADO: Usar scopes híbridos (usuario o sistema)
        self.available_scopes = auth_policy.get("scopes", [])  # ✅ FIX: Usar 'scopes' no 'max_scopes'
        self.authorize_url = auth_policy.get("auth_url", "https://app.hubspot.com/oauth-bridge")  # ✅ FIX: URL correcta
        self.token_url = "https://api.hubapi.com/oauth/v1/token"
        self.api_version = auth_policy.get("auth_config", {}).get("api_version", "v1")
        logger.info(f"Using auth_policy: {len(self.available_scopes)} available scopes, API {self.api_version}")
        
        # Metadata adicional de la policy
        self.display_name = auth_policy.get("display_name", "HubSpot OAuth")
        self.provider = auth_policy.get("provider", "hubspot")
        self.service = auth_policy.get("service")
        self.service_id = auth_policy.get("service_id")

    async def authorization_url(self) -> str:
        """
        1) Genera y guarda un 'state' (save_state).
        2) Construye la URL de autorización de HubSpot con client_id, redirect_uri, scopes y state.
        3) 🆕 USA CREDENCIALES HÍBRIDAS: OAuth app del usuario o sistema.
        """
        state = await self.save_state(self.CATALOG_KEY)

        # 🆕 NUEVO: Obtener credenciales OAuth híbridas con scopes
        oauth_creds = await self.get_oauth_credentials()
        client_id = oauth_creds["client_id"]
        
        # 🔥 FIX: Usar scopes híbridos (usuario > auth_policy > fallback)
        user_scopes = oauth_creds.get("scopes")
        if not user_scopes or user_scopes == ["oauth"]:
            # Fallback a scopes de auth_policy (usar 'scopes' no 'max_scopes')
            user_scopes = self.available_scopes or ["oauth"]
            logger.info(f"🔄 Using auth_policy scopes: {user_scopes}")
        else:
            logger.info(f"🔧 Using user-configured scopes: {user_scopes}")
        
        params = {
            "client_id":    client_id,  # ✅ Híbrido: usuario o sistema
            "redirect_uri": settings.OAUTH_CALLBACK_URL,
            "scope":        " ".join(user_scopes),  # ✅ SCOPES DEL USUARIO
            "state":        state,
            "response_type": "code",
        }
        query = urlencode(params)
        return f"{self.authorize_url}?{query}"  # ✅ MIGRADO

    async def fetch_token(self, code: str, incoming_state: str) -> Dict[str, Any]:
        """
        1) Valida y elimina el 'state' guardado (get_and_delete_state).
        2) Intercambia el 'code' por access_token y refresh_token en HubSpot.
        3) 🆕 USA CREDENCIALES HÍBRIDAS para token exchange.
        4) Calcula expires_at y guarda en BD vía upsert_credentials().
        5) Retorna el JSON original con un campo 'expires_at' añadido.
        """
        saved_state, _ = await self.get_and_delete_state(self.CATALOG_KEY, incoming_state)
        if saved_state != incoming_state:
            raise InvalidDataException("State inválido o expirado para HubSpot.")

        # 🆕 NUEVO: Obtener credenciales OAuth híbridas
        oauth_creds = await self.get_oauth_credentials()
        client_id = oauth_creds["client_id"]
        client_secret = oauth_creds["client_secret"]

        data = {
            "grant_type":    "authorization_code",
            "client_id":     client_id,     # ✅ Híbrido: usuario o sistema
            "client_secret": client_secret, # ✅ Híbrido: usuario o sistema
            "redirect_uri":  settings.OAUTH_CALLBACK_URL,
            "code":          code,
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self.token_url, data=data, headers=headers)  # ✅ MIGRADO
                resp.raise_for_status()
                tk = resp.json()
        except httpx.HTTPError as e:
            raise WorkflowProcessingException(f"Error intercambiando código por token en HubSpot: {e}")

        # Calculamos expires_at a partir de "expires_in" en segundos
        expires_in = int(tk.get("expires_in", 0))
        expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()

        payload = {
            "user_id":       self.user_id,
            "provider":      self.CATALOG_KEY,
            "client_id":     client_id,     # ✅ GUARDAMOS las credenciales usadas
            "client_secret": client_secret, # ✅ GUARDAMOS las credenciales usadas (se encripta automáticamente)
            "access_token":  tk.get("access_token"),
            "refresh_token": tk.get("refresh_token"),
            "expires_at":    expires_at,
            "scopes":        [],  # HubSpot: Los scopes los maneja la Developer App del usuario
        }
        await self.upsert_credentials(self.CATALOG_KEY, payload)

        return {**tk, "expires_at": expires_at}

    async def refresh_credentials(self, creds_obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        1) Verifica si 'expires_at' ya pasó y existe 'refresh_token'.
        2) Si expiró, intercambia refresh_token por nuevos tokens.
        3) Actualiza BD vía upsert_credentials() y devuelve el nuevo JSON con 'expires_at'.
        """
        exp_str = creds_obj.get("expires_at")
        if not exp_str:
            return creds_obj

        exp = datetime.fromisoformat(exp_str)
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
            
            data = {
                "grant_type":    "refresh_token",
                "refresh_token": creds_obj["refresh_token"],
                "client_id":     client_id,     # ✅ Híbridas o almacenadas
                "client_secret": client_secret, # ✅ Híbridas o almacenadas
            }
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(self.token_url, data=data, headers=headers)  # ✅ MIGRADO
                    resp.raise_for_status()
                    tk = resp.json()
            except httpx.HTTPError as e:
                raise WorkflowProcessingException(f"Error refrescando token de HubSpot: {e}")

            new_expires_in = int(tk.get("expires_in", 0))
            new_expires = (datetime.utcnow() + timedelta(seconds=new_expires_in)).isoformat()

            payload = {
                "user_id":       self.user_id,
                "provider":      self.CATALOG_KEY,
                "client_id":     client_id,     # ✅ GUARDAMOS las credenciales usadas
                "client_secret": client_secret, # ✅ GUARDAMOS las credenciales usadas (se encripta automáticamente)
                "access_token":  tk.get("access_token"),
                # Si la respuesta no trae nuevo refresh_token, mantenemos el anterior
                "refresh_token": tk.get("refresh_token", creds_obj["refresh_token"]),
                "expires_at":    new_expires,
                "scopes":        [],  # HubSpot: Los scopes los maneja la Developer App del usuario
            }
            await self.upsert_credentials(self.CATALOG_KEY, payload)
            return {**tk, "expires_at": new_expires}

        # Si no expira aún o no hay refresh_token, devolvemos el mismo objeto
        return creds_obj
