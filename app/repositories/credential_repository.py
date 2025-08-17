# app/repositories/credential_repository.py

import time
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy import select, update, delete, insert
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.db.models import Credential
from app.exceptions.api_exceptions import WorkflowProcessingException
from app.db.database import get_db
from app.utils.crypto_utils import encrypt_bytes, decrypt_bytes  # Utilidades de cifrado


class CredentialRepository:
    """
    Repositorio de credenciales en tabla `credentials`, con cifrado de tokens.
    Usa service_id como identificador único de servicios (eliminando provider+flavor).
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_client_credentials(
        self,
        user_id: int,
        service_id: str,
        chat_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Devuelve config para un (user_id, service_id).
        NOTA: client_id y client_secret ahora están en el campo config (JSONB).
        """
        stmt = (
            select(Credential.config)
            .where(
                Credential.user_id == user_id,
                Credential.service_id == service_id,
                Credential.chat_id == chat_id,
            )
        )
        res = await self.db.execute(stmt)
        row = res.first()
        return row[0] if row and row[0] else None

    async def get_credential(
        self,
        user_id: int,
        service_id: str,
        chat_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Recupera la fila de Credential filtrando por (user_id, service_id).
        Desencripta access_token y refresh_token antes de devolver.
        """
        stmt = select(Credential).where(
            Credential.user_id == user_id,
            Credential.service_id == service_id,
            Credential.chat_id == chat_id,
        )
        res = await self.db.execute(stmt)
        cred = res.scalar_one_or_none()
        if not cred:
            return None

        # Desencriptar tokens antes de devolver
        access_token = decrypt_bytes(cred.access_token) if cred.access_token else None
        refresh_token = decrypt_bytes(cred.refresh_token) if cred.refresh_token else None
        client_secret = decrypt_bytes(cred.client_secret) if cred.client_secret else None

        result = cred.__dict__.copy()
        result["access_token"] = access_token
        result["refresh_token"] = refresh_token
        result["client_secret"] = client_secret
        return result

    async def create_credential(
        self,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Inserta una nueva fila en credentials.
        Espera que data contenga keys:
          user_id, service_id, config (JSONB), access_token, refresh_token, 
          expires_at, scopes, etc.
        Cifra access_token y refresh_token antes de insertar.
        """
        try:
            # Cifrar tokens y client_secret si están presentes
            if data.get("access_token"):
                data["access_token"] = encrypt_bytes(data["access_token"].encode())
            if data.get("refresh_token"):
                data["refresh_token"] = encrypt_bytes(data["refresh_token"].encode())
            if data.get("client_secret"):
                data["client_secret"] = encrypt_bytes(data["client_secret"].encode())

            stmt = insert(Credential).values(**data).returning(Credential)
            res = await self.db.execute(stmt)
            # ✅ Repository no maneja transacciones - solo flush
            await self.db.flush()
            new = res.scalar_one()

            # Desencriptar para el dict de respuesta
            new_dict = new.__dict__.copy()
            new_dict["access_token"] = (
                decrypt_bytes(new.access_token) if new.access_token else None
            )
            new_dict["refresh_token"] = (
                decrypt_bytes(new.refresh_token) if new.refresh_token else None
            )
            new_dict["client_secret"] = (
                decrypt_bytes(new.client_secret) if new.client_secret else None
            )
            return new_dict
        except Exception as e:
            # ✅ Repository no maneja transacciones - las maneja el service
            # await self.db.rollback()  # Removido
            raise WorkflowProcessingException(f"Error creando credencial: {e}")

    async def update_credential(
        self,
        user_id: int,
        service_id: str,
        data: Dict[str, Any],
        chat_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Actualiza la fila existente para (user_id, service_id) con los nuevos datos.
        Cifra tokens si vienen en el diccionario de datos.
        """
        try:
            # Cifrar tokens y client_secret si están presentes en data
            if data.get("access_token"):
                data["access_token"] = encrypt_bytes(data["access_token"].encode())
            if data.get("refresh_token"):
                data["refresh_token"] = encrypt_bytes(data["refresh_token"].encode())
            if data.get("client_secret"):
                data["client_secret"] = encrypt_bytes(data["client_secret"].encode())

            stmt = (
                update(Credential)
                .where(
                    Credential.user_id == user_id,
                    Credential.service_id == service_id,
                    Credential.chat_id == chat_id,
                )
                .values(**data)
                .returning(Credential)
            )
            res = await self.db.execute(stmt)
            # ✅ Repository no maneja transacciones - solo flush
            await self.db.flush()
            updated = res.scalar_one()

            # Desencriptar antes de devolver
            updated_dict = updated.__dict__.copy()
            updated_dict["access_token"] = (
                decrypt_bytes(updated.access_token) if updated.access_token else None
            )
            updated_dict["refresh_token"] = (
                decrypt_bytes(updated.refresh_token) if updated.refresh_token else None
            )
            updated_dict["client_secret"] = (
                decrypt_bytes(updated.client_secret) if updated.client_secret else None
            )
            return updated_dict
        except Exception as e:
            # ✅ Repository no maneja transacciones - las maneja el service
            # await self.db.rollback()  # Removido
            raise WorkflowProcessingException(f"Error actualizando credencial: {e}")

    async def delete_credential(
        self,
        user_id: int,
        service_id: str,
        chat_id: Optional[str] = None,
    ) -> None:
        """
        Elimina la fila de Credential para (user_id, service_id).
        """
        try:
            stmt = delete(Credential).where(
                Credential.user_id == user_id,
                Credential.service_id == service_id,
                Credential.chat_id == chat_id,
            )
            await self.db.execute(stmt)
            # ✅ Repository no maneja transacciones - solo flush
            await self.db.flush()
        except Exception as e:
            # ✅ Repository no maneja transacciones - las maneja el service
            # await self.db.rollback()  # Removido
            raise WorkflowProcessingException(f"Error eliminando credencial: {e}")

    async def list_by_owner(
        self,
        owner_id: int,
        chat_id: UUID,
    ) -> List[Dict[str, Any]]:
        """Lista credenciales de un usuario para un chat."""
        stmt = select(Credential).where(
            Credential.user_id == owner_id,
            Credential.chat_id == chat_id,
        )
        res = await self.db.execute(stmt)
        creds = res.scalars().all()

        result: List[Dict[str, Any]] = []
        for c in creds:
            access_token = decrypt_bytes(c.access_token) if c.access_token else None
            refresh_token = decrypt_bytes(c.refresh_token) if c.refresh_token else None
            client_secret = decrypt_bytes(c.client_secret) if c.client_secret else None
            c_dict = c.__dict__.copy()
            c_dict["access_token"] = access_token
            c_dict["refresh_token"] = refresh_token
            c_dict["client_secret"] = client_secret
            result.append(c_dict)

        return result

    async def list_credentials(
        self,
        user_id: int,
        chat_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Devuelve todas las credenciales del usuario, desencriptando tokens.
        El resultado incluirá provider y flavor para cada fila.
        """
        stmt = select(Credential).where(
            Credential.user_id == user_id,
            Credential.chat_id == chat_id,
        )
        res = await self.db.execute(stmt)
        creds = res.scalars().all()

        result_list: List[Dict[str, Any]] = []
        for c in creds:
            access_token = decrypt_bytes(c.access_token) if c.access_token else None
            refresh_token = decrypt_bytes(c.refresh_token) if c.refresh_token else None
            client_secret = decrypt_bytes(c.client_secret) if c.client_secret else None
            c_dict = c.__dict__.copy()
            c_dict["access_token"] = access_token
            c_dict["refresh_token"] = refresh_token
            c_dict["client_secret"] = client_secret
            result_list.append(c_dict)

        return result_list

    # ==================== OAUTH CREDENTIALS MANAGEMENT ====================
    # ✅ UNIFICADO: Usa la infraestructura OAuth existente para todo
    
    async def save_oauth_credentials(
        self,
        user_id: int,
        provider: str,
        client_id: str,
        client_secret: str,
        app_name: str = None,
    ) -> Dict[str, Any]:
        """
        ✅ SIMPLIFICADO: Guarda credenciales OAuth usando la infraestructura existente
        Reemplaza todo el sistema OAuthApp con el sistema OAuth normal
        """
        # ✅ LÓGICA DE NEGOCIO: Mapeo dinámico de provider -> service_id y provider real
        from app.services.auth_policy_service import AuthPolicyService
        from app.repositories.auth_policy_repository import AuthPolicyRepository
        
        auth_policy_repo = AuthPolicyRepository(self.db)
        auth_policy_service = AuthPolicyService(self.db, auth_policy_repo)
        
        # Buscar auth policy para el service_id (gmail, sheets, etc.)
        auth_policy = await auth_policy_service.get_auth_policy_by_service_id(provider)
        if not auth_policy:
            # Fallback: buscar por provider (google, microsoft, etc.)
            auth_policy = await auth_policy_service.get_auth_policy_by_provider(provider)
        
        if not auth_policy:
            # Si no existe, usar el provider como está (para compatibilidad)
            service_id = provider
            real_provider = provider
        else:
            # Usar configuración dinámica de la BD
            service_id = auth_policy.get("service_id", provider)
            real_provider = auth_policy.get("provider", provider)
        
        # Preparar configuración estándar
        config = {
            "app_name": app_name or f"{real_provider.title()} OAuth Credentials",
            "provider": real_provider,
            "user_configured": True,  # Indica que fueron configuradas por el usuario
        }
        
        # No encriptar aquí - se encripta en create_credential
        # encrypted_client_secret = encrypt_bytes(client_secret.encode()) if client_secret else None
        
        # Verificar si ya existe
        existing = await self.get_credential(user_id, service_id, chat_id=None)
        
        data = {
            "user_id": user_id,
            "service_id": service_id,
            "provider": real_provider,  # Usar provider real mapeado
            "client_id": client_id,
            "client_secret": client_secret,  # Se encripta en create_credential
            "config": config,
            "chat_id": None,  # Credenciales globales del usuario
            "access_token": None,  # Se llenan después del OAuth flow
            "refresh_token": None,
            "expires_at": None,
            "scopes": None,
        }
        
        if existing:
            # Actualizar credenciales existentes
            update_data = {k: v for k, v in data.items() if k not in ["user_id", "service_id", "chat_id"]}
            return await self.update_credential(user_id, service_id, update_data, chat_id=None)
        else:
            # Crear nuevas credenciales
            return await self.create_credential(data)
    
    async def list_user_oauth_credentials(self, user_id: int) -> List[Dict[str, Any]]:
        """
        ✅ SIMPLIFICADO: Lista credenciales OAuth configuradas por el usuario
        """
        # Buscar credenciales del usuario (globales)
        stmt = select(Credential).where(
            Credential.user_id == user_id,
            Credential.chat_id == None,  # Solo credenciales globales
        )
        
        res = await self.db.execute(stmt)
        credentials = res.scalars().all()
        
        result = []
        for cred in credentials:
            # Solo incluir credenciales que tienen client_id (OAuth credentials)
            if cred.client_id and cred.config and cred.config.get("user_configured"):
                cred_dict = {
                    "id": cred.id,
                    "provider": cred.provider,
                    "service_id": cred.service_id,
                    "client_id": cred.client_id,
                    "app_name": cred.config.get("app_name", f"{cred.provider.title()} Credentials"),
                    "created_at": cred.created_at,
                    "updated_at": cred.updated_at,
                }
                result.append(cred_dict)
        
        return result
    
    async def delete_oauth_credentials(self, user_id: int, provider: str) -> None:
        """
        ✅ SIMPLIFICADO: Elimina credenciales OAuth del usuario
        """
        # Obtener service_id usando la misma lógica que save_oauth_credentials
        from app.services.auth_policy_service import AuthPolicyService
        from app.repositories.auth_policy_repository import AuthPolicyRepository
        
        auth_policy_repo = AuthPolicyRepository(self.db)
        auth_policy_service = AuthPolicyService(self.db, auth_policy_repo)
        
        # Buscar auth policy para el service_id (gmail, sheets, etc.)
        auth_policy = await auth_policy_service.get_auth_policy_by_service_id(provider)
        if not auth_policy:
            # Fallback: buscar por provider (google, microsoft, etc.)
            auth_policy = await auth_policy_service.get_auth_policy_by_provider(provider)
        
        if not auth_policy:
            service_id = provider
        else:
            service_id = auth_policy.get("service_id", provider)
        
        await self.delete_credential(user_id, service_id, chat_id=None)


def get_credential_repository(
    db: AsyncSession = Depends(get_db)
) -> CredentialRepository:
    """
    Dependency provider para CredentialRepository.
    """
    return CredentialRepository(db)
