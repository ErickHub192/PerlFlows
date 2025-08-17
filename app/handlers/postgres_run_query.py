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
            "dsn": {
                "type": "string",
                "title": "DSN",
                "description": "Cadena de conexión libpq (por ejemplo: 'postgres://user:pass@host:port/db')"
            },
            "query": {
                "type": "string",
                "title": "Consulta SQL",
                "description": "Sentencia SQL que se ejecutará"
            }
        },
        "required": ["dsn", "query"]
    }

@register_node("Postgres.run_query")
@register_tool("Postgres.run_query")
class PostgresRunQueryHandler(ActionHandler):
    """
    Handler para la acción 'run_query' de PostgreSQL.
    Parámetros en params:
      - dsn   (str, requerido): URI de conexión libpq.
      - query (str, requerido): Sentencia SQL a ejecutar.
    """

    def __init__(self, creds: Dict[str, Any]):
        # En este caso no usamos 'creds'; el DSN viene en params.
        pass

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start_ts = time.perf_counter()

        # 1) Validación de parámetros
        dsn   = params.get("dsn")
        query = params.get("query")
        if not dsn or not query:
            return {
                "status":      "error",
                "error":       "Faltan parámetros: 'dsn' y 'query' son requeridos",
                "output":      None,
                "duration_ms": 0
            }

        # 2) Conexión y ejecución
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

        # 3) Medir duración
        duration_ms = int((time.perf_counter() - start_ts) * 1000)

        return {
            "status":      status,
            "output":      output,
            "error":       error,
            "duration_ms": duration_ms
        }
