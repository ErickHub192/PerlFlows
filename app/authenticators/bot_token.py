# app/authenticators/bot_token.py

from typing import Dict, Any, Optional
from app.authenticators.registry import register_authenticator
from app.authenticators.base_oauth_authenticator import BaseOAuthAuthenticator
from app.exceptions.api_exceptions import InvalidDataException, WorkflowProcessingException

@register_authenticator("bot_token", "telegram")
@register_authenticator("bot_token", "slack")
class BotTokenAuthenticator(BaseOAuthAuthenticator):
    """
    Autenticador para servicios que usan un Bot Token (p.ej. Telegram bots).
    Hereda save_state/get_and_delete_state/upsert_credentials de la base,
    aunque no necesita CSRF ni scopes. 
      • fetch_token recibe directamente el bot_token.
      • Guarda el token en la tabla credentials (cifrado en repositorio).
      • refresh_credentials no hace nada (no hay refresh para bot tokens).
    """

    CATALOG_KEY = "bot_token"

    def __init__(self, user_id: int, db, auth_policy: Dict[str, Any]):
        """
        BaseOAuthAuthenticator ya inicializa state_repo y cred_repo.
        ✅ MIGRADO: Usa auth_policy exclusivamente
        """
        super().__init__(user_id=user_id, db=db, service_id=auth_policy.get("service_id"))
        self.auth_policy = auth_policy
        self.service_id = auth_policy.get("service_id")
        self.provider = auth_policy.get("provider", "bot_token")

    async def authorization_url(self) -> str:
        """
        No aplica para Bot Token: no hay URL de autorización.
        Retornamos cadena vacía.
        """
        return ""

    async def fetch_token(self, bot_token: str, state: str = None) -> Dict[str, Any]:
        """
        'bot_token' es la clave que el usuario ingresa para autenticar al bot.
        Guardamos ese valor crudo (el repositorio cifrará el campo access_token).
        Retornamos un diccionario con {"bot_token": <valor>} para que el servicio lo use.
        """
        if not bot_token or not bot_token.strip():
            raise InvalidDataException("Se requiere un Bot Token válido.")

        payload = {
            "user_id":       self.user_id,
            "provider":      self.provider,
            "service_id":    self.service_id,
            "access_token":  bot_token.strip(),  # se guarda cifrado
            "refresh_token": None,               # no aplica
            "expires_at":    None,               # no aplica
            "scopes":        None,               # no aplica
        }

        try:
            await self.upsert_credentials(self.CATALOG_KEY, payload)
        except Exception as e:
            raise WorkflowProcessingException(f"No se pudo guardar el Bot Token: {e}")

        return {"bot_token": bot_token.strip()}

    async def refresh_credentials(self, creds_obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        Para Bot Token no hay flujo de refresh. Retorna el mismo creds_obj sin cambios.
        """
        return creds_obj
