# app/authenticators/__init__.py

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import async_session

from app.authenticators.registry import get_registered_class
from app.services.auth_resolver import CentralAuthResolver

# Import all authenticators to trigger their @register_authenticator decorators
from app.authenticators import google
from app.authenticators import dropbox
from app.authenticators import microsoft
from app.authenticators import slack
from app.authenticators import salesforce
from app.authenticators import github
from app.authenticators import hubspot
from app.authenticators import whatsapp
from app.authenticators import api_key
from app.authenticators import bot_token
from app.authenticators import db_credentials


async def get_authenticator(default_auth: str, user_id: int, db: AsyncSession = async_session, auth_resolver: CentralAuthResolver = None):
    """
    ✅ MIGRADO: Obtiene authenticator usando CentralAuthResolver en lugar de parse_auth
    
    Args:
        default_auth: String de auth (ej: "oauth2_google_sheets")
        user_id: ID del usuario
        db: Sesión de BD
        auth_resolver: ✅ NUEVO: CentralAuthResolver para obtener auth policies

    1. CentralAuthResolver obtiene auth policy completa desde BD
    2. Si no hay policy o mecanismo → no se requiere autenticador
    3. Se busca en el registro global la clase correspondiente a (mech, provider)
    4. Se instancia la clase con auth_policy completa
    5. Si no existe ningún registro, se lanza ValueError
    """
    if not auth_resolver:
        raise ValueError("CentralAuthResolver is required")
        
    # ✅ NUEVO: Usar CentralAuthResolver en lugar de parse_auth
    auth_policy = await auth_resolver.resolve_auth_once(default_auth)
    
    if not auth_policy:
        return None
    
    mech = auth_policy.mechanism
    provider = auth_policy.provider
    service = auth_policy.service  # Antes era "flavor"

    # Si no hay mecanismo ni provider → no se requiere autenticador
    if not mech and not provider:
        return None

    # Buscamos la clase en el registro global (incluye caso "db","credentials")
    cls = get_registered_class(mech, provider)
    if not cls:
        raise ValueError(f"Mecanismo/Proveedor no soportado: '{mech}_{provider}'")

    # ✅ NUEVO: Instanciar con auth_policy completa desde BD
    return cls(user_id=user_id, db=db, auth_policy=auth_policy.to_dict())
