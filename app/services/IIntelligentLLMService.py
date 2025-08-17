# app/services/IIntelligentLLMService.py

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class IIntelligentLLMService(ABC):
    """
    Interface para el servicio de LLM inteligente.
    
    Servicio mejorado de LLM para modelos SELECCIONADOS POR USUARIOS y agentes.
    
    Separado del LLMService interno de Kyra:
    - Operaciones internas de Kyra: Usar LLMService con settings.DEFAULT_LLM_MODEL
    - Agentes de usuario/Bill/custom: Usar IntelligentLLMService con modelos seleccionados
    
    Características: selección inteligente de modelos, tracking de costos, analytics de uso
    """

    @abstractmethod
    async def run_with_model_selection(
        self,
        system_prompt: str,
        short_term: List[Dict[str, Any]],
        long_term: List[Dict[str, Any]],
        user_prompt: str,
        user_id: int,
        model_key: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        auto_select_model: bool = True
    ) -> Dict[str, Any]:
        """
        Ejecuta prompt con selección inteligente de modelo.
        
        Args:
            system_prompt: Prompt del sistema
            short_term: Memoria de corto plazo
            long_term: Memoria de largo plazo
            user_prompt: Prompt del usuario
            user_id: ID del usuario
            model_key: Clave del modelo específico (opcional)
            temperature: Temperatura para generación (opcional)
            max_tokens: Máximo de tokens (opcional)
            auto_select_model: Si True, selecciona automáticamente el mejor modelo
            
        Returns:
            Dict con respuesta del LLM y metadata (costo, modelo usado, etc.)
            
        Raises:
            WorkflowProcessingException: Si hay errores durante la ejecución
        """
        pass