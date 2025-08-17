# app/ai/config_loader.py

from uuid import UUID

from app.db.database import async_session
from app.repositories.ai_agent_repository import AIAgentRepository
from app.services.ai_agent_service import AIAgentService
from app.models.agent_config import AgentConfig


class AgentNotFoundError(Exception):
    """Se lanza cuando no se encuentra la configuración para el agent_id dado."""
    pass


async def load_agent_config(agent_id: UUID) -> AgentConfig:
    """
    Carga y mapea a AgentConfig la configuración del agente desde la base de datos.

    :param agent_id: UUID del agente a cargar.
    :return: Instancia de AgentConfig.
    :raises AgentNotFoundError: Si no existe ningún agente con ese ID.
    """
    async with async_session() as session:
        repository = AIAgentRepository(session)
        service = AIAgentService(repository)
        dto = await service.get_agent(agent_id)

    if not dto:
        raise AgentNotFoundError(f"Agent {agent_id} not found")

    return AgentConfig(
        agent_id=dto.agent_id,
        name=dto.name,
        default_prompt=dto.default_prompt,
        tools=dto.tools,
        memory_schema=dto.memory_schema,
        model=dto.model,
        max_iterations=dto.max_iterations,
        temperature=getattr(dto, "temperature", 0.7),
    )
