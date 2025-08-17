from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime

class AIAgentDTO(BaseModel):
    agent_id: Optional[UUID] = None
    name: str
    default_prompt: str
    temperature: float 
    tools: List[str]
    memory_schema: Dict[str, Any]
    model: Optional[str] = None  # Keep for backward compatibility
    max_iterations: int
    status: Optional[str] = None
    
    # Enhanced LLM references
    llm_provider_id: Optional[UUID] = None
    llm_model_id: Optional[UUID] = None
    
    # Usage tracking for cost analytics
    total_input_tokens: Optional[int] = 0
    total_output_tokens: Optional[int] = 0
    total_cost: Optional[Decimal] = Decimal('0')
    
    # Activation Configuration - Triggers seleccionables
    activation_type: Optional[str] = "manual"  # "manual", "triggered"
    trigger_config: Optional[Dict[str, Any]] = None  # Configuración del trigger seleccionado
    is_active: Optional[bool] = True  # Si está activo para triggers automáticos
    last_triggered: Optional[datetime] = None  # Última ejecución por trigger
    
    model_config = ConfigDict(from_attributes=True)
