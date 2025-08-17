"""
AuthPolicyService - Servicio para manejo de políticas de autenticación dinámicas
Reemplaza hardcodeo de scopes con configuración basada en BD
"""
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.db.database import get_db
from app.repositories.auth_policy_repository import AuthPolicyRepository
from app.exceptions.api_exceptions import WorkflowProcessingException
from app.services.IAuthPolicyService import IAuthPolicyService

logger = logging.getLogger(__name__)


class AuthPolicyService(IAuthPolicyService):
    """
    Servicio para manejo de políticas de autenticación dinámicas
    """
    
    def __init__(
        self, 
        db: AsyncSession,
        auth_policy_repo: AuthPolicyRepository
    ):
        self.db = db
        self.auth_policy_repo = auth_policy_repo
    
    async def resolve_auth(self, auth_string: str) -> Optional[Dict[str, Any]]:
        """
        Resuelve auth_string a configuración completa desde BD
        Reemplaza parse_auth() + hardcodeo de scopes
        
        Args:
            auth_string: String de autenticación (ej: "oauth2_google_gmail")
            
        Returns:
            Dict con configuración completa o None si no existe
        """
        policy = await self.auth_policy_repo.get_by_auth_string(auth_string)
        
        if not policy:
            logger.debug(f"No auth policy found for: {auth_string}")
            return None
        
        return {
            "id": policy.id,
            "mechanism": policy.mechanism,
            "provider": policy.provider,
            "service": policy.service,
            "service_id": policy.service_id or f"{policy.provider}_{policy.service}" if policy.service else policy.provider,
            "scopes": policy.max_scopes or [],
            "auth_url": policy.base_auth_url,
            "auth_config": policy.auth_config or {},
            "display_name": policy.display_name,
            "description": policy.description,
            "icon_url": policy.icon_url,
            "auth_string": policy.auth_string
        }
    
    async def get_auth_policy_by_service_id(self, service_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene policy por service_id (nuevo approach agnostic)
        
        Args:
            service_id: ID del servicio (gmail, slack, etc.)
            
        Returns:
            Dict con configuración o None
        """
        policy = await self.auth_policy_repo.get_by_service_id(service_id)
        
        if not policy:
            logger.debug(f"No auth policy found for service_id: {service_id}")
            return None
        
        return {
            "id": policy.id,
            "mechanism": policy.mechanism,
            "provider": policy.provider,
            "service": policy.service,
            "service_id": policy.service_id or f"{policy.provider}_{policy.service}" if policy.service else policy.provider,
            "scopes": policy.max_scopes or [],
            "auth_url": policy.base_auth_url,
            "auth_config": policy.auth_config or {},
            "display_name": policy.display_name,
            "description": policy.description,
            "icon_url": policy.icon_url,
            "auth_string": policy.auth_string
        }
    
    async def get_auth_policy_by_provider(
        self, 
        provider: str, 
        mechanism: str,
        service: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene policy por provider/service/mechanism
        
        Args:
            provider: Proveedor (google, dropbox, etc.)
            mechanism: Mecanismo de auth (oauth2, api_key, bearer_token, etc.) - REQUERIDO
            service: Servicio específico (gmail, sheets, etc.) - opcional
            
        Returns:
            Dict con configuración o None
            
        Note:
            mechanism es requerido para evitar ambigüedad cuando un provider
            soporta múltiples mecanismos de autenticación
        """
        policy = await self.auth_policy_repo.get_by_provider_service(provider, service, mechanism)
        
        if not policy:
            return None
        
        return {
            "id": policy.id,
            "mechanism": policy.mechanism,
            "provider": policy.provider,
            "service": policy.service,
            "scopes": policy.max_scopes or [],
            "auth_url": policy.base_auth_url,
            "auth_config": policy.auth_config or {},
            "display_name": policy.display_name,
            "description": policy.description,
            "icon_url": policy.icon_url,
            "auth_string": policy.auth_string
        }
    
    # ✅ Métodos de conveniencia para casos comunes
    async def get_oauth2_policy(self, provider: str, service: str = None) -> Optional[Dict[str, Any]]:
        """
        Conveniencia para obtener política OAuth2
        
        Args:
            provider: Proveedor (google, dropbox, etc.)
            service: Servicio específico (opcional)
        """
        return await self.get_auth_policy_by_provider(provider, "oauth2", service)
    
    async def get_api_key_policy(self, provider: str, service: str = None) -> Optional[Dict[str, Any]]:
        """
        Conveniencia para obtener política API Key
        
        Args:
            provider: Proveedor (github, stripe, etc.)
            service: Servicio específico (opcional)
        """
        return await self.get_auth_policy_by_provider(provider, "api_key", service)
    
    async def get_bearer_token_policy(self, provider: str, service: str = None) -> Optional[Dict[str, Any]]:
        """
        Conveniencia para obtener política Bearer Token
        
        Args:
            provider: Proveedor
            service: Servicio específico (opcional)
        """
        return await self.get_auth_policy_by_provider(provider, "bearer_token", service)
    
    async def get_action_auth_requirements(self, action_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene auth requirements específicos para una acción usando actions.auth_policy_id
        
        Args:
            action_id: UUID de la acción
            
        Returns:
            Dict con policy + scopes requeridos o None
        """
        from sqlalchemy import select
        from app.db.models import Action, AuthPolicy
        
        # Query action with its auth_policy
        stmt = (
            select(Action, AuthPolicy)
            .join(AuthPolicy, Action.auth_policy_id == AuthPolicy.id, isouter=True)
            .where(Action.action_id == action_id)
        )
        
        result = await self.db.execute(stmt)
        row = result.first()
        
        if not row or not row[0].auth_required:
            logger.debug(f"No auth requirements found for action: {action_id}")
            return None
        
        action, policy = row
        
        if not policy:
            logger.warning(f"Action {action_id} requires auth but no auth_policy found")
            return None
        
        return {
            "action_id": str(action.action_id),
            "policy_id": policy.id,
            "mechanism": policy.mechanism,
            "provider": policy.provider,
            "service": policy.service,
            "service_id": policy.service_id or f"{policy.provider}_{policy.service}" if policy.service else policy.provider,
            "required_scopes": action.custom_scopes or policy.max_scopes or [],
            "max_scopes": policy.max_scopes or [],
            "auth_url": policy.base_auth_url,
            "auth_config": policy.auth_config or {},
            "display_name": policy.display_name,
            "description": policy.description,
            "auth_string": policy.auth_string,
            "auth_required": action.auth_required
        }
    
    async def create_auth_policy(self, policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea nueva política de autenticación
        ✅ Service maneja transacciones (movido desde repository)
        
        Args:
            policy_data: Datos de la política
            
        Returns:
            Dict con política creada
        """
        try:
            # ✅ Service maneja la transacción
            async with self.db.begin():
                policy = await self.auth_policy_repo.create(policy_data)
                
                return {
                    "id": policy.id,
                    "auth_string": policy.auth_string,
                    "provider": policy.provider,
                    "service": policy.service,
                    "mechanism": policy.mechanism,
                    "display_name": policy.display_name,
                    "created": True
                }
                
        except Exception as e:
            from app.exceptions.api_exceptions import WorkflowProcessingException
            raise WorkflowProcessingException(f"Error creando auth policy: {str(e)}")
    
    async def update_action_auth_requirements(
        self, 
        action_id: str, 
        auth_policy_id: int = None,
        auth_required: bool = None,
        custom_scopes: List[str] = None
    ) -> Dict[str, Any]:
        """
        Actualiza auth requirements de una acción usando columns directas
        
        Args:
            action_id: UUID de la acción
            auth_policy_id: ID de la política de auth (opcional)
            auth_required: Si requiere autenticación (opcional)
            custom_scopes: Scopes específicos para esta acción (opcional)
            
        Returns:
            Dict con resultado de la actualización
        """
        from sqlalchemy import update
        from app.db.models import Action
        
        try:
            # Build update dict with only provided values
            update_data = {}
            if auth_policy_id is not None:
                update_data["auth_policy_id"] = auth_policy_id
            if auth_required is not None:
                update_data["auth_required"] = auth_required
            if custom_scopes is not None:
                update_data["custom_scopes"] = custom_scopes
            
            if not update_data:
                raise WorkflowProcessingException("No update data provided")
            
            async with self.db.begin():
                stmt = (
                    update(Action)
                    .where(Action.action_id == action_id)
                    .values(**update_data)
                    .returning(Action)
                )
                
                result = await self.db.execute(stmt)
                updated_action = result.scalar_one_or_none()
                
                if not updated_action:
                    raise WorkflowProcessingException(f"Action not found: {action_id}")
                
                return {
                    "action_id": str(updated_action.action_id),
                    "auth_policy_id": updated_action.auth_policy_id,
                    "auth_required": updated_action.auth_required,
                    "custom_scopes": updated_action.custom_scopes,
                    "updated": True
                }
                
        except Exception as e:
            from app.exceptions.api_exceptions import WorkflowProcessingException
            if isinstance(e, WorkflowProcessingException):
                raise
            raise WorkflowProcessingException(f"Error updating action auth requirements: {str(e)}")
    
    async def get_all_active_policies(self) -> List[Dict[str, Any]]:
        """
        Obtiene todas las políticas activas para admin UI
        
        Returns:
            Lista de políticas
        """
        policies = await self.auth_policy_repo.get_all_active()
        
        return [
            {
                "id": policy.id,
                "auth_string": policy.auth_string,
                "provider": policy.provider,
                "service": policy.service,
                "mechanism": policy.mechanism,
                "display_name": policy.display_name,
                "description": policy.description,
                "max_scopes": policy.max_scopes,
                "base_auth_url": policy.base_auth_url,
                "is_active": policy.is_active
            }
            for policy in policies
        ]
    
    async def get_actions_by_policy(self, policy_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene todas las acciones que usan una política específica usando actions.auth_policy_id
        
        Args:
            policy_id: ID de la política
            
        Returns:
            Lista de acciones con sus scopes
        """
        from sqlalchemy import select
        from app.db.models import Action, Node
        
        stmt = (
            select(Action, Node)
            .join(Node, Action.node_id == Node.node_id, isouter=True)
            .where(Action.auth_policy_id == policy_id)
        )
        
        result = await self.db.execute(stmt)
        rows = result.all()
        
        return [
            {
                "action_id": str(action.action_id),
                "action_name": action.name,
                "node_name": node.name if node else "Unknown",
                "auth_required": action.auth_required,
                "custom_scopes": action.custom_scopes or [],
            }
            for action, node in rows
        ]
    
    async def fallback_parse_auth(self, auth_string: str) -> Dict[str, Any]:
        """
        Fallback para parsing cuando no hay policy en BD
        Mantiene compatibilidad con sistema anterior usando parsing básico
        
        Args:
            auth_string: String de autenticación
            
        Returns:
            Dict con información básica parseada
        """
        try:
            # ✅ MIGRADO: Usar parsing básico en lugar de parse_auth eliminado
            mechanism, provider, service = self._basic_parse_auth(auth_string)
            
            # Calcular service_id usando la misma lógica que en la línea 53
            service_id = f"{provider}_{service}" if service else provider
            
            return {
                "mechanism": mechanism,
                "provider": provider,
                "service": service,
                "service_id": service_id,  # ✅ AGREGADO: service_id faltante
                "scopes": [],  # Vacío en fallback
                "auth_url": f"/oauth/{provider}/authorize" if provider else "",
                "auth_config": {},
                "display_name": f"{provider.title()} {service.title()}" if service else provider.title(),
                "description": f"Legacy auth for {auth_string}",
                "auth_string": auth_string,
                "is_fallback": True
            }
            
        except Exception as e:
            logger.error(f"Error in fallback parse_auth for {auth_string}: {e}")
            return {
                "mechanism": "unknown",
                "provider": "unknown",
                "service": None,
                "service_id": "unknown",  # ✅ AGREGADO: service_id faltante
                "scopes": [],
                "auth_url": "",
                "auth_config": {},
                "display_name": "Unknown Auth",
                "description": f"Failed to parse {auth_string}",
                "auth_string": auth_string,
                "is_fallback": True
            }
    
    def _basic_parse_auth(self, auth_string: str) -> tuple:
        """
        Parsing básico para fallback (reemplaza parse_auth eliminado)
        """
        if not auth_string:
            return "unknown", "unknown", ""
        
        auth_string = auth_string.lower().strip()
        
        # Formato esperado: oauth2_provider_service
        if "_" in auth_string:
            parts = auth_string.split("_")
            if len(parts) >= 2:
                mechanism = parts[0]
                provider = parts[1]
                service = parts[2] if len(parts) > 2 else ""
                return mechanism, provider, service
        
        # Si no tiene underscore, asumir que es el provider
        return "oauth2", auth_string, ""

    async def create_action_auth_scope(
        self, 
        action_id: str, 
        policy_id: int, 
        required_scopes: List[str]
    ) -> Dict[str, Any]:
        """
        Crea scopes de autenticación para una acción.
        
        Args:
            action_id: UUID de la acción
            policy_id: ID de la política de auth
            required_scopes: Lista de scopes requeridos
            
        Returns:
            Dict con resultado de la creación
        """
        try:
            # Actualizar la acción con la política y scopes
            result = await self.update_action_auth_requirements(
                action_id=action_id,
                auth_policy_id=policy_id,
                auth_required=True,
                custom_scopes=required_scopes
            )
            
            return {
                "action_id": action_id,
                "policy_id": policy_id,
                "required_scopes": required_scopes,
                "created": True,
                **result
            }
            
        except Exception as e:
            from app.exceptions.api_exceptions import WorkflowProcessingException
            raise WorkflowProcessingException(f"Error creating action auth scope: {str(e)}")

    async def update_action_scopes(
        self, 
        action_id: str, 
        required_scopes: List[str]
    ) -> Dict[str, Any]:
        """
        Actualiza los scopes requeridos para una acción.
        
        Args:
            action_id: UUID de la acción
            required_scopes: Lista de scopes actualizados
            
        Returns:
            Dict con resultado de la actualización
        """
        try:
            # Actualizar solo los scopes de la acción
            result = await self.update_action_auth_requirements(
                action_id=action_id,
                custom_scopes=required_scopes
            )
            
            return {
                "action_id": action_id,
                "required_scopes": required_scopes,
                "updated": True,
                **result
            }
            
        except Exception as e:
            from app.exceptions.api_exceptions import WorkflowProcessingException
            raise WorkflowProcessingException(f"Error updating action scopes: {str(e)}")


# Factory para FastAPI DI
async def get_auth_policy_service(db: AsyncSession = Depends(get_db)) -> AuthPolicyService:
    """
    Factory para inyección de dependencias
    ✅ Inyecta repositorios en lugar de instanciación directa
    """
    auth_policy_repo = AuthPolicyRepository(db)
    return AuthPolicyService(db, auth_policy_repo)