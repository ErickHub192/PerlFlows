# app/authenticators/db_credentials.py

from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.authenticators.registry import register_authenticator
from app.authenticators.base_oauth_authenticator import BaseOAuthAuthenticator
from app.schemas.db_schema_registry import get_db_schema
from fastapi import HTTPException

# DEBUG: Confirmar que el módulo se está importando
print("🚨 DB_CREDENTIALS MODULE LOADING...")

@register_authenticator("db_credentials", "postgres")
@register_authenticator("db_credentials", "mysql")
class DbCredentialsAuthenticator(BaseOAuthAuthenticator):
    """
    Autenticador “db_credentials_<flavor>” (postgres, mysql, mongo, redis, …).
    Solo se preocupa por devolver el JSON‐Schema registrado y (opcionalmente) guardar/validar credenciales.
    """

    def __init__(self, user_id: int, db: AsyncSession, auth_policy: Dict[str, Any]):
        # DEBUG: Log para ver si se instancia correctamente
        print(f"🔧 DB_CREDENTIALS INIT: user_id={user_id}, auth_policy={auth_policy}")
        
        # Llamar al constructor de la clase base
        super().__init__(user_id=user_id, db=db, service_id=auth_policy.get("service_id"))
        self.auth_policy = auth_policy
        # Obtener el tipo de base de datos desde auth_policy
        self.db_type = auth_policy.get("service", "postgres")
        self.provider = auth_policy.get("provider", "postgres")
        
        print(f"🔧 DB_CREDENTIALS READY: provider={self.provider}, service_id={self.service_id}")

    async def get_json_schema(self, node_id: str) -> Dict[str, Any]:
        """
        Retorna el JSON Schema registrado bajo el tipo de base de datos actual.
        Si el tipo no existe, devolvemos error 400.
        """
        try:
            schema = get_db_schema(self.db_type)
        except KeyError:
            raise HTTPException(status_code=400, detail=f"No existe JSON‐Schema para db_type='{self.db_type}'")
        return {"schema": schema}

    async def validate_and_save(self, connection_data: Dict[str, Any]) -> None:
        """
        (Opcional) Validar que 'connection_data' cumple con el schema (puedes usar jsonschema.validate aquí),
        luego guardar las credenciales en la tabla de credenciales si así lo deseas.
        """
        # Validar que los campos requeridos estén presentes
        required_fields = ["host", "database", "username", "password"]
        missing_fields = [field for field in required_fields if not connection_data.get(field)]
        
        if missing_fields:
            raise HTTPException(
                status_code=400, 
                detail=f"Faltan campos requeridos: {', '.join(missing_fields)}"
            )
        
        # Usar el método heredado para guardar credenciales
        await self.upsert_credentials(self.provider, connection_data)

    async def authorization_url(self) -> str:
        """
        Para db_credentials no hay URL de autorización OAuth.
        Retornamos string vacío ya que se maneja por formulario directo.
        """
        return ""

    async def fetch_token(self, credentials_data: dict, state: str = None) -> Dict[str, Any]:
        """
        Para db_credentials, simplemente validamos y retornamos las credenciales.
        No hay intercambio de tokens como en OAuth.
        """
        # Validar campos requeridos
        required_fields = ["host", "database", "username", "password"]
        missing_fields = [field for field in required_fields if not credentials_data.get(field)]
        
        if missing_fields:
            raise HTTPException(
                status_code=400, 
                detail=f"Faltan campos requeridos: {', '.join(missing_fields)}"
            )
        
        # Para db_credentials, las credenciales van en 'config'
        return {
            "service_id": self.service_id,
            "provider": self.provider,
            "config": credentials_data
        }

    async def refresh_credentials(self, creds_obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        Las credenciales de base de datos no requieren refresh.
        Simplemente retornamos las credenciales existentes.
        """
        return creds_obj
