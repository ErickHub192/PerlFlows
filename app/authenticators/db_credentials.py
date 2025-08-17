# app/authenticators/db_credentials.py

from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.authenticators.registry import register_authenticator
from app.schemas.db_schema_registry import get_db_schema
from fastapi import HTTPException

@register_authenticator("db_credentials", "")
class DbCredentialsAuthenticator:
    """
    Autenticador “db_credentials_<flavor>” (postgres, mysql, mongo, redis, …).
    Solo se preocupa por devolver el JSON‐Schema registrado y (opcionalmente) guardar/validar credenciales.
    """

    def __init__(self, user_id: int, db: AsyncSession, auth_policy: Dict[str, Any]):
        self.user_id = user_id
        self.db = db
        self.auth_policy = auth_policy
        # Obtener el tipo de base de datos desde auth_policy
        self.db_type = auth_policy.get("service", "postgres")
        self.service_id = auth_policy.get("service_id")

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
        # Ejemplo de validación (si usas 'jsonschema'):
        # from jsonschema import validate, ValidationError
        # schema = get_db_schema(self.db_type)
        # try:
        #     validate(instance=connection_data, schema=schema)
        # except ValidationError as e:
        #     raise HTTPException(status_code=400, detail=f"Parámetros inválidos: {e.message}")
        #
        # Luego guardar en BD con encrypt y repositorio...
        pass
