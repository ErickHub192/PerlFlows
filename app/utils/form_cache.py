# app/utils/form_cache.py
import time
from typing import Optional, Tuple
from app.dtos.form_schema_dto import FormSchemaDTO

# { "<node_id>:<action>": (schema, timestamp) }
_schema_cache: dict[str, Tuple[FormSchemaDTO, float]] = {}
CACHE_TTL = 300  

def get_cached_schema(node_id: str, action: str) -> Optional[FormSchemaDTO]:
    key = f"{node_id}:{action or ''}"
    entry = _schema_cache.get(key)
    if entry:
        schema, ts = entry
        if time.time() - ts < CACHE_TTL:
            return schema
        # expiró
        del _schema_cache[key]
    return None

def set_cached_schema(node_id: str, action: str, schema: FormSchemaDTO) -> None:
    key = f"{node_id}:{action or ''}"
    _schema_cache[key] = (schema, time.time())
