# app/connectors/handlers/outlook_send_mail.py

import time
from typing import Any, Dict
import httpx
from app.connectors.factory import register_tool, register_node
from .connector_handler import ActionHandler

@register_node("Outlook.send_mail")
@register_tool("Outlook.send_mail")
class OutlookSendMailHandler(ActionHandler):
    """
    Handler para la acción 'send_mail' de Outlook.
    Parámetros en params:
      - from    (str, opcional): correo remitente (requiere permisos send-as).
      - email   (str, requerido): correo destinatario.
      - subject (str, requerido): asunto del mensaje.
      - message (str, requerido): cuerpo del mensaje.
    """

    def __init__(self, creds: Dict[str, Any]):
        # creds debe incluir 'access_token' válido con el scope Mail.Send
        self.token = creds.get("access_token")

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start_ts = time.perf_counter()

        url = "https://graph.microsoft.com/v1.0/me/sendMail"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type":  "application/json"
        }

        # Construye el objeto message según la API
        msg = {
            "message": {
                "subject": params["subject"],
                "body": {
                    "contentType": "Text",
                    "content":     params["message"]
                },
                "toRecipients": [
                    { "emailAddress": { "address": params["email"] } }
                ]
            },
            "saveToSentItems": True
        }

        # Si se proporcionó remitente explícito y el token lo permite
        if params.get("from"):
            msg["message"]["from"] = {
                "emailAddress": { "address": params["from"] }
            }

        try:
            async with httpx.AsyncClient() as cli:
                resp = await cli.post(url, headers=headers, json=msg)
                resp.raise_for_status()
            status, output, error = "success", None, None

        except httpx.HTTPStatusError as exc:
            status = "error"
            output = None
            error  = f"{exc.response.status_code}: {exc.response.text}"
        except Exception as exc:
            status = "error"
            output = None
            error  = str(exc)

        duration_ms = int((time.perf_counter() - start_ts) * 1000)
        return {
            "status":      status,
            "output":      output,
            "error":       error,
            "duration_ms": duration_ms
        }
