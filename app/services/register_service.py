# app/services/register_service.py

import bcrypt
from fastapi import HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dtos.register_dto import RegisterRequestDTO, RegisterResponseDTO
from app.dtos.login_dto import LoginRequestDTO
from app.repositories.login_repository import LoginRepository
from app.services.login_service import LoginService
from app.db.database import get_db

class RegisterService:
    def __init__(self, repo: LoginRepository, login_svc: LoginService):
        self.repo = repo
        self.login_svc = login_svc

    async def register(self, req: RegisterRequestDTO) -> RegisterResponseDTO:
        # 1) Verificar existencia
        if await self.repo.get_user_by_username(req.username):
            raise HTTPException(status_code=400, detail="El usuario ya existe")

        # 2) Hash de contraseña
        hashed = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
        data = req.model_dump(exclude={"password"})
        data["hashed_password"] = hashed

        # 3) Crear usuario
        await self.repo.create_user(data)

        # 4) Auto-login
        login_req = LoginRequestDTO(username=req.username, password=req.password)
        token_data = await self.login_svc.login(login_req)
        return RegisterResponseDTO(**token_data.model_dump())


# Factory para FastAPI DI
def get_register_service(
    db: AsyncSession = Depends(get_db),
) -> RegisterService:
    """
    Factory para inyección de dependencias
    """
    from app.repositories.refresh_token_repository import RefreshTokenRepository
    
    login_repo = LoginRepository(db)
    token_repo = RefreshTokenRepository(db)
    login_service = LoginService(login_repo, token_repo)
    
    return RegisterService(login_repo, login_service)
