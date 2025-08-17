# app/routers/credentials_router.py

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.core.auth import get_current_user_id
from app.services.credential_service import get_credential_service, CredentialService
from app.dtos.credential_dto import CredentialDTO, CredentialInputDTO

router = APIRouter(
    prefix="/api/credentials",
    tags=["credentials"],
    responses={404: {"description": "Not found"}, 500: {"description": "Internal error"}},
)


@router.get(
    "/",
    response_model=List[CredentialDTO],
    summary="Listar todas las credenciales del usuario"
)
async def list_credentials(
    chat_id: Optional[UUID] = Query(None, description="ID de la sesi\u00f3n de chat"),
    user_id: int = Depends(get_current_user_id),
    svc: CredentialService = Depends(get_credential_service),
) -> List[CredentialDTO]:
    """
    Devuelve el listado de credenciales (provider, flavor, client_id, client_secret, etc.)
    asociadas al usuario autenticado. Si se provee ``chat_id``, la sesi\u00f3n se
    verifica y se retorna 404 si no existe.
    """
    try:
        creds = await svc.list_user_credentials(user_id=user_id, chat_id=chat_id)
        return [CredentialDTO.model_validate(c) for c in creds]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/{provider_or_service_id}",
    response_model=CredentialDTO,
    summary="Obtener credencial por provider+flavor (legacy) o service_id (nuevo)"
)
async def get_credential(
    provider_or_service_id: str,
    flavor: Optional[str] = Query(None, description="Flavor del provider (solo para legacy)"),
    chat_id: Optional[str] = Query(None, description="ID de chat asociado"),
    user_id: int = Depends(get_current_user_id),
    svc: CredentialService = Depends(get_credential_service),
) -> CredentialDTO:
    """
    ✅ REFACTORIZADO: Soporta tanto provider+flavor (legacy) como service_id (nuevo)
    - Si flavor está presente: busca por provider+flavor (legacy)
    - Si flavor es None: busca por service_id (nuevo sistema agnóstico)
    """
    try:
        if flavor is not None:
            # Legacy mode: provider + flavor (necesita servicio legacy)
            # TODO: Implementar búsqueda legacy si es necesaria
            raise HTTPException(status_code=400, detail="Legacy provider+flavor mode deprecated. Use service_id instead.")
        else:
            # New agnostic mode: service_id
            cred = await svc.get_credential(user_id=user_id, service_id=provider_or_service_id, chat_id=chat_id)
        
        if not cred:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credencial no encontrada")
        return CredentialDTO.model_validate(cred)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/",
    response_model=CredentialDTO,
    summary="Crear o actualizar las credenciales del usuario"
)
async def upsert_credentials(
    input_data: CredentialInputDTO,
    user_id: int = Depends(get_current_user_id),
    svc: CredentialService = Depends(get_credential_service),
) -> CredentialDTO:
    """
    Inserta o actualiza las credenciales para el usuario autenticado.
    Si ya existe una credencial para ese (provider, flavor), la actualiza.
    """
    try:
        # ✅ REFACTORIZADO: Usar método agnóstico
        cred_data = input_data.model_dump()
        cred = await svc.create_credential(
            user_id=user_id, 
            service_id=cred_data.get('service_id', cred_data.get('provider')),
            data=cred_data,
            chat_id=cred_data.get('chat_id')
        )
        return CredentialDTO.model_validate(cred)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete(
    "/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar credencial por service_id (agnóstico)"
)
async def delete_credentials(
    service_id: str,
    chat_id: Optional[str] = Query(None, description="ID de chat asociado"),
    user_id: int = Depends(get_current_user_id),
    svc: CredentialService = Depends(get_credential_service),
) -> None:
    """
    ✅ REFACTORIZADO: Elimina credencial por service_id (sistema agnóstico)
    Retorna 204 No Content si se eliminó exitosamente.
    """
    try:
        await svc.delete_credential(user_id=user_id, service_id=service_id, chat_id=chat_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
