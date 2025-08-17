"""
Registry Pattern agnóstico para generadores de datos fake
Sistema completamente declarativo sin lógica hardcodeada
"""

from typing import Any, Dict, Callable, Optional
import logging

logger = logging.getLogger(__name__)


class FakeDataRegistry:
    """
    Registry completamente agnóstico que no conoce tipos de nodos.
    Solo registra y ejecuta generadores declarados por decorators.
    """
    
    def __init__(self):
        self._node_generators: Dict[str, Callable] = {}
        self._scanned = False
    
    def register_generator(self, node_key: str):
        """
        Decorator para registrar un generador de datos fake para un nodo específico
        
        Args:
            node_key: Clave exacta del nodo (ej: "HTTP_Request.request", "Gmail.send_messages")
        """
        def decorator(generator_func: Callable[[Dict[str, Any]], Dict[str, Any]]):
            self._node_generators[node_key] = generator_func
            logger.debug(f"Registered fake data generator: {node_key}")
            return generator_func
        return decorator
    
    def generate_fake_output(self, node_key: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera output fake para un nodo específico
        
        Args:
            node_key: Clave del nodo (ej: "HTTP_Request.request")
            params: Parámetros del step
            
        Returns:
            Dict con output fake realista o estructura genérica si no hay generador
        """
        self._ensure_scanned()
        
        # Buscar generador específico
        generator = self._node_generators.get(node_key)
        if generator:
            try:
                return generator(params)
            except Exception as e:
                logger.error(f"Error en generador para {node_key}: {e}")
        
        # Si no hay generador específico, devolver estructura genérica
        return self._default_output()
    
    def _default_output(self) -> Dict[str, Any]:
        """Output genérico cuando no hay generador específico"""
        from app.utils.template_engine import template_engine
        return template_engine.generate_fake_output_structure()
    
    def has_generator(self, node_key: str) -> bool:
        """Verifica si existe un generador para el nodo"""
        self._ensure_scanned()
        return node_key in self._node_generators
    
    def _ensure_scanned(self):
        """Escanea e importa todos los generadores modulares"""
        if not self._scanned:
            self._scan_generators()
            self._scanned = True
    
    def _scan_generators(self):
        """Importa dinámicamente todos los generadores"""
        try:
            import app.utils.fake_data.generators
            import pkgutil
            import importlib
            
            generators_path = app.utils.fake_data.generators.__path__
            for _, module_name, _ in pkgutil.iter_modules(generators_path):
                if not module_name.startswith('_'):
                    importlib.import_module(f"app.utils.fake_data.generators.{module_name}")
                    
        except Exception as e:
            logger.error(f"Error escaneando generadores: {e}")
    
    def get_registry_status(self) -> Dict[str, Any]:
        """Debug: Estado del registry"""
        self._ensure_scanned()
        return {
            'total_generators': len(self._node_generators),
            'registered_nodes': list(self._node_generators.keys())
        }


# Instancia global
fake_data_registry = FakeDataRegistry()

# Decorator shortcut
register_fake_generator = fake_data_registry.register_generator