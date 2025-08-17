"""
Registry modular para handlers de triggers
Permite auto-registro de handlers con sus capacidades de trigger
"""
from typing import Dict, Any, Optional, Callable
import logging

logger = logging.getLogger(__name__)

class TriggerRegistry:
    """
    Registry centralizado para handlers de triggers
    """
    
    def __init__(self):
        self._handlers: Dict[str, Dict[str, Any]] = {}
    
    def register_trigger_handler(
        self, 
        trigger_type: str, 
        node_name: str, 
        handler_class: type,
        schedule_method: str = "execute",
        unschedule_method: str = "unschedule"
    ):
        """
        Registra un handler como capaz de manejar triggers
        
        Args:
            trigger_type: Tipo de trigger ("cron", "webhook", etc.)
            node_name: Nombre del nodo en BD
            handler_class: Clase del handler
            schedule_method: Método para scheduling
            unschedule_method: Método para unscheduling
        """
        self._handlers[trigger_type] = {
            "node_name": node_name,
            "handler_class": handler_class,
            "schedule_method": schedule_method,
            "unschedule_method": unschedule_method
        }
        logger.info(f"Registered trigger handler: {trigger_type} -> {node_name}")
    
    def get_trigger_handler(self, trigger_type: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene handler info para un tipo de trigger
        """
        return self._handlers.get(trigger_type)
    
    def get_all_trigger_types(self) -> list[str]:
        """
        Lista todos los tipos de trigger registrados
        """
        return list(self._handlers.keys())
    
    async def schedule_trigger(
        self, 
        trigger_type: str, 
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Ejecuta scheduling usando el handler registrado
        """
        handler_info = self.get_trigger_handler(trigger_type)
        if not handler_info:
            return {
                "status": "error",
                "error": f"No handler registered for trigger type: {trigger_type}"
            }
        
        try:
            handler_class = handler_info["handler_class"]
            schedule_method = handler_info["schedule_method"]
            
            handler_instance = handler_class()
            method = getattr(handler_instance, schedule_method)
            
            result = await method(params)
            return result
            
        except Exception as e:
            logger.error(f"Error scheduling {trigger_type}: {e}")
            return {
                "status": "error", 
                "error": f"Error scheduling trigger: {str(e)}"
            }
    
    async def unschedule_trigger(
        self, 
        trigger_type: str, 
        job_id: str,
        scheduler: Any = None
    ) -> Dict[str, Any]:
        """
        Ejecuta unscheduling usando el handler registrado
        """
        handler_info = self.get_trigger_handler(trigger_type)
        if not handler_info:
            return {
                "status": "error",
                "error": f"No handler registered for trigger type: {trigger_type}"
            }
        
        try:
            handler_class = handler_info["handler_class"]
            unschedule_method = handler_info["unschedule_method"]
            
            handler_instance = handler_class()
            method = getattr(handler_instance, unschedule_method)
            
            # Llamar método con los argumentos apropiados
            if unschedule_method == "unschedule" and scheduler:
                result = await method(scheduler, job_id)
            else:
                result = await method(job_id)
                
            return result
            
        except Exception as e:
            logger.error(f"Error unscheduling {trigger_type}: {e}")
            return {
                "status": "error",
                "error": f"Error unscheduling trigger: {str(e)}"
            }


# Singleton global
_trigger_registry = TriggerRegistry()


def register_trigger_capability(
    trigger_type: str,
    node_name: str, 
    schedule_method: str = "execute",
    unschedule_method: str = "unschedule"
):
    """
    Decorator para auto-registrar handlers con capacidades de trigger
    
    Usage:
        @register_trigger_capability("cron", "Cron_Trigger.schedule")
        class CronScheduleHandler(ActionHandler):
            ...
    """
    def decorator(handler_class):
        _trigger_registry.register_trigger_handler(
            trigger_type=trigger_type,
            node_name=node_name,
            handler_class=handler_class,
            schedule_method=schedule_method,
            unschedule_method=unschedule_method
        )
        return handler_class
    return decorator


def get_trigger_registry() -> TriggerRegistry:
    """
    Obtiene el registry global de triggers
    """
    return _trigger_registry