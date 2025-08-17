# app/ai/handlers/slack_handler.py

import httpx, time
from uuid import UUID
from typing import Any, Dict
from .connector_handler import ActionHandler
from app.connectors.factory import register_tool, register_node

@register_node("Slack.post_message")
@register_tool("Slack.post_message")
class SlackHandler(ActionHandler):
    def __init__(self, creds: Dict[str, Any]):
        self.token = creds['access_token']

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # aquí podrías mapear action_id → ruta/método Slack; o mejor, tus metadatos ya indican endpoint
        start = time.perf_counter()
        url = "https://slack.com/api/chat.postMessage"
        headers = {"Authorization": f"Bearer {self.token}"}
        body = {
          "channel": params["channel"],
          "text":    params["message"],
        }
        async with httpx.AsyncClient() as cli:
            resp = await cli.post(url, headers=headers, json=body)
            data = resp.json()
        return {
          "status":      "success"    if data.get("ok") else "error",
          "output":      data,
          "error":       None         if data.get("ok") else data.get("error"),
          "duration_ms": int((time.perf_counter() - start)*1000)
        }
