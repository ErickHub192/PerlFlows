import asyncio
from uuid import UUID
import redis
from rq import Worker, Queue, Connection

from app.core.config import settings
from app.db.database import async_session
from app.db.models import AgentStatus, AIAgent
from app.db.repositories.agent_run_repository import AgentRunRepository
from app.agent.run_manager import RunManager
from app.ai.memories.manager import MemoryManager
from app.services.kyra_agent_service import get_kyra_agent_service


async def _execute_run(run_id: UUID) -> None:
    """Load run info and execute it using KyraAgentService."""
    async with async_session() as session:
        repo = AgentRunRepository(session)
        manager = RunManager(repo, session)

        run = await repo.get_run(run_id)
        if run is None:
            return
        agent = await session.get(AIAgent, run.agent_id)
        if agent is None:
            return

        memory = MemoryManager(agent.memory_schema or {})
        # INTEGRACIÓN: Usar factory para obtener servicio completamente integrado
        # Nota: Aquí usaríamos dependency injection en un contexto real, 
        # pero para el worker necesitamos instanciar manualmente
        from app.ai.llm_clients.llm_service import get_llm_service
        from app.services.workflow_runner_service import get_workflow_runner
        from app.services.cag_service import get_cag_service
        from app.workflow_engine.llm.llm_workflow_planner import get_unified_workflow_planner
        
        # Crear instancias manuales para el worker context
        llm_service = get_llm_service()
        workflow_runner = get_workflow_runner()
        cag_service = get_cag_service(session)
        workflow_planner = await get_unified_workflow_planner()
        
        service = get_kyra_agent_service(
            llm_service=llm_service,
            workflow_runner=workflow_runner, 
            cag_service=cag_service,
            workflow_planner=workflow_planner
        )
        await manager.update_status(run_id, AgentStatus.running)

        system_prompt = ""
        if isinstance(run.result, dict):
            system_prompt = run.result.get("system_prompt", "")
        system_prompt = system_prompt or (agent.default_prompt or "")

        await service.run(
            run_manager=manager,
            memory_manager=memory,
            agent_id=agent.agent_id,
            run_id=run_id,
            steps=None,
            user_id=0,
            system_prompt=system_prompt,
            user_prompt=run.goal or "",
        )


def run_agent(run_id: str) -> None:
    asyncio.run(_execute_run(UUID(run_id)))


def start_worker() -> None:
    redis_conn = redis.Redis.from_url(settings.REDIS_URL)
    with Connection(redis_conn):
        worker = Worker([Queue("agent_runs", connection=redis_conn)])
        worker.work()


if __name__ == "__main__":
    start_worker()
