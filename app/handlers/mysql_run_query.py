"""
MySQL Query Execution Handler
Ejecuta queries SQL en bases de datos MySQL usando autenticación de credenciales.
"""

import asyncio
import traceback
from typing import Dict, Any
import logging
import mysql.connector
from mysql.connector import Error

from app.handlers.base_handler import BaseHandler
from app.schemas.db_schema_registry import register_db_schema

logger = logging.getLogger(__name__)

class MySQLRunQueryHandler(BaseHandler):
    """Handler para ejecutar queries SQL en MySQL"""
    
    def __init__(self, user_id: int, creds: Dict[str, Any]):
        super().__init__(user_id=user_id, creds=creds)
        logger.info(f"🔧 MySQL Handler initialized for user {user_id}")
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta un query SQL en MySQL.
        
        Separación de responsabilidades:
        1) Handler solo recibe 'query' como parámetro del LLM
        2) Credenciales (host, port, database, username, password) vienen del authenticator
        3) Se construye conexión internamente
        """
        try:
            # 1) Validar parámetro del LLM (solo query)
            query = params.get("query")
            if not query or not isinstance(query, str):
                return {
                    "success": False,
                    "error": "Se requiere parámetro 'query' válido",
                    "data": None
                }
            
            # 2) Obtener credenciales del authenticator
            host = self.creds.get("host")
            port = self.creds.get("port", 3306)
            database = self.creds.get("database") 
            username = self.creds.get("username")
            password = self.creds.get("password")
            
            # 3) Validar credenciales requeridas
            missing_creds = []
            if not host: missing_creds.append("host")
            if not database: missing_creds.append("database")
            if not username: missing_creds.append("username")
            if not password: missing_creds.append("password")
            
            if missing_creds:
                return {
                    "success": False,
                    "error": f"Credenciales faltantes: {', '.join(missing_creds)}",
                    "data": None
                }
            
            logger.info(f"🔧 MySQL connecting to {host}:{port}/{database} as {username}")
            
            # 4) Ejecutar query en un hilo separado para evitar bloqueo
            result = await asyncio.get_event_loop().run_in_executor(
                None, 
                self._execute_sync_query,
                host, port, database, username, password, query
            )
            
            return result
            
        except Exception as e:
            logger.error(f"🚨 MySQL Handler error: {str(e)}")
            logger.error(f"🚨 MySQL Handler traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Error ejecutando query MySQL: {str(e)}",
                "data": None
            }
    
    def _execute_sync_query(self, host: str, port: int, database: str, 
                           username: str, password: str, query: str) -> Dict[str, Any]:
        """Ejecuta query MySQL de forma síncrona"""
        connection = None
        try:
            # Crear conexión MySQL
            connection = mysql.connector.connect(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password,
                autocommit=True
            )
            
            if not connection.is_connected():
                raise Error("No se pudo conectar a MySQL")
                
            cursor = connection.cursor(dictionary=True)
            
            # Ejecutar query
            cursor.execute(query)
            
            # Determinar si es SELECT o modificación
            if query.strip().upper().startswith(('SELECT', 'SHOW', 'DESCRIBE', 'EXPLAIN')):
                # Query de lectura - obtener resultados
                results = cursor.fetchall()
                rows_affected = len(results)
                
                return {
                    "success": True,
                    "data": results,
                    "rows_affected": rows_affected,
                    "query": query,
                    "message": f"Query ejecutado exitosamente. {rows_affected} filas retornadas."
                }
            else:
                # Query de modificación (INSERT, UPDATE, DELETE, etc.)
                rows_affected = cursor.rowcount
                
                return {
                    "success": True,
                    "data": None,
                    "rows_affected": rows_affected,
                    "query": query,
                    "message": f"Query ejecutado exitosamente. {rows_affected} filas afectadas."
                }
                
        except Error as mysql_error:
            error_msg = f"Error MySQL: {mysql_error}"
            logger.error(f"🚨 {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "data": None
            }
        except Exception as e:
            error_msg = f"Error inesperado: {str(e)}"
            logger.error(f"🚨 {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "data": None
            }
        finally:
            if connection and connection.is_connected():
                connection.close()
                logger.info("🔧 MySQL connection closed")
    
    def get_required_permissions(self) -> list:
        """Permisos requeridos para este handler"""
        return ["database.mysql.execute"]
    
    def get_handler_info(self) -> Dict[str, Any]:
        """Información del handler para el LLM"""
        return {
            "name": "MySQL Query Execution",
            "description": "Ejecuta queries SQL en bases de datos MySQL",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "Query SQL a ejecutar (SELECT, INSERT, UPDATE, DELETE, etc.)",
                    "required": True
                }
            },
            "authentication": "db_credentials",
            "provider": "mysql"
        }


@register_db_schema("mysql")
def _mysql_schema() -> Dict[str, Any]:
    """Schema para credenciales MySQL"""
    return {
        "type": "object",
        "properties": {
            "host": {
                "type": "string",
                "title": "Host",
                "description": "Servidor MySQL (ej: localhost)",
                "default": "localhost"
            },
            "port": {
                "type": "integer",
                "title": "Puerto",
                "description": "Puerto de MySQL",
                "default": 3306
            },
            "database": {
                "type": "string",
                "title": "Base de datos",
                "description": "Nombre de la base de datos MySQL"
            },
            "username": {
                "type": "string",
                "title": "Usuario",
                "description": "Usuario de MySQL"
            },
            "password": {
                "type": "string",
                "title": "Contraseña",
                "description": "Contraseña de MySQL",
                "format": "password"
            }
        },
        "required": ["host", "database", "username", "password"],
        "additionalProperties": False
    }