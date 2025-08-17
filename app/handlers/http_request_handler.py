import time
import asyncio
from typing import Any, Dict, Optional
import base64
import httpx

from app.handlers.connector_handler import ActionHandler
from app.connectors.factory import register_node, register_tool
from app.utils.request_helper import request_helper

@register_node("HTTP_Request.request")
@register_tool("HTTP_Request.request")
class HttpRequestHandler(ActionHandler):
    """Nodo universal para realizar peticiones HTTP externas."""

    async def execute(
        self,
        params: Dict[str, Any],
        creds: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Ejecuta la solicitud HTTP.

        Parámetros en ``params``:
            - ``method`` (str): Verbo HTTP (GET, POST, ...).
            - ``url`` (str): URL completa del recurso.
            - ``headers`` (dict, opcional): Headers adicionales.
            - ``queryParams`` (dict, opcional): Parámetros de query.
            - ``body`` (cualquiera, opcional): Datos del cuerpo.
            - ``bodyType`` (str, opcional): ``raw`` | ``json`` | ``form``.
            - ``auth`` (dict, opcional):
                ``{"type": "bearer", "token": "..."}``
                ``{"type": "basic", "username": "u", "password": "p"}``
                ``{"type": "apiKey", "header": "X-API-KEY", "key": "..."}``
        """
        start = time.perf_counter()
        method = str(params.get("method", "")).upper()
        url = params.get("url")
        if not method or not url:
            return {
                "status": "error",
                "output": None,
                "error": "'method' y 'url' son requeridos",
                "duration_ms": int((time.perf_counter() - start) * 1000),
            }

        headers = params.get("headers", {}) or {}
        query = params.get("queryParams", {}) or {}
        body = params.get("body")
        body_type = params.get("bodyType", "json")
        auth_cfg = params.get("auth")

        auth: Optional[httpx.Auth] = None
        if auth_cfg:
            atype = auth_cfg.get("type")
            if atype == "bearer" and auth_cfg.get("token"):
                headers.setdefault("Authorization", f"Bearer {auth_cfg['token']}")
            elif atype == "basic" and auth_cfg.get("username") is not None:
                cred = f"{auth_cfg.get('username')}:{auth_cfg.get('password','')}"
                b64 = base64.b64encode(cred.encode()).decode()
                headers.setdefault("Authorization", f"Basic {b64}")
            elif atype == "apiKey" and auth_cfg.get("key"):
                hname = auth_cfg.get("header", "X-API-KEY")
                headers.setdefault(hname, auth_cfg["key"])

        data = None
        json_data = None
        if body is not None:
            if body_type == "raw":
                data = body
            elif body_type == "form":
                data = body
            else:
                json_data = body

        delay = 0.5
        retries = params.get("retries", 2)
        for attempt in range(retries + 1):
            try:
                resp = await request_helper(
                    method=method,
                    url=url,
                    headers=headers,
                    params=query,
                    data=data,
                    json=json_data,
                    auth=auth,
                )
                resp.raise_for_status()
                try:
                    content = resp.json()
                except Exception:
                    content = resp.text
                return {
                    "status": "success",
                    "output": {
                        "status_code": resp.status_code,
                        "body": content,
                    },
                    "duration_ms": int((time.perf_counter() - start) * 1000),
                }
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < retries:
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                return {
                    "status": "error",
                    "output": None,
                    "error": str(e),
                    "duration_ms": int((time.perf_counter() - start) * 1000),
                }
            except Exception as e:
                if attempt < retries:
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                return {
                    "status": "error",
                    "output": None,
                    "error": str(e),
                    "duration_ms": int((time.perf_counter() - start) * 1000),
                }

