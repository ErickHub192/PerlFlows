# app/core/http_client.py

import asyncio
import httpx
from app.core.config import settings

# Semáforo para no saturar concurrencia de HTTP o DB
semaphore = asyncio.Semaphore(settings.DB_MAX_CONCURRENT_QUERIES)

# Límites de conexiones y keep‑alive
_limits = httpx.Limits(
    max_connections=settings.HTTPX_MAX_CONNECTIONS,
    max_keepalive_connections=settings.HTTPX_MAX_KEEPALIVE,
)

# Timeouts: connect, read, write y pool
_timeout = httpx.Timeout(
    connect=settings.HTTPX_CONNECT_TIMEOUT,
    read=settings.HTTPX_READ_TIMEOUT,
    write=settings.HTTPX_READ_TIMEOUT,
    pool=settings.HTTPX_CONNECT_TIMEOUT,
)

# Cliente global reutilizable, exportado como http_client
http_client: httpx.AsyncClient = httpx.AsyncClient(
    limits=_limits,
    timeout=_timeout,
    follow_redirects=True,
)
