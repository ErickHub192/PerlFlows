"""
AuthHandlerRegistry - Registry agnóstico para manejadores de autenticación
Usa el registry pattern existente para eliminar hardcodeo de if/elif statements
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type, Protocol
from app.authenticators.registry import get_registered_class, get_registered_mechanisms
from app.dtos.auth_requirement_dto import AuthStepDTO

logger = logging.getLogger(__name__)


class AuthHandler(Protocol):
    """Protocol que define la interfaz para auth handlers"""
    
    async def create_auth_step(
        self,
        service_id: str,
        display_name: str,
        auth_config: Dict[str, Any],
        user_id: int,
        chat_id: str,
        **kwargs
    ) -> AuthStepDTO:
        """Crea un paso de autenticación para este mecanismo"""
        ...
    
    async def validate_credentials(
        self,
        service_id: str,
        credentials: Dict[str, Any]
    ) -> bool:
        """Valida si las credenciales son válidas para este mecanismo"""
        ...


class BaseAuthHandler(ABC):
    """Base class para auth handlers"""
    
    def __init__(self, mechanism: str):
        self.mechanism = mechanism
    
    @abstractmethod
    async def create_auth_step(
        self,
        service_id: str,
        display_name: str,
        auth_config: Dict[str, Any],
        user_id: int,
        chat_id: str,
        **kwargs
    ) -> AuthStepDTO:
        """Implementación específica para crear auth step"""
        pass
    
    @abstractmethod
    async def validate_credentials(
        self,
        service_id: str,
        credentials: Dict[str, Any]
    ) -> bool:
        """Implementación específica para validar credenciales"""
        pass


class OAuth2AuthHandler(BaseAuthHandler):
    """Handler para autenticación OAuth2"""
    
    def __init__(self):
        super().__init__("oauth2")
    
    async def create_auth_step(
        self,
        service_id: str,
        display_name: str,
        auth_config: Dict[str, Any],
        user_id: int,
        chat_id: str,
        **kwargs
    ) -> AuthStepDTO:
        """Crea paso OAuth2"""
        from app.mappers.auth_requirement_mapper import create_auth_step_dto
        
        # Generate OAuth URL with state
        auth_url = auth_config.get("base_auth_url", "/oauth/authorize")
        state_params = {
            "user_id": user_id,
            "chat_id": chat_id,
            "service_id": service_id
        }
        
        full_auth_url = f"{auth_url}?service_id={service_id}&state={state_params}"
        
        return create_auth_step_dto(
            mechanism=self.mechanism,
            service_id=service_id,
            display_name=display_name,
            auth_url=full_auth_url,
            required_scopes=kwargs.get("required_scopes", []),
            metadata={
                "redirect_uri": auth_config.get("redirect_uri"),
                "client_id": auth_config.get("client_id"),
                **kwargs.get("metadata", {})
            }
        )
    
    async def validate_credentials(
        self,
        service_id: str,
        credentials: Dict[str, Any]
    ) -> bool:
        """Valida credenciales OAuth2"""
        return (
            credentials.get("access_token") is not None and
            credentials.get("service_id") == service_id
        )


class ApiKeyAuthHandler(BaseAuthHandler):
    """Handler para autenticación API Key"""
    
    def __init__(self):
        super().__init__("api_key")
    
    async def create_auth_step(
        self,
        service_id: str,
        display_name: str,
        auth_config: Dict[str, Any],
        user_id: int,
        chat_id: str,
        **kwargs
    ) -> AuthStepDTO:
        """Crea paso API Key"""
        from app.mappers.auth_requirement_mapper import create_auth_step_dto
        
        return create_auth_step_dto(
            mechanism=self.mechanism,
            service_id=service_id,
            display_name=display_name,
            input_required=True,
            metadata={
                "field_name": auth_config.get("key_field_name", "api_key"),
                "field_label": auth_config.get("key_field_label", "API Key"),
                "help_text": auth_config.get("help_text", f"Enter your {display_name} API key"),
                "docs_url": auth_config.get("docs_url"),
                **kwargs.get("metadata", {})
            }
        )
    
    async def validate_credentials(
        self,
        service_id: str,
        credentials: Dict[str, Any]
    ) -> bool:
        """Valida credenciales API Key"""
        config = credentials.get("config", {})
        return (
            config.get("api_key") is not None and
            credentials.get("service_id") == service_id
        )


class BotTokenAuthHandler(BaseAuthHandler):
    """Handler para autenticación Bot Token"""
    
    def __init__(self):
        super().__init__("bot_token")
    
    async def create_auth_step(
        self,
        service_id: str,
        display_name: str,
        auth_config: Dict[str, Any],
        user_id: int,
        chat_id: str,
        **kwargs
    ) -> AuthStepDTO:
        """Crea paso Bot Token"""
        from app.mappers.auth_requirement_mapper import create_auth_step_dto
        
        return create_auth_step_dto(
            mechanism=self.mechanism,
            service_id=service_id,
            display_name=display_name,
            input_required=True,
            metadata={
                "field_name": auth_config.get("token_field_name", "bot_token"),
                "field_label": auth_config.get("token_field_label", "Bot Token"),
                "help_text": auth_config.get("help_text", f"Enter your {display_name} bot token"),
                "docs_url": auth_config.get("docs_url"),
                **kwargs.get("metadata", {})
            }
        )
    
    async def validate_credentials(
        self,
        service_id: str,
        credentials: Dict[str, Any]
    ) -> bool:
        """Valida credenciales Bot Token"""
        config = credentials.get("config", {})
        return (
            config.get("bot_token") is not None and
            credentials.get("service_id") == service_id
        )


class DbCredentialsAuthHandler(BaseAuthHandler):
    """Handler para credenciales de base de datos"""
    
    def __init__(self):
        super().__init__("db_credentials")
    
    async def create_auth_step(
        self,
        service_id: str,
        display_name: str,
        auth_config: Dict[str, Any],
        user_id: int,
        chat_id: str,
        **kwargs
    ) -> AuthStepDTO:
        """Crea paso DB Credentials"""
        from app.mappers.auth_requirement_mapper import create_auth_step_dto
        
        return create_auth_step_dto(
            mechanism=self.mechanism,
            service_id=service_id,
            display_name=display_name,
            input_required=True,
            metadata={
                "fields": auth_config.get("required_fields", [
                    {"name": "host", "label": "Host", "type": "text"},
                    {"name": "port", "label": "Port", "type": "number"},
                    {"name": "database", "label": "Database", "type": "text"},
                    {"name": "username", "label": "Username", "type": "text"},
                    {"name": "password", "label": "Password", "type": "password"}
                ]),
                "help_text": auth_config.get("help_text", f"Enter your {display_name} connection details"),
                "docs_url": auth_config.get("docs_url"),
                **kwargs.get("metadata", {})
            }
        )
    
    async def validate_credentials(
        self,
        service_id: str,
        credentials: Dict[str, Any]
    ) -> bool:
        """Valida credenciales DB"""
        config = credentials.get("config", {})
        required_fields = ["host", "database", "username", "password"]
        return (
            all(config.get(field) for field in required_fields) and
            credentials.get("service_id") == service_id
        )


class AuthHandlerRegistry:
    """
    Registry agnóstico para auth handlers
    Elimina hardcodeo y usa dynamic dispatch
    """
    
    def __init__(self):
        self._handlers: Dict[str, AuthHandler] = {}
        self._initialize_default_handlers()
    
    def _initialize_default_handlers(self):
        """Inicializa handlers por defecto"""
        self._handlers["oauth2"] = OAuth2AuthHandler()
        self._handlers["api_key"] = ApiKeyAuthHandler()
        self._handlers["bot_token"] = BotTokenAuthHandler()
        self._handlers["db_credentials"] = DbCredentialsAuthHandler()
    
    def register_handler(self, mechanism: str, handler: AuthHandler):
        """Registra un handler personalizado"""
        self._handlers[mechanism] = handler
        logger.info(f"Registered auth handler for mechanism: {mechanism}")
    
    def get_handler(self, mechanism: str) -> Optional[AuthHandler]:
        """Obtiene handler para un mecanismo específico"""
        return self._handlers.get(mechanism)
    
    def get_supported_mechanisms(self) -> list:
        """Retorna lista de mecanismos soportados"""
        return list(self._handlers.keys())
    
    async def create_auth_step_for_mechanism(
        self,
        mechanism: str,
        service_id: str,
        display_name: str,
        auth_config: Dict[str, Any],
        user_id: int,
        chat_id: str,
        **kwargs
    ) -> Optional[AuthStepDTO]:
        """
        Crea auth step usando el handler apropiado
        ✅ SIN IF/ELIF - usa dynamic dispatch
        """
        handler = self.get_handler(mechanism)
        if not handler:
            logger.warning(f"No handler found for mechanism: {mechanism}")
            return None
        
        try:
            return await handler.create_auth_step(
                service_id=service_id,
                display_name=display_name,
                auth_config=auth_config,
                user_id=user_id,
                chat_id=chat_id,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error creating auth step for {mechanism}: {e}")
            return None
    
    async def validate_credentials_for_mechanism(
        self,
        mechanism: str,
        service_id: str,
        credentials: Dict[str, Any]
    ) -> bool:
        """
        Valida credenciales usando el handler apropiado
        ✅ SIN IF/ELIF - usa dynamic dispatch
        """
        handler = self.get_handler(mechanism)
        if not handler:
            logger.warning(f"No handler found for mechanism: {mechanism}")
            return False
        
        try:
            return await handler.validate_credentials(service_id, credentials)
        except Exception as e:
            logger.error(f"Error validating credentials for {mechanism}: {e}")
            return False


# Singleton instance
_auth_handler_registry = AuthHandlerRegistry()


def get_auth_handler_registry() -> AuthHandlerRegistry:
    """
    Obtiene la instancia singleton del registry
    """
    return _auth_handler_registry