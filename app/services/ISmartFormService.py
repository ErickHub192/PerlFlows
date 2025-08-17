"""
Interfaz para el servicio de formularios inteligentes
Combina parámetros de BD con discovery automático
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from uuid import UUID
from app.dtos.form_schema_dto import FormSchemaDTO


class ISmartFormService(ABC):
    
    @abstractmethod
    async def analyze_handler_parameters(self, handler_name: str, discovered_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analiza qué parámetros faltan para un handler específico
        """
        ...
    
    @abstractmethod
    async def get_missing_parameters_form(self, handler_name: str, discovered_params: Dict[str, Any]) -> Optional[FormSchemaDTO]:
        """
        Genera formulario dinámico solo para parámetros faltantes
        """
        ...
    
    @abstractmethod
    async def get_traditional_form_by_action(self, action_id: UUID) -> FormSchemaDTO:
        """
        Genera formulario tradicional basado en parámetros de BD (flujo original)
        """
        ...
    
    @abstractmethod
    async def merge_and_execute_handler(
        self, 
        handler_name: str, 
        discovered_params: Dict[str, Any],
        user_provided_params: Dict[str, Any],
        execution_creds: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Combina parámetros descubiertos + input del usuario y ejecuta el handler
        """
        ...
    
    @abstractmethod
    async def should_use_smart_form(self, handler_name: str) -> bool:
        """
        Determina si usar el sistema inteligente o el tradicional para un handler
        """
        ...