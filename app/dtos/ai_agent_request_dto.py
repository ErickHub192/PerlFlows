from pydantic import BaseModel, Field
from typing import Optional

class AIAgentRequestDTO(BaseModel):
    prompt: str = Field(..., description="Mensaje del usuario para el agente")
    model: Optional[str] = Field(None, description="(Opcional) Modelo de LLM")
    temperature: Optional[float] = Field(None, description="(Opcional) Aleatoriedad")
    max_iterations: Optional[int] = Field(
        None, description="(Opcional) Límite de iteraciones ReAct"
    )
    # early_stopping_method: Optional[str] = Field(
    #     None, description="(Opcional) Método de parada anticipada"
    # )

