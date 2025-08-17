# app/ai/handlers/airtable_read_write_handler.py

import time
import httpx
from typing import Dict, Any
from .connector_handler import ActionHandler
from app.connectors.factory import register_tool, register_node
from app.core.service_urls import AIRTABLE_API_BASE, DEFAULT_TIMEOUT


@register_node("Airtable.read_write")
@register_tool("Airtable.read_write")
class AirtableReadWriteHandler(ActionHandler):
    """
    Handler para la acción Airtable – read_write.
    Soporta crear o actualizar un solo registro en una tabla Airtable.
    """


    def __init__(self, creds: Dict[str, Any]):
        # creds debe incluir 'api_key'
        self.api_key: str = creds["api_key"]

    async def execute(
        self,
        params: Dict[str, Any],
        creds: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Parámetros en `params`:
          - base_id (str)
          - table (str)
          - record (dict)
          - record_id (str, opcional)
        """
        start = time.perf_counter()
        base_id = params["base_id"]
        table   = params["table"]
        record  = params["record"]
        record_id = params.get("record_id")

        # Construir URL y método según si hay record_id
        if record_id:
            url = f"{AIRTABLE_API_BASE}/{base_id}/{table}/{record_id}"
            method = "PATCH"
            payload = {"fields": record}
        else:
            url = f"{AIRTABLE_API_BASE}/{base_id}/{table}"
            method = "POST"
            payload = {"fields": record}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                resp = await client.request(method, url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            return {
                "status":      "error",
                "output":      None,
                "error":       str(e),
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }

        # En create y update, Airtable devuelve el registro en 'id' y 'fields'
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
                "error":       data.get("error", "Unknown error"),
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
