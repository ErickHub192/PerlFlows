# app/ai/handlers/whatsapp_send_template_handler.py

import time
import httpx
from typing import Dict, Any
from .connector_handler import ActionHandler
from app.connectors.factory import register_tool, register_node


@register_node("WhatsApp_Business.send_template")
@register_tool("WhatsApp_Business.send_template")
class WhatsAppSendTemplateHandler(ActionHandler):
    """
    Handler para la acción WhatsApp Business – send_template.
    Usa el endpoint POST https://graph.facebook.com/{version}/{phone_number_id}/messages
    """

    API_VERSION = "v22.0"  # Ajusta según tu configuración de Graph API

    def __init__(self, creds: Dict[str, Any]):
        # creds debe incluir 'access_token'
        self.access_token: str = creds["access_token"]

    async def execute(
        self,
        params: Dict[str, Any],
        creds: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta send_template en WhatsApp Business Cloud API.
        Parámetros esperados en `params`:
          - phone_number_id (str): ID del número de WhatsApp Business
          - to (str): número destino, p. ej. "5215512345678"
          - template_name (str): nombre de la plantilla aprobada
          - language (str): código de idioma, p. ej. "es_MX"
          - components (list, opcional): lista de componentes de plantilla
        """
        start = time.perf_counter()
        version = params.get("api_version", self.API_VERSION)
        phone_number_id = params["phone_number_id"]
        url = f"https://graph.facebook.com/{version}/{phone_number_id}/messages"

        # Construir payload
        payload: Dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type":    "individual",
            "to":                params["to"],
            "type":              "template",
            "template": {
                "name":     params["template_name"],
                "language": {"code": params["language"]}
            }
        }
        # Añadir componentes si vienen en params
        if "components" in params:
            payload["template"]["components"] = params["components"]

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type":  "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            return {
                "status":      "error",
                "output":      None,
                "error":       str(e),
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }

        # Graph API devuelve 'messages' en caso de éxito
        if "messages" in data:
            return {
                "status":      "success",
                "output":      data,
                "error":       None,
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
        else:
            return {
                "status":      "error",
                "output":      data,
                "error":       data.get("error", "Unknown error"),
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
