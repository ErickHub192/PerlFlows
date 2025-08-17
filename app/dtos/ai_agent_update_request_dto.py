# app/dtos/ai_agent_update_request_dto.py

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from uuid import UUID
from decimal import Decimal

class AIAgentUpdateRequestDTO(BaseModel):
    """
    DTO para actualizar parcialmente un agente AI.
    Todos los campos son opcionales; solo se aplican los que vienen en la petición.
    """
    name: Optional[str] = Field(None, description="Nuevo nombre descriptivo del agente")
    default_prompt: Optional[str] = Field(None, description="Nuevo prompt base del sistema")
    temperature: Optional[float] = Field(None, description="Nueva aleatoriedad del LLM")
    tools: Optional[List[str]] = Field(None, description="Nueva lista de herramientas habilitadas")
    memory_schema: Optional[Dict[str, Any]] = Field(
        None, description="Nueva configuración de memoria"
    )
    model: Optional[str] = Field(None, description="Nuevo modelo LLM a utilizar")
    max_iterations: Optional[int] = Field(None, description="Nuevo máximo de iteraciones")
    
    # Enhanced LLM references
    llm_provider_id: Optional[UUID] = Field(None, description="ID del proveedor LLM")
    llm_model_id: Optional[UUID] = Field(None, description="ID del modelo LLM")
    
    # Usage tracking fields
    total_input_tokens: Optional[int] = Field(None, description="Total de tokens de input utilizados")
    total_output_tokens: Optional[int] = Field(None, description="Total de tokens de output generados")
    total_cost: Optional[float] = Field(None, description="Costo total acumulado")
