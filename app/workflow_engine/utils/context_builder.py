"""
Context Builder - Construcción centralizada de contextos básicos
Elimina la duplicación de lógica de construcción de contextos en el workflow engine
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session


class ContextBuilder:
    """
    Maneja la construcción consistente de contextos básicos para eliminar duplicación
    """
    
    @staticmethod
    def build_request_context(
        user_id: int,
        db_session: Session,
        context: Optional[Dict[str, Any]] = None,
        cag_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Construye el contexto base que se repite en múltiples métodos
        
        Esta es la lógica duplicada actual:
        request_context = {
            "user_id": user_id,
            "db_session": db_session,
            "cag_context": cag_context,  # Solo cuando viene de Kyra
            **(context or {})
        }
        """
        request_context = {
            "user_id": user_id,
            "db_session": db_session,
        }
        
        if cag_context:
            request_context["cag_context"] = cag_context
            
        if context:
            request_context.update(context)
            
        return request_context