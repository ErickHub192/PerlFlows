# app/routers/connector_router.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.services.connector_service import ConnectorService 
from app.services.connector_service import get_connector_service
from app.dtos.node_dto import NodeDTO

router = APIRouter(
    prefix="/api/connectors",
    tags=["connectors"]
)

@router.get(
    "",
    response_model=List[NodeDTO],
    summary="Lista todos los conectores disponibles"
)
async def list_connectors(
    svc: ConnectorService = Depends(get_connector_service)
) -> List[NodeDTO]:
    """
    Retorna el catálogo de conectores (nodos) con sus metadatos:
      - node_id
      - name
      - default_auth
      - actions (lista de {action_id, name})
    """
    try:
        return await svc.list_connectors()
    except Exception as e:
        # Ponemos un HTTP 500 en caso de fallo inesperado
        raise HTTPException(status_code=500, detail=str(e))
