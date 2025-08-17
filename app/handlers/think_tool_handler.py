# app/handlers/think_tool_handler.py

import time
from typing import Any, Dict
from uuid import UUID

from app.ai.config_loader import load_agent_config
from app.ai.llm_factory import create as create_llm_client
from app.handlers.connector_handler import ActionHandler
from app.connectors.factory import register_tool, register_node

@register_node("think")
@register_tool("think")
class ThinkToolHandler(ActionHandler):
    """
    Think Tool: permite al agente generar una reflexión interna
    (“chain of thought”) sin enviarla al usuario final.
    """

    def __init__(self, creds: Dict[str, Any]):
        super().__init__(creds)
        self.creds = creds

    async def execute(
        self,
        params: Dict[str, Any],
        creds: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        start = time.perf_counter()

        # 1) Cargar configuración del agente para obtener modelo y temperatura
        agent_id = UUID(self.creds["agent_id"])
        cfg = await load_agent_config(agent_id)

        # 2) Instanciar cliente LLM
        api_key = self.creds.get("api_key")
        llm = create_llm_client(api_key=api_key, model=cfg.model)

        # 3) Construir prompt de reflexión
        topic = params.get("topic") or params.get("prompt") or ""
        system_msg = (
            "Esta herramienta te ayuda a reflexionar internamente. "
            "Genera tu cadena de pensamiento sin darle salida al usuario."
        )
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user",   "content": f"Think step: {topic}"}
        ]

        # 4) Llamar al LLM para generar la reflexión
        try:
            resp = await llm.chat_completion(
                messages=messages,
                temperature=cfg.temperature
            )
            thought = resp.choices[0].message.content or ""
        except Exception as e:
            return {
                "status":      "error",
                "output":      None,
                "error":       f"Think tool failed: {e}",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }

        # 5) Devolver la reflexión
        return {
            "status":      "success",
            "output":      {"thought": thought},
            "duration_ms": int((time.perf_counter() - start) * 1000)
        }
