# app/authenticators/auth.py

from typing import Any
from fastapi import Depends, HTTPException, status

from app.core.auth import get_current_user_id
from app.repositories.ICredentialRepository import ICredentialRepository
from app.repositories.credential_repository import get_credential_repository

async def get_credentials_for_user(
    provider: str,
    user_id: int = Depends(get_current_user_id),
    repo: ICredentialRepository = Depends(get_credential_repository)
) -> Any:
    """
    Dependencia que recupera las credenciales del usuario autenticado
    para un proveedor dado.

    Args:
        provider: dominio o nombre del servicio (e.g., "google").
        user_id: inyectado desde el JWT.
        repo: repositorio de credenciales.

    Returns:
        Diccionario con los datos de la credencial.

    Raises:
        HTTPException 404 si no existe credencial para ese proveedor.
    """
    cred = await repo.get_credential(user_id, provider)
    if not cred:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró credencial para el proveedor '{provider}'"
        )
    return cred
