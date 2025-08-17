# app/schema/db_schema_registry.py

from typing import Callable, Dict, Any

# Mantenemos un mapping: flavor -> función que retorna schema
_SCHEMA_REGISTRY: Dict[str, Callable[[], Dict[str, Any]]] = {}


def register_db_schema(flavor: str):
    """
    Decorador para que cada handler de BD registre su propio JSON‐Schema bajo el 'flavor' indicado.
    Ejemplo de uso en un handler de Postgres:
        @register_db_schema("postgres")
        def _postgres_schema() -> Dict[str,Any]:
            return { … JSON schema de Postgres … }
    """
    def _wrapper(func: Callable[[], Dict[str, Any]]):
        _SCHEMA_REGISTRY[flavor] = func
        return func
    return _wrapper


def get_db_schema(flavor: str) -> Dict[str, Any]:
    """
    Devuelve el JSON‐Schema registrado para el 'flavor' dado.
    Si no existe un esquema para ese flavor, podemos:
      1) Lanzar excepción HTTP 400
      2) O devolver un schema genérico / vacío
    """
    schema_func = _SCHEMA_REGISTRY.get(flavor)
    if not schema_func:
        raise KeyError(f"No hay JSON‐Schema registrado para flavor='{flavor}'")
    return schema_func()
