# app/services/flow_definition_service.py

from typing import Dict, Any
from uuid import UUID

from fastapi import Depends

from app.repositories.flow_definition_repository import FlowDefinitionRepository, get_flow_definition_repository

class FlowDefinitionService:
    """
    Servicio que implementa la obtención de spec de flujos.
    """
    def __init__(self, repo: FlowDefinitionRepository):
        self.repo = repo

    async def get_flow_spec(self, flow_id: UUID) -> Dict[str, Any]:
        # Delegar la obtención al repositorio
        return await self.repo.get_spec(flow_id)

async def get_flow_definition_service(
    repo: FlowDefinitionRepository = Depends(get_flow_definition_repository),
) -> FlowDefinitionService:
    """
    ✅ LIMPIADO: Factory sin interface innecesaria
    """
    return FlowDefinitionService(repo)
