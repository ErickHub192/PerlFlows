# app/ai/handlers/stripe_create_charge_handler.py

import time
import httpx
from typing import Dict, Any
from .connector_handler import ActionHandler
from app.connectors.factory import register_tool, register_node

@register_node("Stripe.create_charge")
@register_tool("Stripe.create_charge")
class StripeCreateChargeHandler(ActionHandler):
    """
    Handler para la acción Stripe.create_charge.
    Usa el endpoint POST https://api.stripe.com/v1/charges.
    """

    CHARGES_URL = "https://api.stripe.com/v1/charges"

    def __init__(self, creds: Dict[str, Any]):
        # creds debe incluir 'api_key' (tu clave secreta de Stripe)
        self.api_key: str = creds["api_key"]

    async def execute(
        self,
        params: Dict[str, Any],
        creds: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Parámetros en `params`:
          - amount      (int):    Monto en la menor unidad (centavos) (requerido)
          - currency    (str):    Código ISO, p. ej. "mxn" (requerido)
          - source      (str):    Token de fuente, p. ej. "tok_visa" (requerido)
          - customer_id (str):    ID de cliente existente (opcional)
        """
        start = time.perf_counter()
        payload: Dict[str, Any] = {
            "amount":   params["amount"],
            "currency": params["currency"],
            "source":   params["source"]
        }
        # Añadir customer si existe
        if "customer_id" in params:
            payload["customer"] = params["customer_id"]

        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Stripe espera datos de formulario
                resp = await client.post(self.CHARGES_URL, data=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            return {
                "status":      "error",
                "output":      None,
                "error":       str(e),
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }

        # Si devuelve 'id', fue exitoso
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
                "error":       data.get("error", data.get("message", "Unknown error")),
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
