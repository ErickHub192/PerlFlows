# app/authenticators/api_key.py

from typing import Dict, Any, Optional
from app.authenticators.registry import register_authenticator
from app.authenticators.base_oauth_authenticator import BaseOAuthAuthenticator
from app.exceptions.api_exceptions import InvalidDataException, WorkflowProcessingException

@register_authenticator("api_key", "stripe")
@register_authenticator("api_key", "airtable")
@register_authenticator("api_key", "ai")
@register_authenticator("api_key", "sat")
@register_authenticator("api_key", "whatsapp")
class APIKeyAuthenticator(BaseOAuthAuthenticator):
    """
    Autenticador para servicios que solo usan API Key (p.ej. un header X-API-KEY).
    Hereda save_state/get_and_delete_state/upsert_credentials de la base,
    aunque no usa CSRF ni scopes. Básicamente:
      • fetch_token recibe directamente la clave.
      • Guarda el valor en la tabla credentials.
      • refresh_credentials no hace nada (no hay refresh en API Key).
    """

    CATALOG_KEY = "api_key"

    def __init__(self, user_id: int, db, auth_policy: Dict[str, Any]):
        """
        BaseOAuthAuthenticator ya inicializa state_repo y cred_repo.
        ✅ MIGRADO: Usa auth_policy exclusivamente
        """
        super().__init__(user_id=user_id, db=db, service_id=auth_policy.get("service_id"))
        self.auth_policy = auth_policy
        self.service_id = auth_policy.get("service_id")
        self.provider = auth_policy.get("provider", "api_key")

    async def authorization_url(self) -> str:
        """
        No aplica para API Key: simplemente no hay URL de autorización.
        Retornamos None o cadena vacía para indicar que no se redirige.
        """
        return ""

    async def fetch_token(self, api_key: str, state: str = None) -> Dict[str, Any]:
        """
        En este contexto, 'api_key' es la clave que el usuario ingresa.
        Guardamos ese valor crudo (el repositorio cifrará el campo access_token).
        Retornamos un dict con { "api_key": <valor> } para que el servicio lo use.
        """
        if not api_key or not api_key.strip():
            raise InvalidDataException("Se requiere una API Key válida.")

        payload = {
            "user_id":       self.user_id,
            "provider":      self.provider,
            "service_id":    self.service_id,
            "access_token":  api_key.strip(),
            "refresh_token": None,       # no aplica
            "expires_at":    None,       # no aplica
            "scopes":        None,       # no aplica
        }

        try:
            await self.upsert_credentials(self.CATALOG_KEY, payload)
        except Exception as e:
            raise WorkflowProcessingException(f"No se pudo guardar la API Key: {e}")

        return {"api_key": api_key.strip()}

    async def refresh_credentials(self, creds_obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        Para API Key no hay flujo de refresh. Devuelve el mismo creds_obj.
        """
        return creds_obj
