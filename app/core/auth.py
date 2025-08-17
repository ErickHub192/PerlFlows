# app/core/auth.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated
from datetime import datetime, timedelta, timezone
import secrets
import hashlib
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.core.config import settings

# El endpoint que emite tokens es POST /api/auth/login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No se pudo validar credenciales",
    headers={"WWW-Authenticate": "Bearer"},
)


def create_access_token(sub: int, expires_minutes: int = 10080) -> str:  # 7 días = 7 * 24 * 60 = 10080 minutos
    """
    Genera un JWT con subject `sub` (entero) y expiración en `expires_minutes`.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {"sub": str(sub), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def create_refresh_token(expires_days: int = 7) -> tuple[str, str, datetime]:
    """Generate a secure refresh token and its hash with expiration."""
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expire = datetime.now(timezone.utc) + timedelta(days=expires_days)
    return token, token_hash, expire


def verify_refresh_token(token: str, token_hash: str) -> bool:
    """Return True if the provided token matches the stored hash."""
    calc_hash = hashlib.sha256(token.encode()).hexdigest()
    return secrets.compare_digest(calc_hash, token_hash)


def verify_jwt_token(token: str) -> int:
    """
    Valida el JWT y retorna el campo `sub` convertido a int.
    Lanza excepción si expiró o es inválido.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except ExpiredSignatureError:
        raise ValueError("Token has expired")
    except InvalidTokenError:
        raise ValueError("Invalid token")
    
    sub = payload.get("sub")
    if sub is None:
        raise ValueError("Token missing subject")
    
    try:
        return int(sub)
    except ValueError:
        raise ValueError("Invalid user ID in token")


async def get_current_user_id(token: Annotated[str, Depends(oauth2_scheme)]) -> int:
    """
    Valida el JWT y retorna el campo `sub` convertido a int.
    Lanza 401 si expiró o es inválido.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token ha expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError:
        raise credentials_exception

    sub = payload.get("sub")
    if sub is None:
        raise credentials_exception

    try:
        return int(sub)
    except ValueError:
        raise credentials_exception


async def require_admin(user_id: Annotated[int, Depends(get_current_user_id)]) -> int:
    """
    Dependencia para rutas que solo pueden usar administradores.
    Valida que el user_id esté en ADMIN_USER_IDS (entero).
    """
    admin_ids = getattr(settings, "ADMIN_USER_IDS", [])
    if user_id not in admin_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos de administrador requeridos",
        )
    return user_id
