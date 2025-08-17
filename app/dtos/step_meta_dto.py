from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

class StepMetaDTO(BaseModel):
    """Metadata de un paso de acción dentro de un flujo."""
    id: UUID = Field(
        default_factory=uuid4,
        description="Identificador único del paso dentro del flujo",
    )
    next: Optional[UUID] = Field(
        None,
        description="ID del siguiente paso si la ejecución continúa de forma lineal",
    )
    node_id: UUID = Field(..., description="ID único del nodo en el flujo")
    action_id: UUID = Field(..., description="ID único de la acción asociada al nodo")
    node_name: str = Field(..., description="Nombre del nodo (p.ej. 'Google_Calendar')")
    action_name: str = Field(..., description="Nombre de la acción (p.ej. 'create_event')")
    default_auth: Optional[Any] = Field(
        None,
        description="Proveedor de autenticación por defecto (p.ej. 'Google')"
    )
    params: Dict[str, Any] = Field(
        ...,
        description="Valores de parámetros para la ejecución del paso"
    )
    params_meta: List[Dict[str, Any]] = Field(
        ...,
        description="Metadatos de cada parámetro (nombre, tipo, requerido, etc.)"
    )
    uses_mcp: bool = Field(
        False,
        description="Indica si este paso debe invocarse a través de MCP Server"
    )
    retries: int = Field(
        0,
        description="Número de reintentos permitidos en caso de fallo del paso"
    )
    timeout_ms: Optional[int] = Field(
        None,
        description="Tiempo máximo de espera para la ejecución del paso (en milisegundos)"
    )
    simulate: bool = Field(
        False,
        description="Si es True, el paso solo simula la ejecución y devuelve datos stub"
    )
