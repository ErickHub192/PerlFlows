# app/authenticators/base_oauth_authenticator.py

import secrets
import logging
from app.repositories.oauth_state_repository import OAuthStateRepository
from app.repositories.credential_repository import CredentialRepository
from app.exceptions.api_exceptions import WorkflowProcessingException

logger = logging.getLogger(__name__)

class BaseOAuthAuthenticator:
    def __init__(self, user_id: int, db, service_id: str = None, chat_id: str = None):
        self.user_id    = user_id
        self.service_id = service_id  # ✅ NUEVO: service_id agnóstico
        self.chat_id    = chat_id     # ✅ NUEVO: chat_id para credentials
        self.state_repo = OAuthStateRepository(db)
        self.cred_repo  = CredentialRepository(db)
        self.provider   = None  # Debe ser establecido por las subclases

    async def save_state(self, provider: str) -> str:
        state = secrets.token_urlsafe(16)
        await self.state_repo.save_oauth_state(self.user_id, provider, self.service_id, state, self.chat_id)
        return state

    async def get_and_delete_state(self, provider: str, incoming: str):
        saved = await self.state_repo.get_oauth_state(self.user_id, provider, self.service_id)
        await self.state_repo.delete_oauth_state(self.user_id, provider, self.service_id)
        return saved, incoming

    async def upsert_credentials(self, provider: str, payload: dict):
        # 🌍 GLOBAL CREDENTIALS: Always save credentials as global (chat_id=None)
        # This allows credentials to work across all chats for better UX
        logger.info(f"🔧 UPSERT: Starting upsert_credentials for {provider}, user {self.user_id}, service {self.service_id}")
        
        existing = await self.cred_repo.get_credential(self.user_id, self.service_id, chat_id=None)
        logger.info(f"🔧 UPSERT: Existing credential found: {bool(existing)}")
        
        if existing:
            logger.info(f"🔧 UPSERT: Updating existing credential...")
            await self.cred_repo.update_credential(self.user_id, self.service_id, payload, chat_id=None)
            logger.info(f"🔧 UPSERT: Update completed successfully")
        else:
            logger.info(f"🔧 UPSERT: Creating new credential...")
            await self.cred_repo.create_credential(payload)
            logger.info(f"🔧 UPSERT: Create completed successfully")

    async def get_oauth_credentials(self) -> dict:
        """
        🆕 NUEVO: Obtiene credenciales OAuth híbridas (usuario o sistema).
        Primero intenta OAuth app del usuario, luego fallback a sistema.
        """
        if not self.provider:
            raise ValueError("Provider no establecido en el authenticator")
            
        try:
            # Primero intentar credenciales del usuario usando service_id
            user_creds = await self.cred_repo.get_credential(self.user_id, self.service_id, chat_id=None)
            if user_creds and user_creds.get("client_id") and user_creds.get("client_secret"):
                # 🔥 INCLUIR SCOPES desde config
                config = user_creds.get("config", {})
                scopes = config.get("scopes", ["oauth"])
                
                return {
                    "client_id": user_creds["client_id"],
                    "client_secret": user_creds["client_secret"],
                    "scopes": scopes  # ✅ SCOPES DEL USUARIO
                }
            
            # Fallback a credenciales del sistema (.env)
            from app.core.config import settings
            
            # Mapear provider a configuración del sistema
            provider_configs = {
                "google": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET
                },
                "github": {
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET
                },
                "microsoft": {
                    "client_id": settings.MICROSOFT_CLIENT_ID,
                    "client_secret": settings.MICROSOFT_CLIENT_SECRET
                },
                "slack": {
                    "client_id": settings.SLACK_CLIENT_ID,
                    "client_secret": settings.SLACK_CLIENT_SECRET
                },
                "salesforce": {
                    "client_id": settings.SALESFORCE_CLIENT_ID,
                    "client_secret": settings.SALESFORCE_CLIENT_SECRET
                },
                "dropbox": {
                    "client_id": settings.DROPBOX_CLIENT_ID,
                    "client_secret": settings.DROPBOX_CLIENT_SECRET
                },
                "hubspot": {
                    "client_id": settings.HUBSPOT_CLIENT_ID,
                    "client_secret": settings.HUBSPOT_CLIENT_SECRET
                }
            }
            
            config = provider_configs.get(self.provider)
            if not config or not config["client_id"] or not config["client_secret"]:
                raise ValueError(f"No se encontraron credenciales para {self.provider}")
            
            # ❌ REMOVIDO: No usar scopes hardcodeados del sistema
            # Los scopes deben venir de auth_policy o base de datos
            return config
            
        except Exception as e:
            raise WorkflowProcessingException(f"No se pudieron obtener credenciales OAuth para {self.provider}: {e}")

    def _get_default_system_scopes(self) -> list:
        """❌ DEPRECATED: Scopes deben venir de auth_policy, no hardcodeados"""
        logger.warning("⚠️ _get_default_system_scopes is deprecated. Use auth_policy scopes instead.")
        return []

    async def refresh_credentials(self, creds_obj: dict) -> dict:
        """
        Hook que debe implementar cada autenticador concreto para refrescar tokens.
        Recibe un diccionario con las credenciales actuales (decrypted),
        y retorna un diccionario con los valores actualizados:
          {
            "access_token": ...,
            "refresh_token": ...,
            "expires_at": ...,
            "scopes": [...]
          }
        """
        raise NotImplementedError("refresh_credentials debe implementarse en el autenticador concreto.")
