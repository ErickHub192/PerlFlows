# app/routers/login_router.py

import logging
from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.supabase_client import get_supabase_client
from app.repositories.login_repository import LoginRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.db.database import get_db
from app.services.login_service import LoginService
from app.services.register_service import RegisterService
from app.exceptions.api_exceptions import InvalidDataException
from app.dtos.login_dto import LoginRequestDTO, LoginResponseDTO
from app.dtos.register_dto import RegisterRequestDTO, RegisterResponseDTO

router = APIRouter(prefix="/api/auth", tags=["auth"])


async def get_login_service(
    client: Client = Depends(get_supabase_client), db: AsyncSession = Depends(get_db)
) -> LoginService:
    repo = LoginRepository(client)
    token_repo = RefreshTokenRepository(db)
    return LoginService(repo, token_repo)


async def get_register_service(
    client: Client = Depends(get_supabase_client),
    login_svc: LoginService = Depends(get_login_service),
) -> RegisterService:
    repo = LoginRepository(client)
    return RegisterService(repo, login_svc)


@router.post("/login", response_model=LoginResponseDTO)
async def login(
    request: LoginRequestDTO,
    service: LoginService = Depends(get_login_service),
):
    logging.info(f"LOGIN_ROUTER: Iniciando login para usuario: {request.username}")
    try:
        result = await service.login(request)
        logging.info(f"LOGIN_ROUTER: Login exitoso para usuario: {request.username}, user_id: {result.user_id}")
        return result
    except InvalidDataException as e:
        logging.warning(f"LOGIN_ROUTER: Fallo de autenticación para usuario: {request.username}, error: {str(e)}")
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logging.error(f"LOGIN_ROUTER: Error inesperado durante login para usuario: {request.username}")
        logging.exception(f"LOGIN_ROUTER: Detalles completos del error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {type(e).__name__}")


@router.post("/register", response_model=RegisterResponseDTO)
async def register(
    request: RegisterRequestDTO,
    service: RegisterService = Depends(get_register_service),
):
    logging.info(f"LOGIN_ROUTER: Iniciando registro para usuario: {request.username}, email: {request.email}")
    try:
        result = await service.register(request)
        logging.info(f"LOGIN_ROUTER: Registro exitoso para usuario: {request.username}")
        return result
    except HTTPException as e:
        logging.warning(f"LOGIN_ROUTER: Error HTTP durante registro para usuario: {request.username}, status: {e.status_code}, detail: {e.detail}")
        raise
    except Exception as e:
        logging.error(f"LOGIN_ROUTER: Error inesperado durante registro para usuario: {request.username}")
        logging.exception(f"LOGIN_ROUTER: Detalles completos del error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Registration error: {type(e).__name__}: {str(e)}")


@router.post("/refresh", response_model=LoginResponseDTO)
async def refresh(
    refresh_token: str,
    service: LoginService = Depends(get_login_service),
):
    logging.info(f"LOGIN_ROUTER: Iniciando refresh token, token_preview: {refresh_token[:10]}...")
    try:
        result = await service.refresh_access_token(refresh_token)
        logging.info(f"LOGIN_ROUTER: Refresh token exitoso para user_id: {result.user_id}")
        return result
    except InvalidDataException as e:
        logging.warning(f"LOGIN_ROUTER: Refresh token inválido, error: {str(e)}")
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logging.error(f"LOGIN_ROUTER: Error inesperado durante refresh token")
        logging.exception(f"LOGIN_ROUTER: Detalles completos del error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {type(e).__name__}")


@router.post("/logout")
async def logout(
    refresh_token: str,
    service: LoginService = Depends(get_login_service),
):
    logging.info(f"LOGIN_ROUTER: Iniciando logout, token_preview: {refresh_token[:10]}...")
    try:
        await service.logout(refresh_token)
        logging.info(f"LOGIN_ROUTER: Logout exitoso")
        return {"detail": "logout exitoso"}
    except InvalidDataException as e:
        logging.warning(f"LOGIN_ROUTER: Error durante logout, token inválido: {str(e)}")
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logging.error(f"LOGIN_ROUTER: Error inesperado durante logout")
        logging.exception(f"LOGIN_ROUTER: Detalles completos del error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {type(e).__name__}")
