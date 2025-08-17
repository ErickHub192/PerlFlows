"""
ActionAuthRepository - Repositorio para verificación de auth por acción
"""
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models import ActionAuthScope, AuthPolicy, Action
from app.exceptions.api_exceptions import WorkflowProcessingException

logger = logging.getLogger(__name__)


class ActionAuthRepository:
    """
    Repositorio para consultas relacionadas con auth de acciones
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_action_auth_requirements(self, action_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene auth requirements completos para una acción
        
        Args:
            action_id: UUID de la acción
            
        Returns:
            Dict con datos de auth o None si no existe
        """
        try:
            query = select(ActionAuthScope).options(
                selectinload(ActionAuthScope.auth_policy),
                selectinload(ActionAuthScope.action)
            ).where(ActionAuthScope.action_id == action_id)
            
            result = await self.db.execute(query)
            action_auth = result.scalar_one_or_none()
            
            if not action_auth:
                return None
            
            policy = action_auth.auth_policy
            action = action_auth.action
            
            return {
                "action_id": str(action_auth.action_id),
                "action_name": action.name if action else "Unknown",
                "policy_id": policy.id,
                "mechanism": policy.mechanism,
                "provider": policy.provider,
                "service": policy.service,
                "required_scopes": action_auth.required_scopes,
                "max_scopes": policy.max_scopes or [],
                "auth_url": policy.base_auth_url,
                "auth_config": policy.auth_config or {},
                "display_name": policy.display_name,
                "description": policy.description,
                "auth_string": policy.auth_string
            }
            
        except Exception as e:
            logger.error(f"Error getting action auth requirements for {action_id}: {e}")
            return None
    
    async def get_multiple_action_auth_requirements(self, action_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Obtiene auth requirements para múltiples acciones de una vez
        
        Args:
            action_ids: Lista de UUIDs de acciones
            
        Returns:
            Dict con action_id -> auth_requirements
        """
        try:
            query = select(ActionAuthScope).options(
                selectinload(ActionAuthScope.auth_policy),
                selectinload(ActionAuthScope.action)
            ).where(ActionAuthScope.action_id.in_(action_ids))
            
            result = await self.db.execute(query)
            action_auths = result.scalars().all()
            
            requirements = {}
            for action_auth in action_auths:
                policy = action_auth.auth_policy
                action = action_auth.action
                
                requirements[str(action_auth.action_id)] = {
                    "action_id": str(action_auth.action_id),
                    "action_name": action.name if action else "Unknown",
                    "policy_id": policy.id,
                    "mechanism": policy.mechanism,
                    "provider": policy.provider,
                    "service": policy.service,
                    "required_scopes": action_auth.required_scopes,
                    "max_scopes": policy.max_scopes or [],
                    "auth_url": policy.base_auth_url,
                    "auth_config": policy.auth_config or {},
                    "display_name": policy.display_name,
                    "description": policy.description,
                    "auth_string": policy.auth_string
                }
            
            return requirements
            
        except Exception as e:
            logger.error(f"Error getting multiple action auth requirements: {e}")
            return {}
    
    async def get_actions_by_provider(self, provider: str, service: str = None) -> List[Dict[str, Any]]:
        """
        Obtiene todas las acciones que requieren auth de un provider específico
        
        Args:
            provider: Proveedor (google, dropbox, etc.)
            service: Servicio específico (opcional)
            
        Returns:
            Lista de acciones con sus auth requirements
        """
        try:
            query = select(ActionAuthScope).options(
                selectinload(ActionAuthScope.auth_policy),
                selectinload(ActionAuthScope.action)
            ).join(AuthPolicy).where(
                AuthPolicy.provider == provider,
                AuthPolicy.service == service if service else True,
                AuthPolicy.is_active == True
            )
            
            result = await self.db.execute(query)
            action_auths = result.scalars().all()
            
            actions = []
            for action_auth in action_auths:
                policy = action_auth.auth_policy
                action = action_auth.action
                
                actions.append({
                    "action_id": str(action_auth.action_id),
                    "action_name": action.name if action else "Unknown",
                    "required_scopes": action_auth.required_scopes,
                    "provider": policy.provider,
                    "service": policy.service,
                    "auth_string": policy.auth_string
                })
            
            return actions
            
        except Exception as e:
            logger.error(f"Error getting actions by provider {provider}/{service}: {e}")
            return []
    
    async def get_provider_scope_summary(self, provider: str, service: str = None) -> Dict[str, Any]:
        """
        Obtiene resumen de todos los scopes usados por un provider
        
        Args:
            provider: Proveedor (google, dropbox, etc.)
            service: Servicio específico (opcional)
            
        Returns:
            Dict con resumen de scopes
        """
        try:
            actions = await self.get_actions_by_provider(provider, service)
            
            if not actions:
                return {
                    "provider": provider,
                    "service": service,
                    "total_actions": 0,
                    "all_scopes": [],
                    "scope_usage": {}
                }
            
            # Recopilar todos los scopes únicos
            all_scopes = set()
            scope_usage = {}
            
            for action in actions:
                scopes = action["required_scopes"]
                all_scopes.update(scopes)
                
                for scope in scopes:
                    if scope not in scope_usage:
                        scope_usage[scope] = {
                            "count": 0,
                            "actions": []
                        }
                    scope_usage[scope]["count"] += 1
                    scope_usage[scope]["actions"].append({
                        "action_id": action["action_id"],
                        "action_name": action["action_name"]
                    })
            
            return {
                "provider": provider,
                "service": service,
                "total_actions": len(actions),
                "all_scopes": list(all_scopes),
                "scope_usage": scope_usage,
                "actions": actions
            }
            
        except Exception as e:
            logger.error(f"Error getting provider scope summary for {provider}/{service}: {e}")
            return {
                "provider": provider,
                "service": service,
                "total_actions": 0,
                "all_scopes": [],
                "scope_usage": {},
                "error": str(e)
            }