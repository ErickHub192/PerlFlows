# app/services/credential_service.py

from typing import Optional, Dict, Any, List
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.credential_repository import CredentialRepository, get_credential_repository
from app.db.database import get_db


class CredentialService:
    """
    Servicio para gestión de credenciales usando service_id únicamente.
    Elimina la lógica de provider+flavor y usa el nuevo esquema simplificado.
    """

    def __init__(self, repo: CredentialRepository):
        self.repo = repo

    async def get_credential(
        self,
        user_id: int,
        service_id: str,
        chat_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene credenciales para un servicio específico.
        Busca primero credenciales globales (chat_id=None) y luego específicas del chat.
        """
        # 🌍 PRIMERO: Buscar credenciales globales (las que guardan los authenticators)
        global_cred = await self.repo.get_credential(user_id, service_id, chat_id=None)
        if global_cred:
            return global_cred
            
        # 📍 SEGUNDO: Buscar credenciales específicas del chat (legacy)
        if chat_id:
            return await self.repo.get_credential(user_id, service_id, chat_id)
            
        return None

    async def get_service_config(
        self,
        user_id: int,
        service_id: str,
        chat_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Obtiene configuración (client_id, client_secret, etc.) para un servicio"""
        return await self.repo.get_client_credentials(user_id, service_id, chat_id)

    async def create_credential(
        self,
        user_id: int,
        service_id: str,
        data: Dict[str, Any],
        chat_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Crea una nueva credencial para un servicio.
        La data incluye tokens, configuración, etc.
        """
        credential_data = {
            "user_id": user_id,
            "service_id": service_id,
            "chat_id": chat_id,
            **data
        }
        return await self.repo.create_credential(credential_data)

    async def update_credential(
        self,
        user_id: int,
        service_id: str,
        data: Dict[str, Any],
        chat_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Actualiza credenciales existentes para un servicio"""
        return await self.repo.update_credential(user_id, service_id, data, chat_id)

    async def delete_credential(
        self,
        user_id: int,
        service_id: str,
        chat_id: Optional[str] = None,
    ) -> bool:
        """Elimina credenciales para un servicio"""
        await self.repo.delete_credential(user_id, service_id, chat_id)
        return True

    async def list_user_credentials(
        self,
        user_id: int,
        chat_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lista todas las credenciales de un usuario"""
        return await self.repo.list_by_owner(user_id, chat_id)

    async def has_credential(
        self,
        user_id: int,
        service_id: str,
        chat_id: Optional[str] = None,
    ) -> bool:
        """
        Verifica si el usuario tiene credenciales para un servicio.
        Usa la búsqueda híbrida (global primero, específico después).
        """
        credential = await self.get_credential(user_id, service_id, chat_id)
        return credential is not None

    async def get_credentials_by_services(
        self,
        user_id: int,
        service_ids: List[str],
        chat_id: Optional[str] = None,
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Obtiene credenciales para múltiples servicios de una vez.
        Retorna un dict: {service_id: credential_data}
        """
        result = {}
        for service_id in service_ids:
            credential = await self.get_credential(user_id, service_id, chat_id)
            result[service_id] = credential
        return result


def get_credential_service(
    repo: CredentialRepository = Depends(get_credential_repository)
) -> CredentialService:
    """Dependency injection para CredentialService"""
    return CredentialService(repo)