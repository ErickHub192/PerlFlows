# app/ai/handlers/hubspot_create_contact_handler.py

import time
import httpx
from typing import Dict, Any
from app.handlers.connector_handler import ActionHandler
from app.connectors.factory import register_tool, register_node

@register_node("HubSpot.create_contact")
@register_tool("HubSpot.create_contact")
class HubSpotCreateContactHandler(ActionHandler):
    """
    Handler para la acción HubSpot.create_contact.
    Usa el endpoint POST https://api.hubapi.com/crm/v3/objects/contacts.
    """

    CREATE_URL = "https://api.hubapi.com/crm/v3/objects/contacts"

    def __init__(self, creds: Dict[str, Any]):
        # creds debe incluir 'access_token'
        self.access_token: str = creds["access_token"]

    async def execute(
        self,
        params: Dict[str, Any],
        creds: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Parámetros en `params`:
          - email     (str): correo del contacto (requerido)
          - firstname (str): nombre (opcional)
          - lastname  (str): apellido (opcional)
        """
        start = time.perf_counter()
        payload = {
            "properties": {
                "email":     params["email"],
                **({"firstname": params["firstname"]} if "firstname" in params else {}),
                **({"lastname":  params["lastname"]}  if "lastname" in params  else {})
            }
        }
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type":  "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self.CREATE_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            return {
                "status":      "error",
                "output":      None,
                "error":       str(e),
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }

        # Si la respuesta incluye 'id', consideramos éxito
        if data.get("id"):
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
                "error":       data.get("message", "Unknown error"),
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
