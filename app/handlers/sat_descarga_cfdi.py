import asyncio
import os
import time
import zipfile
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional
import tempfile

from app.connectors.factory import register_node
from app.handlers.connector_handler import ActionHandler
from app.clients.sat_ws_client import SATWSClient

# Contador simple de requests por RFC/día
REQUEST_COUNTER: Dict[str, int] = {}
MAX_REQUESTS_PER_DAY = 50


@register_node("SAT.descarga_cfdi")
class SATDescargaCFDIHandler(ActionHandler):
    """Nodo para descargar CFDI mediante el Web Service del SAT."""

    def __init__(self, creds: Dict[str, Any]):
        self.cer: bytes = creds["cer"]
        self.key: bytes = creds["key"]
        self.password: str = creds["password"]
        self.client = SATWSClient()

    async def execute(
        self,
        params: Dict[str, Any],
        creds: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        start = time.perf_counter()

        fecha_inicio = params["fecha_inicio"]
        fecha_fin = params["fecha_fin"]
        tipo = params.get("tipo", "I")
        rfc = params["rfc"]

        # Control de cuota por RFC/día
        counter_key = f"{rfc}-{date.today().isoformat()}"
        if REQUEST_COUNTER.get(counter_key, 0) >= MAX_REQUESTS_PER_DAY:
            return {
                "status": "error",
                "output": None,
                "error": "Límite diario de descargas alcanzado",
                "duration_ms": int((time.perf_counter() - start) * 1000),
            }
        REQUEST_COUNTER[counter_key] = REQUEST_COUNTER.get(counter_key, 0) + 1

        dest_param = params.get("dest_dir")
        if dest_param:
            dest_dir = Path(dest_param)
            dest_dir.mkdir(parents=True, exist_ok=True)
        else:
            dest_dir = Path(tempfile.mkdtemp(prefix="sat_cfdi_", dir="/tmp"))
            os.chmod(dest_dir, 0o700)

        token = await self.client.authenticate(self.cer, self.key, self.password)
        request_id = await self.client.request_cdfi(token, fecha_inicio, fecha_fin, tipo)

        status = {}
        for _ in range(params.get("poll_retries", 3)):
            status = await self.client.poll_status(token, request_id)
            if status.get("estado") == "terminado" or status.get("status") == "ready":
                break
            await asyncio.sleep(params.get("poll_interval", 1))

        paquetes = status.get("paquetes", [])
        archivos = []
        for pid in paquetes:
            data = await self.client.download_package(token, pid)
            pkg_zip = dest_dir / f"{pid}.zip"
            pkg_zip.write_bytes(data)
            with zipfile.ZipFile(pkg_zip) as zf:
                zf.extractall(dest_dir / pid)
            for fname in os.listdir(dest_dir / pid):
                if fname.lower().endswith(".xml"):
                    archivos.append(str(dest_dir / pid / fname))
        return {
            "status": "success",
            "output": {"file_paths": archivos},
            "duration_ms": int((time.perf_counter() - start) * 1000),
        }
