from abc import ABC, abstractmethod
from typing import Any
from app.repositories.oauth_state_repository import OAuthStateRepository
from app.repositories.credential_repository import CredentialRepository

class BaseOAuthAuthenticator(ABC):
    def __init__(self, user_id: int, db):
        self.user_id    = user_id
        self.state_repo = OAuthStateRepository(db)
        self.cred_repo  = CredentialRepository(db)

    @abstractmethod
    async def authorization_url(self) -> str:
        """Construye la URL de autorización."""
        ...

    @abstractmethod
    async def fetch_token(self, code: str, state: str):
        """Intercambia code→tokens y persiste credenciales."""
        ...

    @abstractmethod
    async def refresh_credentials(self, creds_obj: Any):
        """Refresca el token si está expirado."""
        ...

    async def save_state(self, provider: str) -> str:
        ...

    async def get_and_delete_state(self, provider: str, incoming: str):
        ...

    async def upsert_credentials(self, provider: str, payload: dict):
        ...

