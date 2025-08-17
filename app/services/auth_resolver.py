"""
AuthResolver - ÚNICO punto centralizado para resolución de autenticación
Elimina parsing duplicado y centraliza auth logic
"""
import logging
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.db.database import get_db
from app.services.auth_policy_service import AuthPolicyService, get_auth_policy_service
# ❌ ELIMINADO: parse_auth ya no existe

logger = logging.getLogger(__name__)


class AuthPolicy:
    """
    Objeto unificado que representa una política de auth resuelta
    Puede incluir tanto policy general como scopes específicos por acción
    """
    def __init__(self, policy_data: Dict[str, Any]):
        self.mechanism = policy_data.get("mechanism", "")
        self.provider = policy_data.get("provider", "")
        self.service = policy_data.get("service")
        self.scopes = policy_data.get("scopes", [])
        self.max_scopes = policy_data.get("max_scopes", [])
        self.auth_url = policy_data.get("auth_url", "")
        self.auth_config = policy_data.get("auth_config", {})
        self.display_name = policy_data.get("display_name", "")
        self.description = policy_data.get("description", "")
        self.auth_string = policy_data.get("auth_string", "")
        self.is_fallback = policy_data.get("is_fallback", False)
        
        # ✅ NUEVO: Action-specific auth data
        self.action_id = policy_data.get("action_id")  # Si es específico para una acción
        self.required_scopes = policy_data.get("required_scopes", [])  # Scopes específicos de la acción
        self.policy_id = policy_data.get("policy_id")  # ID de la policy en BD
        
        # API version para discovery handlers
        self.api_version = self.auth_config.get("api_version", "v3")
    
    def requires_oauth(self) -> bool:
        """Determina si requiere OAuth"""
        return self.mechanism == "oauth2"
    
    def get_provider_key(self) -> str:
        """Clave única para este provider/service"""
        if self.service:
            return f"{self.provider}_{self.service}"
        return self.provider
    
    def get_effective_scopes(self) -> list:
        """
        Retorna scopes efectivos: required_scopes si existe, sino max_scopes
        """
        return self.required_scopes if self.required_scopes else self.scopes
    
    def is_action_specific(self) -> bool:
        """
        Determina si esta policy es específica para una acción
        """
        return self.action_id is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a dict para serialización"""
        return {
            "mechanism": self.mechanism,
            "provider": self.provider,
            "service": self.service,
            "scopes": self.scopes,
            "max_scopes": self.max_scopes,
            "auth_url": self.auth_url,
            "auth_config": self.auth_config,
            "display_name": self.display_name,
            "description": self.description,
            "auth_string": self.auth_string,
            "is_fallback": self.is_fallback,
            "api_version": self.api_version,
            # Action-specific data
            "action_id": self.action_id,
            "required_scopes": self.required_scopes,
            "policy_id": self.policy_id,
            "effective_scopes": self.get_effective_scopes()
        }


class CentralAuthResolver:
    """
    ÚNICO punto de resolución de auth en todo el sistema
    Elimina duplicación de parse_auth() en múltiples lugares
    """
    
    def __init__(self, auth_policy_service: AuthPolicyService):
        self.auth_policy_service = auth_policy_service
        self._cache = {}  # In-memory cache para sesión
        
    async def resolve_auth_once(self, auth_string: str) -> Optional[AuthPolicy]:
        """
        Resuelve auth_string UNA SOLA VEZ y cachea el resultado
        
        Args:
            auth_string: String de auth (ej: "oauth2_google_gmail")
            
        Returns:
            AuthPolicy objeto o None si no requiere auth
        """
        if not auth_string or auth_string.strip() == "":
            return None
            
        # Check cache primero
        if auth_string in self._cache:
            logger.debug(f"Auth cache HIT for: {auth_string}")
            return self._cache[auth_string]
        
        logger.debug(f"Resolving auth for: {auth_string}")
        
        # 1. Intentar obtener desde AuthPolicyService (BD)
        policy_data = await self.auth_policy_service.resolve_auth(auth_string)
        
        if policy_data:
            auth_policy = AuthPolicy(policy_data)
            self._cache[auth_string] = auth_policy
            logger.debug(f"Auth resolved from DB for: {auth_string}")
            return auth_policy
        
        # 2. Fallback a parsing manual (legacy compatibility)
        fallback_data = await self.auth_policy_service.fallback_parse_auth(auth_string)
        auth_policy = AuthPolicy(fallback_data)
        self._cache[auth_string] = auth_policy
        
        logger.warning(f"Auth resolved via fallback for: {auth_string}")
        return auth_policy
    
    async def resolve_action_auth(self, action_id: str) -> Optional[AuthPolicy]:
        """
        Resuelve auth requirements específicos para una acción
        Prioriza action_auth_scopes sobre auth general
        
        Args:
            action_id: UUID de la acción
            
        Returns:
            AuthPolicy específico para la acción o None
        """
        cache_key = f"action:{action_id}"
        
        # Check cache primero
        if cache_key in self._cache:
            logger.debug(f"Action auth cache HIT for: {action_id}")
            return self._cache[cache_key]
        
        logger.debug(f"Resolving action auth for: {action_id}")
        
        # Obtener auth requirements específicos para la acción
        action_auth_data = await self.auth_policy_service.get_action_auth_requirements(action_id)
        
        if action_auth_data:
            # Crear AuthPolicy con datos específicos de la acción
            auth_policy = AuthPolicy(action_auth_data)
            self._cache[cache_key] = auth_policy
            logger.debug(f"Action auth resolved from DB for: {action_id}")
            return auth_policy
        
        logger.debug(f"No specific action auth found for: {action_id}")
        return None
    
    async def resolve_multiple_auth(self, auth_strings: list) -> Dict[str, AuthPolicy]:
        """
        Resuelve múltiples auth strings de forma eficiente
        
        Args:
            auth_strings: Lista de auth strings
            
        Returns:
            Dict con auth_string -> AuthPolicy
        """
        results = {}
        
        for auth_string in auth_strings:
            if auth_string:
                policy = await self.resolve_auth_once(auth_string)
                if policy:
                    results[auth_string] = policy
        
        return results
    
    async def resolve_multiple_action_auth(self, action_ids: list) -> Dict[str, AuthPolicy]:
        """
        Resuelve auth para múltiples acciones de forma eficiente
        
        Args:
            action_ids: Lista de action UUIDs
            
        Returns:
            Dict con action_id -> AuthPolicy
        """
        results = {}
        
        for action_id in action_ids:
            if action_id:
                policy = await self.resolve_action_auth(action_id)
                if policy:
                    results[action_id] = policy
        
        return results
    
    def clear_cache(self):
        """Limpia cache (útil para testing)"""
        self._cache.clear()
        logger.debug("Auth cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Stats del cache para debugging"""
        return {
            "cached_items": len(self._cache),
            "cached_keys": list(self._cache.keys())
        }


# Factory para FastAPI DI
async def get_auth_resolver(
    auth_policy_service: AuthPolicyService = Depends(get_auth_policy_service)
) -> CentralAuthResolver:
    """
    Factory para inyección de dependencias
    """
    return CentralAuthResolver(auth_policy_service)