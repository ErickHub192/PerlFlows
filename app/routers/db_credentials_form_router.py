# app/routers/db_credentials_form_router.py

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Any, Dict

from app.authenticators import get_authenticator
from app.core.auth import get_current_user_id
from app.db.database import async_session

router = APIRouter(
    prefix="/api/db-credentials",
    tags=["db-credentials"],
    responses={404: {"description": "Not found"}, 500: {"description": "Internal error"}},
)

@router.get(
    "/schema",
    summary="Devuelve el JSON Schema para credenciales de base de datos (según flavor)",
    response_model=Dict[str, Any]
)
async def get_db_credentials_schema(
    node_id: UUID = Query(..., description="UUID del nodo que pide credenciales de DB"),
    flavor: str = Query(
        ..., 
        description="Tipo de base de datos: 'postgres', 'mysql', 'mongo', 'redis', etc."
    ),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(async_session),
) -> Dict[str, Any]:
    """
    1. El frontend envía node_id y flavor.
    2. Construimos default_auth = f"db_credentials_{flavor}".
    3. Instanciamos el authenticator: get_authenticator("db_credentials_<flavor>", …).
    4. Devolvemos lo que get_json_schema() retorne.
    """
    # Validar inputs básicos
    if not node_id:
        raise HTTPException(status_code=400, detail="Falta parámetro 'node_id'.")
    if not flavor:
        raise HTTPException(status_code=400, detail="Falta parámetro 'flavor'.")

    default_auth = f"db_credentials_{flavor}"
    auth = get_authenticator(default_auth, user_id, db)
    if auth is None:
        raise HTTPException(status_code=400, detail=f"No existe autenticador para '{default_auth}'")

    return await auth.get_json_schema(str(node_id))
