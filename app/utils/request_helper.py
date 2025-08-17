from typing import Any, Dict, Optional
import httpx
from app.core.http_client import http_client, semaphore

async def request_helper(
    method: str,
    url: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    data: Any = None,
    json: Any = None,
    auth: Any = None,
    timeout: Optional[float] = None,
) -> httpx.Response:
    """Simple wrapper around the shared httpx client with semaphore."""
    async with semaphore:
        resp = await http_client.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            data=data,
            json=json,
            auth=auth,
            timeout=timeout,
        )
    return resp

