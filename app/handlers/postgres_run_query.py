# app/connectors/handlers/postgres_run_query.py

import time
from typing import Any, Dict, List
from uuid import UUID
from app.connectors.factory import register_tool, register_node
import asyncpg
from .connector_handler import ActionHandler

# Importamos el decorador para registrar el schema de Postgres
from app.schemas.db_schema_registry import register_db_schema

@register_db_schema("postgres")
def _postgres_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "host": {
                "type": "string",
                "title": "Host",
                "description": "Servidor PostgreSQL (ej: localhost)",
                "default": "localhost"
            },
            "port": {
                "type": "integer",
                "title": "Puerto",
                "description": "Puerto de PostgreSQL",
                "default": 5432
            },
            "database": {
                "type": "string",
                "title": "Base de datos",
                "description": "Nombre de la base de datos"
            },
            "username": {
                "type": "string",
                "title": "Usuario",
                "description": "Usuario de PostgreSQL"
            },
            "password": {
                "type": "string",
                "title": "Contraseña",
                "description": "Contraseña del usuario",
                "format": "password"
            }
        },
        "required": ["host", "database", "username", "password"]
    }

@register_node("Postgres.run_query")
@register_tool("Postgres.run_query")
class PostgresRunQueryHandler(ActionHandler):
    """
    Handler para la acción 'run_query' de PostgreSQL.
    
    Separación de responsabilidades:
    - params: Solo 'query' (lo que pide el LLM)
    - creds: host, port, database, username, password (del authenticator)
    """

    def __init__(self, creds: Dict[str, Any]):
        # Credenciales vienen del authenticator, no de params
        self.creds = creds

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start_ts = time.perf_counter()

        # 1) Validar parámetro del LLM (solo query)
        query = params.get("query")
        if not query:
            return {
                "status": "error",
                "error": "Falta parámetro requerido: 'query'",
                "output": None,
                "duration_ms": 0
            }

        # 2) Obtener credenciales del authenticator
        host = self.creds.get("host")
        port = self.creds.get("port", 5432)
        database = self.creds.get("database")
        username = self.creds.get("username")
        password = self.creds.get("password")
        
        if not all([host, database, username, password]):
            return {
                "status": "error",
                "error": "Credenciales incompletas: faltan host, database, username o password",
                "output": None,
                "duration_ms": 0
            }

        # 3) Construir DSN internamente
        dsn = f"postgresql://{username}:{password}@{host}:{port}/{database}"

        # 4) Conexión y ejecución
        try:
            conn = await asyncpg.connect(dsn=dsn) 
            records = await conn.fetch(query)  
            await conn.close()         

            # Convertir Record → dict
            output: List[Dict[str, Any]] = [
                dict(record) for record in records
            ]
            status, error = "success", None

        except Exception as e:
            status, output, error = "error", None, str(e)

        # 5) Medir duración
        duration_ms = int((time.perf_counter() - start_ts) * 1000)

        return {
            "status": status,
            "output": output,
            "error": error,
            "duration_ms": duration_ms
        }
