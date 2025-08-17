from typing import Optional, List, Dict, Any
from uuid import UUID
import asyncio
import redis
from rq import Queue

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from app.core.config import settings
from app.db.database import get_db
from app.db.models import AgentRun, AgentStatus, AIAgent
from app.db.repositories.agent_run_repository import AgentRunRepository
from app.db.repositories.iagent_run_repository import IAgentRunRepository
from .planner import Planner

from .guardrails import Guardrail
from app.telemetry.agent_instrumentation import start_span

from app.connectors.factory import execute_tool


class RunManager:
    """Gestiona la cola de ejecución de agentes utilizando Redis/RQ."""

    REFLECT_INTERVAL = 3

    def __init__(self, repo: IAgentRunRepository, session: AsyncSession):
        self.repo = repo
        self.session = session
        self._redis = redis.Redis.from_url(settings.REDIS_URL)
        self._queue = Queue("agent_runs", connection=self._redis)

    async def queue_run(
        self,
        agent_id: UUID,
        goal: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> AgentRun:
        """Crea un AgentRun con estado 'queued' y lo encola.

        Guarda el prompt de contexto para usarlo luego en el worker.
        """

        result = {"system_prompt": system_prompt} if system_prompt else None
        run = AgentRun(
            agent_id=agent_id,
            goal=goal,
            result=result,
            status=AgentStatus.queued,
        )
        run = await self.repo.create_run(run)

        # Generar y persistir el plan si existe un goal
        if goal is not None:
            agent: AIAgent | None = await self.session.get(AIAgent, agent_id)
            if agent is not None:
                planner = Planner()
                async with start_span("planner", agent_id=str(agent_id), run_id=str(run.run_id), tool_slug=""):
                    plan = await planner.plan(goal, agent.tools or [])
                await self.session.execute(
                    update(AIAgent)
                    .where(AIAgent.agent_id == agent_id)
                    .values(planner_state=plan)
                )
                await self.session.commit()

        self._queue.enqueue("app.worker.run_worker.run_agent", str(run.run_id))
        return run

    async def update_status(self, run_id: UUID, status: AgentStatus) -> None:
        """Actualiza el estado del AgentRun."""
        await self.session.execute(
            update(AgentRun).where(AgentRun.run_id == run_id).values(status=status)
        )
        await self.session.commit()

    async def pause_run(self, run_id: UUID) -> None:
        await self.update_status(run_id, AgentStatus.paused)

    async def resume_run(self, run_id: UUID) -> None:
        await self.update_status(run_id, AgentStatus.running)

    async def run(self, run_id: UUID) -> None:
        """Ejecuta los pasos planificados para un run."""
        run = await self.repo.get_run(run_id)
        if run is None:
            return
        agent: AIAgent | None = await self.session.get(AIAgent, run.agent_id)
        if agent is None or not agent.planner_state:
            return

        await self.update_status(run_id, AgentStatus.running)
        from app.connectors.connector_client import ConnectorClient
        from app.ai.memories.manager import MemoryManager
        from .tool_router import ToolRouter

        connector_client = ConnectorClient()
        mem_mgr = MemoryManager(agent.memory_schema or {})
        router = ToolRouter()
        results: List[Any] = []
        step_count = 0
        plan: List[str] = list(agent.planner_state)
        i = 0

        while i < len(plan):
            step = plan[i]
            connectors = await connector_client.fetch_connectors()
            tool = await router.select_tool(step, connectors)

            if tool is None or not getattr(tool, "actions", None):
                reflect_needed = True
            else:
                action = tool.actions[0]
                action_id = getattr(action, "action_id", None) or action.get("action_id")
                res = await connector_client.execute_action(tool.node_id, action_id, {}, creds=None)
                await mem_mgr.append_short_term(agent.agent_id, {"step": step, "result": res})
                results.append(res)
                reflect_needed = False

            step_count += 1
            if reflect_needed or step_count % self.REFLECT_INTERVAL == 0:
                r = await execute_tool(
                    "reflect",
                    {"recent_steps": results, "goal": run.goal},
                    {"agent_id": str(agent.agent_id)},
                )
                next_step = r.get("output", {}).get("next_step")
                if next_step:
                    plan.insert(i + 1, next_step)
                await self.session.execute(
                    update(AIAgent)
                    .where(AIAgent.agent_id == agent.agent_id)
                    .values(planner_state=plan)
                )
                await self.session.commit()

            i += 1

        run.result = results
        await self.session.commit()
        await self.update_status(run_id, AgentStatus.succeeded)


async def get_run_manager(db: AsyncSession = Depends(get_db)) -> "RunManager":
    repo = AgentRunRepository(db)
    return RunManager(repo, db)
