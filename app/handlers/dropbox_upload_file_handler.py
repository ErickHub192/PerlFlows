# app/ai/handlers/dropbox_upload_file_handler.py

import time
import base64
import httpx
from typing import Dict, Any
from .connector_handler import ActionHandler
from app.connectors.factory import register_tool, register_node
from app.core.service_urls import DROPBOX_UPLOAD_URL, UPLOAD_TIMEOUT

@register_node("Dropbox.upload_file")
@register_tool("Dropbox.upload_file")
class DropboxUploadFileHandler(ActionHandler):
    """
    Handler para la acción Dropbox.upload_file.
    Usa el endpoint POST https://content.dropboxapi.com/2/files/upload
    """


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
          - path (str): ruta destino en Dropbox
          - autorename (bool, opcional)
          - content (str): Base64 del contenido del archivo
          - mute (bool, opcional)
        """
        start = time.perf_counter()

        # Decodificar Base64
        file_bytes = base64.b64decode(params["content"])

        # Construir arg JSON
        api_arg = {
            "path":       params["path"],
            "mode":       "add",
            "autorename": params.get("autorename", False),
            "mute":       params.get("mute", False)
        }

        headers = {
            "Authorization":    f"Bearer {self.access_token}",
            "Content-Type":     "application/octet-stream",
            "Dropbox-API-Arg":  httpx.json.dumps(api_arg)
        }

        try:
            async with httpx.AsyncClient(timeout=UPLOAD_TIMEOUT) as client:
                resp = await client.post(DROPBOX_UPLOAD_URL, content=file_bytes, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            return {
                "status":      "error",
                "output":      None,
                "error":       str(e),
                "duration_ms": int((time.time() - start) * 1000)
            }

        # Respuesta incluye 'id' y 'name' si tuvo éxito
        if data.get("id"):
            return {
                "status":      "success",
                "output":      data,
                "error":       None,
                "duration_ms": int((time.time() - start) * 1000)
            }
        else:
            return {
                "status":      "error",
                "output":      data,
                "error":       data.get("error_summary", "Unknown error"),
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
