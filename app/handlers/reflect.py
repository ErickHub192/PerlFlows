# app/connectors/handlers/reflect.py

import json
import time
from typing import Any, Dict

from app.connectors.factory import register_tool, register_node
from app.handlers.connector_handler import ActionHandler
from app.ai.llm_clients.llm_service import get_llm_service

@register_node("reflect")
@register_tool("reflect", usage_mode="tool")
class ReflectHandler(ActionHandler):
    """Tool that critiques recent steps and proposes the next action."""

    def __init__(self, creds: Dict[str, Any]):
        super().__init__()  # ActionHandler doesn't take arguments
        self.creds = creds
        self.llm = get_llm_service()

    async def execute(
        self,
        params: Dict[str, Any],
        creds: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        start = time.perf_counter()
        goal = params.get("goal", "")
        recent = params.get("recent_steps", [])
        system_msg = (
            "Dado el objetivo y los pasos recientes del agente, "
            "devuelve un JSON con 'critique' y 'next_step'."
        )
        messages = [
            {"role": "system", "content": system_msg},
            {
                "role": "user",
                "content": f"Goal: {goal}\nRecent steps: {json.dumps(recent)}",
            },
        ]
        try:
            resp = await self.llm.chat_completion(messages=messages, temperature=0.0)
            content = getattr(resp.choices[0].message, "content", "{}")
            data = json.loads(content)
            return {
                "status": "success",
                "output": {
                    "critique": data.get("critique", ""),
                    "next_step": data.get("next_step", ""),
                },
                "duration_ms": int((time.perf_counter() - start) * 1000),
            }
        except Exception as e:
            return {
                "status": "error",
                "output": None,
                "error": f"Reflect failed: {e}",
                "duration_ms": int((time.perf_counter() - start) * 1000),
            }
