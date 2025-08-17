import time
import httpx
import logging
from typing import Dict, Any

from app.handlers.connector_handler import ActionHandler
from app.connectors.factory import register_tool, register_node
from app.core.service_urls import GITHUB_API_BASE, DEFAULT_TIMEOUT

logger = logging.getLogger(__name__)

@register_node("GitHub.create_issue")
@register_tool("GitHub.create_issue")
class GitHubCreateIssueHandler(ActionHandler):
    """Handler para crear issues en GitHub."""


    def __init__(self, creds: Dict[str, Any]):
        self.token: str = creds["access_token"]

    async def execute(
        self,
        params: Dict[str, Any],
        creds: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        start = time.perf_counter()
        repo = params.get("repo")
        title = params.get("title")
        if not repo or not title:
            return {
                "status": "error",
                "output": None,
                "error": "'repo' and 'title' son requeridos",
                "duration_ms": int((time.perf_counter() - start) * 1000),
            }

        url = f"{GITHUB_API_BASE}/repos/{repo}/issues"
        payload: Dict[str, Any] = {"title": title}
        if "body" in params:
            payload["body"] = params["body"]
        if "assignees" in params:
            payload["assignees"] = params["assignees"]
        if "labels" in params:
            payload["labels"] = params["labels"]

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
        }

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("GitHub issue creation failed: %s", exc)
            return {
                "status": "error",
                "output": None,
                "error": str(exc),
                "duration_ms": int((time.perf_counter() - start) * 1000),
            }

        return {
            "status": "success",
            "output": data,
            "error": None,
            "duration_ms": int((time.perf_counter() - start) * 1000),
        }
