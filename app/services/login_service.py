import bcrypt
from datetime import datetime, timezone
import hashlib
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.core.auth import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)
from app.exceptions.api_exceptions import InvalidDataException
from app.dtos.login_dto import LoginRequestDTO, LoginResponseDTO
from app.repositories.login_repository import LoginRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.dependencies.repository_dependencies import get_login_repository, get_refresh_token_repository
from app.db.database import get_db

logger = logging.getLogger(__name__)


class LoginService:
    def __init__(self, repo: LoginRepository, token_repo: RefreshTokenRepository):
        self.repo = repo
        self.token_repo = token_repo

    async def login(self, req: LoginRequestDTO) -> LoginResponseDTO:
        logger.info("LOGIN_SERVICE: Inicio de login para usuario %s", req.username)
        
        try:
            # 1. Recuperar usuario por username
            logger.debug("LOGIN_SERVICE: Buscando usuario en base de datos: %s", req.username)
            user = await self.repo.get_user_by_username(req.username)
            if not user:
                logger.warning("LOGIN_SERVICE: Usuario %s no encontrado en base de datos", req.username)
                raise InvalidDataException("Usuario o contraseña incorrectos")

            logger.debug("LOGIN_SERVICE: Usuario encontrado, user_id: %s", user.get("id"))
            
            # 2. Verificar que exista hashed_password y que la contraseña coincida
            hashed = user.get("hashed_password")
            if not hashed:
                logger.error("LOGIN_SERVICE: Usuario %s no tiene contraseña configurada", req.username)
                raise InvalidDataException("Usuario o contraseña incorrectos")
                
            logger.debug("LOGIN_SERVICE: Verificando contraseña para usuario %s", req.username)
            if not bcrypt.checkpw(req.password.encode(), hashed.encode()):
                logger.warning("LOGIN_SERVICE: Contraseña incorrecta para usuario %s", req.username)
                raise InvalidDataException("Usuario o contraseña incorrectos")

            logger.debug("LOGIN_SERVICE: Contraseña verificada correctamente para usuario %s", req.username)

            # 3. Generar access y refresh tokens
            logger.debug("LOGIN_SERVICE: Generando tokens para usuario %s", req.username)
            access_token = create_access_token(sub=user["id"])
            refresh_token, token_hash, expires = create_refresh_token()

            logger.info("LOGIN_SERVICE: Tokens generados para usuario %s, user_id: %s", req.username, user["id"])

            # 4. Guardar refresh token en base de datos
            logger.debug("LOGIN_SERVICE: Guardando refresh token en BD para usuario %s", req.username)
            await self.token_repo.create_token(
                {
                    "user_id": user["id"],
                    "token_hash": token_hash,
                    "expires_at": expires,
                }
            )
            logger.info("LOGIN_SERVICE: Refresh token creado en BD para usuario %s", req.username)

            # 5. Construir y retornar el DTO de respuesta
            logger.info("LOGIN_SERVICE: Autenticación completada exitosamente para usuario %s, user_id: %s", req.username, user["id"])
            return LoginResponseDTO(
                access_token=access_token,
                token_type="bearer",
                user_id=str(user["id"]),
                refresh_token=refresh_token,
            )
            
        except InvalidDataException:
            # Re-raise expected exceptions
            raise
        except Exception as e:
            logger.error("LOGIN_SERVICE: Error inesperado durante login para usuario %s: %s", req.username, str(e))
            logger.exception("LOGIN_SERVICE: Stack trace completo del error")
            raise

    async def refresh_access_token(self, token: str) -> LoginResponseDTO:
        logger.info("LOGIN_SERVICE: Iniciando refresh token, token_preview: %s...", token[:10])
        
        try:
            logger.debug("LOGIN_SERVICE: Calculando hash del refresh token")
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            logger.debug("LOGIN_SERVICE: Buscando refresh token en BD, token_hash: %s...", token_hash[:10])
            data = await self.token_repo.get_token(token_hash)
            
            if not data:
                logger.warning("LOGIN_SERVICE: Refresh token no encontrado en BD")
                raise InvalidDataException("Token de refresco inválido")
            
            logger.debug("LOGIN_SERVICE: Refresh token encontrado, user_id: %s, expires_at: %s", data["user_id"], data["expires_at"])
            
            # Verificar expiración
            if data["expires_at"] < datetime.now(timezone.utc):
                logger.warning("LOGIN_SERVICE: Refresh token expirado para user_id: %s", data["user_id"])
                raise InvalidDataException("Token de refresco inválido")
            
            # Verificar token
            if not verify_refresh_token(token, data["token_hash"]):
                logger.warning("LOGIN_SERVICE: Refresh token no válido para user_id: %s", data["user_id"])
                raise InvalidDataException("Token de refresco inválido")

            user_id = data["user_id"]
            logger.debug("LOGIN_SERVICE: Refresh token válido para user_id: %s", user_id)

            # Rotate token
            logger.debug("LOGIN_SERVICE: Eliminando refresh token antiguo para user_id: %s", user_id)
            await self.token_repo.delete_token(token_hash)
            
            logger.debug("LOGIN_SERVICE: Generando nuevo refresh token para user_id: %s", user_id)
            new_refresh, new_hash, expires = create_refresh_token()
            await self.token_repo.create_token(
                {"user_id": user_id, "token_hash": new_hash, "expires_at": expires}
            )
            logger.info("LOGIN_SERVICE: Refresh token rotado exitosamente para user_id: %s", user_id)

            logger.debug("LOGIN_SERVICE: Generando nuevo access token para user_id: %s", user_id)
            new_access = create_access_token(sub=user_id)
            logger.info("LOGIN_SERVICE: Nuevo access token generado para user_id: %s", user_id)
            
            return LoginResponseDTO(
                access_token=new_access,
                token_type="bearer",
                user_id=str(user_id),
                refresh_token=new_refresh,
            )
            
        except InvalidDataException:
            # Re-raise expected exceptions
            raise
        except Exception as e:
            logger.error("LOGIN_SERVICE: Error inesperado durante refresh token: %s", str(e))
            logger.exception("LOGIN_SERVICE: Stack trace completo del error")
            raise

    async def logout(self, token: str) -> None:
        logger.info("LOGIN_SERVICE: Iniciando logout, token_preview: %s...", token[:10])
        
        try:
            logger.debug("LOGIN_SERVICE: Calculando hash del refresh token para logout")
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            logger.debug("LOGIN_SERVICE: Buscando refresh token en BD para logout")
            existing = await self.token_repo.get_token(token_hash)
            if not existing:
                logger.warning("LOGIN_SERVICE: Refresh token no encontrado para logout")
                raise InvalidDataException("Token de refresco inválido")
            
            logger.debug("LOGIN_SERVICE: Eliminando refresh token para logout, user_id: %s", existing["user_id"])
            await self.token_repo.delete_token(token_hash)
            logger.info("LOGIN_SERVICE: Logout completado exitosamente para user_id: %s", existing["user_id"])
            
        except InvalidDataException:
            # Re-raise expected exceptions
            raise
        except Exception as e:
            logger.error("LOGIN_SERVICE: Error inesperado durante logout: %s", str(e))
            logger.exception("LOGIN_SERVICE: Stack trace completo del error")
            raise


# Factory para FastAPI DI
def get_login_service(
    login_repo: LoginRepository = Depends(get_login_repository),
    token_repo: RefreshTokenRepository = Depends(get_refresh_token_repository)
) -> LoginService:
    """
    ✅ REFACTORED: Factory con FastAPI DI apropiada
    """
    return LoginService(login_repo, token_repo)
