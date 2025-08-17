# app/services/IAuthPolicyService.py

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List


class IAuthPolicyService(ABC):
    """
    Interface para el servicio de políticas de autenticación.
    Maneja políticas de autenticación dinámicas basadas en base de datos.
    """

    @abstractmethod
    async def resolve_auth(self, auth_string: str) -> Optional[Dict[str, Any]]:
        """
        Resuelve auth_string a configuración completa desde BD.
        Reemplaza parse_auth() + hardcodeo de scopes.
        
        Args:
            auth_string: String de autenticación (ej: "oauth2_google_gmail")
            
        Returns:
            Dict con configuración completa o None si no existe
        """
        pass

    @abstractmethod
    async def get_auth_policy_by_provider(
        self, 
        provider: str, 
        mechanism: str,
        service: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene política de auth por proveedor, servicio y mecanismo.
        
        Args:
            provider: Proveedor (google, dropbox, etc.)
            mechanism: Mecanismo de auth (oauth2, api_key, etc.) - REQUERIDO
            service: Servicio específico (opcional)
        """
        pass

    @abstractmethod
    async def get_action_auth_requirements(self, action_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene requerimientos de autenticación para una acción específica.
        """
        pass

    @abstractmethod
    async def create_auth_policy(self, policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea una nueva política de autenticación.
        """
        pass

    @abstractmethod
    async def create_action_auth_scope(
        self, 
        action_id: str, 
        policy_id: int, 
        required_scopes: List[str]
    ) -> Dict[str, Any]:
        """
        Crea scopes de autenticación para una acción.
        """
        pass

    @abstractmethod
    async def update_action_scopes(
        self, 
        action_id: str, 
        required_scopes: List[str]
    ) -> Dict[str, Any]:
        """
        Actualiza los scopes requeridos para una acción.
        """
        pass

    @abstractmethod
    async def get_all_active_policies(self) -> List[Dict[str, Any]]:
        """
        Obtiene todas las políticas de autenticación activas.
        """
        pass

    @abstractmethod
    async def get_actions_by_policy(self, policy_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene todas las acciones que usan una política específica.
        """
        pass

    @abstractmethod
    async def fallback_parse_auth(self, auth_string: str) -> Dict[str, Any]:
        """
        Parsing de fallback para auth_string no encontrados en BD.
        """
        pass