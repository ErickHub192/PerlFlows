from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

class AIAgentResponseDTO(BaseModel):
    steps: List[Dict[str, Any]] = Field(
        ..., description="Pasos ejecutados (tool y params) y sus resultados"
    )
    final_output: str = Field(..., description="Salida final del agente")
    tools_duration_ms: Optional[int] = Field(
        None, description="Tiempo total (ms) invertido en ejecutar las tools"
    )
    iterations: Optional[int] = Field(
        None, description="Número de rondas de ReAct/iteraciones realizadas"
    )
