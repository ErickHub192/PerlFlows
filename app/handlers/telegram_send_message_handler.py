# app/ai/handlers/telegram_send_message_handler.py

import time
import httpx
from typing import Dict, Any
from uuid import UUID
from .connector_handler import ActionHandler
from app.connectors.factory import register_tool, register_node
from app.exceptions import requires_parameters, param

@register_node("Telegram.send_message")
@register_tool("Telegram.send_message")
@requires_parameters(
    param("chat_id", str, True, description="ID del chat o username"),
    param("message", str, True, description="Mensaje a enviar")
)
class TelegramSendMessageHandler(ActionHandler):
    """
    Handler para la acción Telegram.send_message.
    Usa el endpoint POST https://api.telegram.org/bot<token>/sendMessage.
    """

    def __init__(self, creds: Dict[str, Any]):
        # creds debe incluir la clave 'bot_token'
        self.bot_token: str = creds["bot_token"]

    async def execute(
        self,
        params: Dict[str, Any],
        creds: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta sendMessage en Telegram Bot API.
        Parámetros esperados en `params`:
          - chat_id (str): ID de chat o '@username'
          - message (str): texto del mensaje
        """
        start = time.perf_counter()
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": params["chat_id"],
            "text":    params["message"]
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            # Error HTTP o de red
            return {
                "status":      "error",
                "output":      None,
                "error":       str(e),
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }

        # Telegram devuelve { "ok": true, "result": { ... } } si tuvo éxito :contentReference[oaicite:0]{index=0}
        if data.get("ok"):
            return {
                "status":      "success",
                "output":      data["result"],
                "error":       None,
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
        else:
            # En caso de fallo, Telegram incluye 'description' en la respuesta :contentReference[oaicite:1]{index=1}
            return {
                "status":      "error",
                "output":      data.get("result"),
                "error":       data.get("description"),
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
