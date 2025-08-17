from typing import Optional, Dict, Any
import base64

from app.repositories.credential_repository import CredentialRepository
from app.utils.crypto_utils import encrypt_bytes

class SATCredentialService:
    """Guarda archivos de e‑firma en la tabla credentials."""

    def __init__(self, repo: CredentialRepository):
        self.repo = repo

    async def save_efirma(
        self,
        user_id: int,
        cer_bytes: bytes,
        key_bytes: bytes,
        password: str,
        chat_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = {
            "user_id": user_id,
            "provider": "sat",
            "client_id": "",
            "client_secret": "",
            "access_token": encrypt_bytes(key_bytes + password.encode()),
            "refresh_token": None,
            "expires_at": None,
            "scopes": None,
            "chat_id": chat_id,
            "config": {"cer": base64.b64encode(cer_bytes).decode()},
        }
        existing = await self.repo.get_credential(user_id, "sat", chat_id=chat_id)
        if existing:
            return await self.repo.update_credential(user_id, "sat", payload, chat_id=chat_id)
        return await self.repo.create_credential(payload)
