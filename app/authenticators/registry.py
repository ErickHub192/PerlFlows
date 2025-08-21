# app/authenticators/registry.py

from typing import Dict, Type

_AUTH_REGISTRY: Dict[str, Dict[str, Type]] = {}


def register_authenticator(mecanismo: str, provider: str):
    """
    Decorador para registrar una clase autenticadora en el índice global.
    - mecanismo: cadena como "oauth2", "api_key", "bot_token" o "db_credentials"
    - provider: nombre del proveedor ("google", "stripe", "telegram", "").
    Ejemplo:
        @register_authenticator("oauth2", "google")
        class GoogleOAuthAuthenticator(...):
            ...
    """
    def _wrapper(cls):
        # DEBUG: Log del registro
        print(f"🔧 REGISTERING: {mecanismo}_{provider} -> {cls.__name__}")
        
        # Si aún no existe el diccionario para este mecanismo, lo creamos
        if mecanismo not in _AUTH_REGISTRY:
            _AUTH_REGISTRY[mecanismo] = {}
        # Asignamos la clase al provider dentro de ese mecanismo
        _AUTH_REGISTRY[mecanismo][provider] = cls
        
        # DEBUG: Estado actual del registry
        print(f"🔧 REGISTRY NOW: {_AUTH_REGISTRY}")
        
        return cls
    return _wrapper


def get_registered_class(mecanismo: str, provider: str):
    """
    Busca en el registro la clase autenticadora para (mecanismo, provider).
    Retorna None si no existe.
    """
    # DEBUG: Log de búsqueda
    print(f"🔍 SEARCHING: {mecanismo}_{provider}")
    print(f"🔍 AVAILABLE REGISTRY: {_AUTH_REGISTRY}")
    
    result = _AUTH_REGISTRY.get(mecanismo, {}).get(provider)
    print(f"🔍 RESULT: {result}")
    
    return result


def get_registered_mechanisms():
    """
    Retorna el conjunto de mecanismos registrados.
    Compatible con auth_handlers.get_registered_handlers().
    """
    return set(_AUTH_REGISTRY.keys())
