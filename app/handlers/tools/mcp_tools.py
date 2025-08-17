#!/usr/bin/env python3
"""
MCP Tools Proxy

Expone las herramientas registradas como endpoints MCP.
Solo actúa como proxy al factory - NO duplica lógica de workflow engine.
"""
from fastmcp import FastMCP
from app.connectors.factory import scan_handlers, _TOOL_REGISTRY, execute_tool
from app.authenticators.auth import get_credentials_for_user

# Inicializar servidor MCP
tools_server = FastMCP("KyraTools")

# Escanear handlers para llenar registry
scan_handlers()

# Crear endpoints MCP para cada tool registrada
for tool_name in _TOOL_REGISTRY:
    def make_tool_fn(name: str):
        async def tool_fn(user_id: str, params: dict) -> dict:
            """Proxy directo al factory - sin lógica duplicada"""
            domain = name.split(".")[0]
            creds = await get_credentials_for_user(user_id, domain)
            return await execute_tool(name, params, creds)
        return tool_fn

    tools_server.tool(name=tool_name)(make_tool_fn(tool_name))

# Exportar instancia para uso externo
tools_server
