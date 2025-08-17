# app/dtos/ai_agent_create_request_dto.py
# sirve para el router de ai_agent_router.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any

class AIAgentCreateRequestDTO(BaseModel):
    """
    DTO para crear un nuevo agente AI.
    No incluye `agent_id`, que se genera en el servidor.
    """
    name: str = Field(..., description="Nombre descriptivo del agente")
    default_prompt: str = Field(..., description="Prompt base del sistema para el agente")
    temperature: float = Field(0.0, description="Aleatoriedad del LLM (0.0–1.0)")
    tools: List[str] = Field(..., description="Lista de herramientas habilitadas (identificadores)")
    memory_schema: Dict[str, Any] = Field(
        ..., description="Esquema/configuración de memoria (short/long term)"
    )
    model: str = Field(..., description="Nombre del modelo LLM a utilizar, e.g. 'gpt-4.1'")
    max_iterations: int = Field(..., description="Máximo número de pasos/reasoning loops")
    
    # Activation Configuration - Triggers seleccionables por Kyra + Usuario
    activation_type: str = Field("manual", description="Tipo de activación: 'manual' o 'triggered'")
    trigger_config: Dict[str, Any] = Field(None, description="Configuración del trigger seleccionado (nodo + parámetros)")
    is_active: bool = Field(True, description="Si el agente está activo para triggers automáticos")
