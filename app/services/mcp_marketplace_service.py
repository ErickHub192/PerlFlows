"""
MCP Marketplace Service
Integración con el ecosistema MCP para autodiscovery de servidores
"""
import logging
import httpx
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class MCPServerType(Enum):
    """Tipos de servidores MCP"""
    FILE_STORAGE = "file_storage"
    DATABASE = "database"
    API_INTEGRATION = "api_integration"
    AUTOMATION = "automation"
    AI_ML = "ai_ml"
    DEVELOPMENT = "development"
    COMMUNICATION = "communication"

@dataclass
class MCPServer:
    """Definición de servidor MCP"""
    name: str
    description: str
    server_type: MCPServerType
    provider: str
    install_command: str
    github_url: str
    documentation_url: str
    requires_auth: bool
    auth_type: str
    popularity_score: float
    setup_difficulty: str  # "easy", "medium", "hard"

class MCPMarketplaceService:
    """Servicio para descubrir y gestionar servidores MCP"""
    
    # Registry de servidores MCP conocidos (actualizado con el ecosistema 2024)
    KNOWN_MCP_SERVERS = [
        MCPServer(
            name="GitHub MCP",
            description="Intelligent issue triaging, automated dependency updates, and security scanning",
            server_type=MCPServerType.DEVELOPMENT,
            provider="github",
            install_command="npx @modelcontextprotocol/server-github",
            github_url="https://github.com/modelcontextprotocol/servers/tree/main/src/github",
            documentation_url="https://modelcontextprotocol.io/servers/github",
            requires_auth=True,
            auth_type="oauth2",
            popularity_score=0.95,
            setup_difficulty="easy"
        ),
        MCPServer(
            name="Google Drive MCP",
            description="Access and manipulate files in Google Drive",
            server_type=MCPServerType.FILE_STORAGE,
            provider="google",
            install_command="npx @modelcontextprotocol/server-gdrive",
            github_url="https://github.com/modelcontextprotocol/servers/tree/main/src/gdrive",
            documentation_url="https://modelcontextprotocol.io/servers/gdrive",
            requires_auth=True,
            auth_type="oauth2",
            popularity_score=0.92,
            setup_difficulty="easy"
        ),
        MCPServer(
            name="Slack MCP",
            description="Send messages and interact with Slack workspaces",
            server_type=MCPServerType.COMMUNICATION,
            provider="slack",
            install_command="npx @modelcontextprotocol/server-slack",
            github_url="https://github.com/modelcontextprotocol/servers/tree/main/src/slack",
            documentation_url="https://modelcontextprotocol.io/servers/slack",
            requires_auth=True,
            auth_type="oauth2",
            popularity_score=0.88,
            setup_difficulty="easy"
        ),
        MCPServer(
            name="Postgres MCP",
            description="Execute SQL queries and manage PostgreSQL databases",
            server_type=MCPServerType.DATABASE,
            provider="postgresql",
            install_command="npx @modelcontextprotocol/server-postgres",
            github_url="https://github.com/modelcontextprotocol/servers/tree/main/src/postgres",
            documentation_url="https://modelcontextprotocol.io/servers/postgres",
            requires_auth=True,
            auth_type="database_creds",
            popularity_score=0.85,
            setup_difficulty="medium"
        ),
        MCPServer(
            name="Docker MCP",
            description="Execute isolated code in Docker containers with multi-language support",
            server_type=MCPServerType.DEVELOPMENT,
            provider="docker",
            install_command="npx @modelcontextprotocol/server-docker",
            github_url="https://github.com/modelcontextprotocol/servers/tree/main/src/docker",
            documentation_url="https://modelcontextprotocol.io/servers/docker",
            requires_auth=False,
            auth_type="none",
            popularity_score=0.82,
            setup_difficulty="medium"
        ),
        MCPServer(
            name="Brave Search MCP",
            description="Web and local search with pagination, filtering, and safety controls",
            server_type=MCPServerType.API_INTEGRATION,
            provider="brave",
            install_command="npx @modelcontextprotocol/server-brave-search",
            github_url="https://github.com/modelcontextprotocol/servers/tree/main/src/brave-search",
            documentation_url="https://modelcontextprotocol.io/servers/brave-search",
            requires_auth=True,
            auth_type="api_key",
            popularity_score=0.78,
            setup_difficulty="easy"
        ),
        MCPServer(
            name="Puppeteer MCP",
            description="Web automation and scraping with headless browser control",
            server_type=MCPServerType.AUTOMATION,
            provider="puppeteer",
            install_command="npx @modelcontextprotocol/server-puppeteer",
            github_url="https://github.com/modelcontextprotocol/servers/tree/main/src/puppeteer",
            documentation_url="https://modelcontextprotocol.io/servers/puppeteer",
            requires_auth=False,
            auth_type="none",
            popularity_score=0.75,
            setup_difficulty="hard"
        ),
        MCPServer(
            name="Perplexity Ask MCP",
            description="Real-time web search through Perplexity API for research and Q&A",
            server_type=MCPServerType.AI_ML,
            provider="perplexity",
            install_command="npx @perplexity/mcp-server",
            github_url="https://github.com/perplexity-ai/mcp-server",
            documentation_url="https://docs.perplexity.ai/mcp",
            requires_auth=True,
            auth_type="api_key",
            popularity_score=0.72,
            setup_difficulty="easy"
        ),
        MCPServer(
            name="Notion MCP",
            description="Access and manipulate Notion databases and pages",
            server_type=MCPServerType.DATABASE,
            provider="notion",
            install_command="npx @notionhq/mcp-server",
            github_url="https://github.com/notionhq/mcp-server",
            documentation_url="https://developers.notion.com/docs/mcp",
            requires_auth=True,
            auth_type="api_key",
            popularity_score=0.70,
            setup_difficulty="medium"
        )
    ]
    
    def __init__(self):
        self.marketplace_urls = [
            "https://mcp.so/api/servers",
            "https://mcpmarket.com/api/discover"
        ]
    
    async def discover_mcp_servers_for_intent(self, user_intent: str) -> List[MCPServer]:
        """
        Descubre servidores MCP relevantes para la intención del usuario
        """
        intent_lower = user_intent.lower()
        relevant_servers = []
        
        # Mapeo de intenciones a tipos de servidores
        intent_mappings = {
            "inventory": [MCPServerType.FILE_STORAGE, MCPServerType.DATABASE],
            "github": [MCPServerType.DEVELOPMENT],
            "automation": [MCPServerType.AUTOMATION, MCPServerType.API_INTEGRATION],
            "database": [MCPServerType.DATABASE],
            "files": [MCPServerType.FILE_STORAGE],
            "search": [MCPServerType.API_INTEGRATION],
            "email": [MCPServerType.COMMUNICATION],
            "slack": [MCPServerType.COMMUNICATION],
            "docker": [MCPServerType.DEVELOPMENT],
            "ai": [MCPServerType.AI_ML]
        }
        
        # Encontrar tipos relevantes
        relevant_types = []
        for keyword, types in intent_mappings.items():
            if keyword in intent_lower:
                relevant_types.extend(types)
        
        # Si no se encontraron tipos específicos, usar los más populares
        if not relevant_types:
            relevant_types = [MCPServerType.FILE_STORAGE, MCPServerType.AUTOMATION]
        
        # Filtrar servidores por tipo
        for server in self.KNOWN_MCP_SERVERS:
            if server.server_type in relevant_types:
                relevant_servers.append(server)
        
        # Intentar descubrir servidores adicionales del marketplace
        marketplace_servers = await self._fetch_from_marketplace(user_intent)
        relevant_servers.extend(marketplace_servers)
        
        # Ordenar por popularidad
        relevant_servers.sort(key=lambda x: x.popularity_score, reverse=True)
        
        return relevant_servers[:5]  # Top 5
    
    async def _fetch_from_marketplace(self, intent: str) -> List[MCPServer]:
        """Busca servidores en los marketplaces online"""
        discovered_servers = []
        
        async with httpx.AsyncClient() as client:
            for marketplace_url in self.marketplace_urls:
                try:
                    response = await client.get(
                        marketplace_url,
                        params={"q": intent, "limit": 10},
                        timeout=5.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        servers = self._parse_marketplace_response(data)
                        discovered_servers.extend(servers)
                        
                except Exception as e:
                    logger.warning(f"Error fetching from marketplace {marketplace_url}: {e}")
        
        return discovered_servers[:3]  # Limitar resultados del marketplace
    
    def _parse_marketplace_response(self, data: Dict[str, Any]) -> List[MCPServer]:
        """Parsea respuesta del marketplace a objetos MCPServer"""
        servers = []
        
        # Esta implementación dependería del formato específico del marketplace
        # Por ahora retornamos lista vacía
        # En implementación real, parsearíamos la respuesta JSON
        
        return servers
    
    async def get_mcp_servers_by_provider(self, provider: str) -> List[MCPServer]:
        """Obtiene servidores MCP para un proveedor específico"""
        return [server for server in self.KNOWN_MCP_SERVERS if server.provider == provider]
    
    async def get_installation_instructions(self, server: MCPServer) -> Dict[str, Any]:
        """Genera instrucciones de instalación para un servidor MCP"""
        
        instructions = {
            "server_name": server.name,
            "install_command": server.install_command,
            "setup_steps": []
        }
        
        # Pasos de instalación básicos
        instructions["setup_steps"].extend([
            {
                "step": 1,
                "title": "Instalar servidor MCP",
                "command": server.install_command,
                "description": f"Instala el servidor MCP para {server.provider}"
            }
        ])
        
        # Pasos específicos según autenticación
        if server.requires_auth:
            if server.auth_type == "oauth2":
                instructions["setup_steps"].append({
                    "step": 2,
                    "title": "Configurar OAuth",
                    "description": f"Configura credenciales OAuth para {server.provider}",
                    "oauth_url": f"/api/oauth/{server.provider}/authorize"
                })
            elif server.auth_type == "api_key":
                instructions["setup_steps"].append({
                    "step": 2,
                    "title": "Configurar API Key",
                    "description": f"Obtén y configura API key de {server.provider}",
                    "config_example": f"export {server.provider.upper()}_API_KEY=your_key_here"
                })
        
        # Paso final de configuración
        instructions["setup_steps"].append({
            "step": len(instructions["setup_steps"]) + 1,
            "title": "Agregar a configuración MCP",
            "description": "Agregar servidor a tu configuración MCP",
            "config_file": "~/.config/mcp/servers.json"
        })
        
        return instructions
    
    async def check_server_compatibility(self, server: MCPServer, user_services: List[str]) -> Dict[str, Any]:
        """Verifica compatibilidad del servidor con servicios del usuario"""
        
        compatibility = {
            "compatible": False,
            "score": 0.0,
            "reasons": [],
            "requirements_met": []
        }
        
        # Verificar si el usuario ya tiene el servicio conectado
        if server.provider in user_services:
            compatibility["compatible"] = True
            compatibility["score"] += 0.8
            compatibility["reasons"].append(f"Ya tienes {server.provider} conectado")
            compatibility["requirements_met"].append("service_connected")
        
        # Verificar dificultad de setup
        difficulty_scores = {"easy": 0.2, "medium": 0.1, "hard": 0.0}
        compatibility["score"] += difficulty_scores.get(server.setup_difficulty, 0.0)
        
        # Verificar popularidad
        if server.popularity_score > 0.8:
            compatibility["score"] += 0.1
            compatibility["reasons"].append("Servidor muy popular y confiable")
        
        # Determinar compatibilidad final
        compatibility["compatible"] = compatibility["score"] > 0.5
        
        return compatibility

# Función auxiliar para uso directo
async def discover_mcp_servers(user_intent: str) -> List[MCPServer]:
    """
    Función auxiliar para descubrir servidores MCP
    
    Example:
        servers = await discover_mcp_servers("Quiero automatizar mi inventario")
        for server in servers:
            print(f"📦 {server.name}: {server.description}")
    """
    service = MCPMarketplaceService()
    return await service.discover_mcp_servers_for_intent(user_intent)