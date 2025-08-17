# app/ai/handlers/salesforce_create_lead_handler.py

import time
import httpx
from typing import Dict, Any
from .connector_handler import ActionHandler
from app.connectors.factory import register_tool, register_node

@register_node("Salesforce.create_lead")
@register_tool("Salesforce.create_lead")
class SalesforceCreateLeadHandler(ActionHandler):
    """
    Handler para la acción Salesforce.create_lead.
    Usa el endpoint POST /services/data/vXX.X/sobjects/Lead/.
    """

    API_VERSION = "v56.0"  # Ajusta según tu Org
    BASE_URL    = "https://yourInstance.salesforce.com"

    def __init__(self, creds: Dict[str, Any]):
        # creds debe incluir 'access_token'
        self.access_token: str = creds["access_token"]

    async def execute(
        self,
        params: Dict[str, Any],
        creds: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Parámetros esperados en `params`:
          - last_name  (str): apellido del lead (requerido)
          - company    (str): nombre de la empresa (requerido)
          - first_name (str): nombre del lead (opcional)
          - email      (str): correo del lead (opcional)
        """
        start = time.perf_counter()
        url = f"{self.BASE_URL}/services/data/v{self.API_VERSION}/sobjects/Lead/"

        # Construir payload mandatorio y opcional
        payload: Dict[str, Any] = {
            "LastName": params["last_name"],
            "Company":  params["company"]
        }
        if "first_name" in params:
            payload["FirstName"] = params["first_name"]
        if "email" in params:
            payload["Email"] = params["email"]

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

        # Verificar éxito por la presencia de 'id'
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
