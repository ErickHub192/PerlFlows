"""
AuthPolicyRepository - Repositorio para manejo de políticas de autenticación
"""
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from app.db.models import AuthPolicy, ActionAuthScope, Action
from app.exceptions.api_exceptions import WorkflowProcessingException

logger = logging.getLogger(__name__)


class AuthPolicyRepository:
    """
    Repositorio para operaciones CRUD de auth policies
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_auth_string(self, auth_string: str) -> Optional[AuthPolicy]:
        """
        Obtiene policy por auth_string generado
        
        Args:
            auth_string: String de autenticación (ej: "oauth2_google_gmail")
            
        Returns:
            AuthPolicy o None si no existe
        """
        try:
            # 1. Búsqueda exacta primero
            query = select(AuthPolicy).where(
                AuthPolicy.auth_string == auth_string,
                AuthPolicy.is_active == True
            )
            result = await self.db.execute(query)
            policy = result.scalar_one_or_none()
            
            if policy:
                return policy
            
            # 2. Si no encuentra y parece ser formato legacy (mechanism_service), 
            #    intentar expandir a mechanism_provider_service dinámicamente
            parts = auth_string.split('_')
            if len(parts) == 2:
                mechanism, service = parts
                
                # Buscar qué providers tienen este service
                provider_query = select(AuthPolicy.provider).where(
                    AuthPolicy.service == service,
                    AuthPolicy.mechanism == mechanism,
                    AuthPolicy.is_active == True
                ).distinct()
                
                provider_result = await self.db.execute(provider_query)
                providers = [row[0] for row in provider_result.fetchall()]
                
                # Intentar mechanism_provider_service para cada provider encontrado
                for provider in providers:
                    expanded_auth_string = f"{mechanism}_{provider}_{service}"
                    logger.debug(f"Trying expanded auth_string: {auth_string} -> {expanded_auth_string}")
                    
                    expanded_query = select(AuthPolicy).where(
                        AuthPolicy.auth_string == expanded_auth_string,
                        AuthPolicy.is_active == True
                    )
                    expanded_result = await self.db.execute(expanded_query)
                    expanded_policy = expanded_result.scalar_one_or_none()
                    
                    if expanded_policy:
                        logger.debug(f"Found policy using expansion: {expanded_auth_string}")
                        return expanded_policy
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting auth policy by auth_string {auth_string}: {e}")
            return None
    
    async def get_by_service_id(self, service_id: str) -> Optional[AuthPolicy]:
        """
        Obtiene policy por service_id
        
        Args:
            service_id: ID del servicio (gmail, slack, etc.)
            
        Returns:
            AuthPolicy o None si no existe
        """
        try:
            # Primary query: buscar por service_id directo
            query = select(AuthPolicy).where(
                AuthPolicy.service_id == service_id,
                AuthPolicy.is_active == True
            )
            result = await self.db.execute(query)
            policy = result.scalar_one_or_none()
            
            if policy:
                return policy
            
            # Fallback 1: buscar por provider_service pattern
            # service_id puede ser "gmail", "google_gmail", etc.
            if "_" in service_id:
                # Si service_id es "google_gmail", separar en provider="google" y service="gmail"
                parts = service_id.split("_", 1)
                if len(parts) == 2:
                    provider, service = parts
                    provider_service_query = select(AuthPolicy).where(
                        AuthPolicy.provider == provider,
                        AuthPolicy.service == service,
                        AuthPolicy.is_active == True
                    )
                    provider_service_result = await self.db.execute(provider_service_query)
                    policy = provider_service_result.scalar_one_or_none()
                    if policy:
                        return policy
            else:
                # Si service_id es solo "gmail", buscar donde service="gmail"
                service_query = select(AuthPolicy).where(
                    AuthPolicy.service == service_id,
                    AuthPolicy.is_active == True
                )
                service_result = await self.db.execute(service_query)
                policy = service_result.scalar_one_or_none()
                if policy:
                    return policy
            
            # Fallback 2: buscar por auth_string para máxima compatibilidad
            # En caso de que service_id no esté poblado pero auth_string sí
            fallback_query = select(AuthPolicy).where(
                AuthPolicy.auth_string.like(f"%{service_id}"),
                AuthPolicy.is_active == True
            )
            fallback_result = await self.db.execute(fallback_query)
            return fallback_result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting auth policy by service_id {service_id}: {e}")
            return None
    
    async def get_by_provider_service(
        self, 
        provider: str, 
        service: str = None, 
        mechanism: str = "oauth2"
    ) -> Optional[AuthPolicy]:
        """
        Obtiene policy por provider/service/mechanism
        
        Args:
            provider: Proveedor (google, dropbox, etc.)
            service: Servicio específico (gmail, sheets, etc.)
            mechanism: Mecanismo de auth (oauth2, api_key, etc.)
            
        Returns:
            AuthPolicy o None si no existe
        """
        try:
            query = select(AuthPolicy).where(
                AuthPolicy.provider == provider,
                AuthPolicy.service == service,
                AuthPolicy.mechanism == mechanism,
                AuthPolicy.is_active == True
            )
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting auth policy for {provider}/{service}: {e}")
            return None
    
    async def get_all_active(self) -> List[AuthPolicy]:
        """
        Obtiene todas las políticas activas
        
        Returns:
            Lista de AuthPolicy
        """
        try:
            query = select(AuthPolicy).where(AuthPolicy.is_active == True)
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting all active auth policies: {e}")
            return []
    
    async def create(self, policy_data: Dict[str, Any]) -> AuthPolicy:
        """
        Crea nueva política de autenticación
        
        Args:
            policy_data: Datos de la política
            
        Returns:
            AuthPolicy creada
        """
        try:
            policy = AuthPolicy(
                provider=policy_data["provider"],
                service=policy_data.get("service"),
                mechanism=policy_data["mechanism"],
                base_auth_url=policy_data["base_auth_url"],
                max_scopes=policy_data.get("max_scopes"),
                auth_config=policy_data.get("auth_config"),
                display_name=policy_data.get("display_name"),
                description=policy_data.get("description"),
                icon_url=policy_data.get("icon_url")
            )
            
            self.db.add(policy)
            # ✅ Repository no maneja transacciones - solo flush
            await self.db.flush()
            await self.db.refresh(policy)
            
            return policy
            
        except Exception as e:
            logger.error(f"Error creating auth policy: {e}")
            raise
    
    async def update(self, policy_id: int, update_data: Dict[str, Any]) -> Optional[AuthPolicy]:
        """
        Actualiza política existente
        
        Args:
            policy_id: ID de la política
            update_data: Datos a actualizar
            
        Returns:
            AuthPolicy actualizada o None si no existe
        """
        try:
            query = update(AuthPolicy).where(
                AuthPolicy.id == policy_id
            ).values(**update_data).returning(AuthPolicy)
            
            result = await self.db.execute(query)
            # ✅ Repository no maneja transacciones - solo flush
            await self.db.flush()
            
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error updating auth policy: {e}")
            raise
    
    async def delete(self, policy_id: int) -> bool:
        """
        Elimina (desactiva) política
        
        Args:
            policy_id: ID de la política
            
        Returns:
            True si se eliminó correctamente
        """
        query = update(AuthPolicy).where(
            AuthPolicy.id == policy_id
        ).values(is_active=False)
        
        await self.db.execute(query)
        # ✅ Repository no maneja transacciones - solo flush
        await self.db.flush()
        
        return True


class ActionAuthScopeRepository:
    """
    Repositorio para operaciones CRUD de action auth scopes
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_action_id(self, action_id: str) -> Optional[ActionAuthScope]:
        """
        Obtiene auth scope por action_id
        
        Args:
            action_id: UUID de la acción
            
        Returns:
            ActionAuthScope o None si no existe
        """
        try:
            query = select(ActionAuthScope).options(
                selectinload(ActionAuthScope.auth_policy)
            ).where(ActionAuthScope.action_id == action_id)
            
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting action auth scope for {action_id}: {e}")
            return None
    
    async def get_by_policy_id(self, policy_id: int) -> List[ActionAuthScope]:
        """
        Obtiene todas las acciones que usan una política específica
        
        Args:
            policy_id: ID de la política
            
        Returns:
            Lista de ActionAuthScope
        """
        try:
            query = select(ActionAuthScope).options(
                selectinload(ActionAuthScope.action)
            ).where(ActionAuthScope.auth_policy_id == policy_id)
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting action auth scopes for policy {policy_id}: {e}")
            return []
    
    async def create(
        self, 
        action_id: str, 
        auth_policy_id: int, 
        required_scopes: List[str]
    ) -> ActionAuthScope:
        """
        Crea nuevo action auth scope
        
        Args:
            action_id: UUID de la acción
            auth_policy_id: ID de la política de auth
            required_scopes: Lista de scopes requeridos
            
        Returns:
            ActionAuthScope creado
        """
        try:
            action_auth = ActionAuthScope(
                action_id=action_id,
                auth_policy_id=auth_policy_id,
                required_scopes=required_scopes
            )
            
            self.db.add(action_auth)
            # ✅ Repository no maneja transacciones - solo flush
            await self.db.flush()
            await self.db.refresh(action_auth)
            
            return action_auth
            
        except Exception as e:
            logger.error(f"Error creating action auth scope: {e}")
            raise
    
    async def update_scopes(self, action_id: str, required_scopes: List[str]) -> Optional[ActionAuthScope]:
        """
        Actualiza scopes requeridos para una acción
        
        Args:
            action_id: UUID de la acción
            required_scopes: Nueva lista de scopes requeridos
            
        Returns:
            ActionAuthScope actualizado o None si no existe
        """
        try:
            query = update(ActionAuthScope).where(
                ActionAuthScope.action_id == action_id
            ).values(required_scopes=required_scopes).returning(ActionAuthScope)
            
            result = await self.db.execute(query)
            # ✅ Repository no maneja transacciones - solo flush
            await self.db.flush()
            
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error updating action auth scopes: {e}")
            raise
    
    async def delete_by_action_id(self, action_id: str) -> bool:
        """
        Elimina auth scope de una acción
        
        Args:
            action_id: UUID de la acción
            
        Returns:
            True si se eliminó correctamente
        """
        try:
            query = delete(ActionAuthScope).where(
                ActionAuthScope.action_id == action_id
            )
            
            await self.db.execute(query)
            # ✅ Repository no maneja transacciones - solo flush
            await self.db.flush()
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting action auth scope: {e}")
            raise