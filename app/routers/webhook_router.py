from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Request, Depends

from app.core.config import settings
from app.services.workflow_runner_service import (
    get_workflow_runner,
    WorkflowRunnerService,
)
from app.services.flow_definition_service import (
    get_flow_definition_service,
    FlowDefinitionService,
)
from app.repositories.webhook_event_repository import (
    get_webhook_event_repository,
    WebhookEventRepository,
)

router = APIRouter(prefix="/api")

ACTIVE_WEBHOOKS: Dict[str, Dict[str, Any]] = {}


def build_webhook_url(path: str) -> str:
    base = settings.API_BASE_URL.rstrip("/")
    return f"{base}{path}"


def register_webhook(flow_id: UUID, user_id: int, trigger_args: Dict[str, Any]):
    path = trigger_args["production_path"]
    methods = trigger_args.get("methods", ["POST"])
    respond = trigger_args.get("respond", "immediate")

    async def _endpoint(
        request: Request,
        background_tasks: BackgroundTasks,
        runner: WorkflowRunnerService = Depends(get_workflow_runner),
        def_service: FlowDefinitionService = Depends(get_flow_definition_service),
        repo: WebhookEventRepository = Depends(get_webhook_event_repository),
    ):
        payload = None
        if request.method in {"POST", "PUT", "PATCH"}:
            try:
                payload = await request.json()
            except Exception:
                payload = None
        else:
            payload = dict(request.query_params)
        headers = {k: v for k, v in request.headers.items()}
        await repo.create_event(flow_id, path, request.method, payload, headers)

        async def run_flow():
            spec = await def_service.get_flow_spec(flow_id)
            await runner.run_workflow(flow_id, spec["steps"], user_id, payload or {}, simulate=False)

        if respond == "immediate":
            background_tasks.add_task(run_flow)
            return {"status": "received"}
        else:
            await run_flow()
            return {"status": "completed"}

    endpoint_router = APIRouter()
    endpoint_router.add_api_route(path, _endpoint, methods=methods)
    from main import app

    app.include_router(endpoint_router)
    ACTIVE_WEBHOOKS[path] = {"flow_id": str(flow_id), "url": build_webhook_url(path)}
    return path  # Return webhook_id (using path as ID)


def unregister_webhook(path: str):
    ACTIVE_WEBHOOKS.pop(path, None)


@router.get("/triggers")
async def list_triggers() -> Dict[str, Any]:
    return list(ACTIVE_WEBHOOKS.values())
