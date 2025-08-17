"""Cliente sencillo para el Web Service de Descarga Masiva CFDI v1.5."""

from typing import Any, Dict

try:  # httpx might be absent in some testing environments
    import httpx  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - handled in tests
    httpx = None

__all__ = ["SATWSClient"]

class SATWSClient:
    """Cliente para el Web Service de Descarga Masiva CFDI v1.5."""

    BASE_URL = "https://descargacfdi.sat.gob.mx/api/v1"

    async def authenticate(self, cer: bytes, key: bytes, password: str) -> str:
        if httpx is None:
            raise RuntimeError("httpx package is required")
        payload = {"cer": cer, "key": key, "password": password}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.BASE_URL}/authenticate", files=payload)
            resp.raise_for_status()
            return resp.json()["token"]

    async def request_cdfi(self, token: str, fecha_inicio: str, fecha_fin: str, tipo: str) -> str:
        if httpx is None:
            raise RuntimeError("httpx package is required")
        headers = {"Authorization": f"Bearer {token}"}
        data = {"fechaInicial": fecha_inicio, "fechaFinal": fecha_fin, "tipo": tipo}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.BASE_URL}/solicita", json=data, headers=headers)
            resp.raise_for_status()
            return resp.json()["id"]

    async def poll_status(self, token: str, request_id: str) -> Dict[str, Any]:
        if httpx is None:
            raise RuntimeError("httpx package is required")
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.BASE_URL}/verifica/{request_id}", headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def download_package(self, token: str, package_id: str) -> bytes:
        if httpx is None:
            raise RuntimeError("httpx package is required")
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(f"{self.BASE_URL}/descarga/{package_id}", headers=headers)
            resp.raise_for_status()
            return resp.content
