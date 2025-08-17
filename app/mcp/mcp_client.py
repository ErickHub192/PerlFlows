# app/mcp_client.py
"""
Módulo wrapper para interactuar con un servidor MCP vía stdio,
utilizando el SDK oficial de MCP.
"""
import sys
from typing import Any, List, Optional, Dict

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


class MCPClient:
    """
    Cliente MCP basado en stdio.

    Lanza el script mcp_tools.py como proceso hijo y se comunica
    por stdin/stdout usando el protocolo MCP oficial.
    """
    def __init__(
        self,
        command: str = sys.executable,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
    ):
        # Parámetros para stdio_client
        self.params = StdioServerParameters(
            command=command,
            args=args or ["mcp_tools.py"],
            env=env,
        )
        self._stdio = None
        self._write = None
        self._session: Optional[ClientSession] = None

    async def _ensure_connected(self) -> None:
        if self._session is not None:
            return
        # Inicia el proceso MCP y la sesión
        self._stdio, self._write = await stdio_client(self.params).__aenter__()
        self._session = await ClientSession(self._stdio, self._write).__aenter__()
        await self._session.initialize()

    async def list_tools(self) -> Any:
        """
        Lista las herramientas expuestas por el servidor MCP.
        """
        await self._ensure_connected()
        return await self._session.list_tools()

    async def call_tool(self, name: str, input: Dict[str, Any]) -> Any:
        """
        Invoca la tool `name` con el payload `input` y devuelve la respuesta.
        """
        await self._ensure_connected()
        return await self._session.call_tool(name=name, input=input)

    async def close(self) -> None:
        """
        Cierra la sesión MCP y el proceso hijo.
        """
        if self._session is not None:
            await self._session.__aexit__(None, None, None)
            await self._stdio.__aexit__(None, None, None)
            self._session = None
