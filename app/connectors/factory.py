# app/connectors/factory.py

from typing import Any, Dict, Type
from app.handlers.connector_handler import ActionHandler
import app.handlers
import pkgutil, importlib
import logging
from app.exceptions.parameter_validation import parameter_validator
from app.exceptions.smart_parameter_handler import smart_parameter_handler
from app.exceptions.requires_user_input_error import RequiresUserInputError
from app.exceptions.logging_utils import get_kyra_logger

logger = get_kyra_logger(__name__)

# Registro dinámico para “tools” (invocado desde el agente)
_TOOL_REGISTRY: Dict[str, Type[ActionHandler]] = {}

# Registro dinámico para "nodes" (workflows)
_NODE_REGISTRY: Dict[str, Type[ActionHandler]] = {}

def register_tool(name: str, usage_mode: str | None = None):
    """Register a tool handler under ``name``.

    Optionally assigns ``usage_mode`` as an attribute of the class so other
    services can read how the tool should be used.

    Example::

        @register_tool("Gmail.send_messages", usage_mode="tool")
    """

    def decorator(cls: Type[ActionHandler]):
        _TOOL_REGISTRY[name] = cls
        if usage_mode is not None:
            setattr(cls, "usage_mode", usage_mode)
        
        # Auto-registrar especificaciones de parámetros
        try:
            parameter_validator.register_handler_specs(name, cls)
            logger.debug(f"Registered tool handler and params: {name} -> {cls.__name__}")
        except Exception as e:
            logger.warning(f"Error registrando parámetros para {name}", error=e)
            logger.debug(f"Registered tool handler: {name} -> {cls.__name__}")
        
        return cls

    return decorator


def _get_handler_from_registry(
    registry: Dict[str, Type[ActionHandler]],
    key: str,
    creds: Dict[str, Any],
    handler_type: str
) -> ActionHandler:
    """
    Función unificada para obtener handlers de cualquier registry.
    Elimina duplicación de código entre get_tool_handler y get_node_handler.
    """
    HandlerCls = registry.get(key)
    if not HandlerCls:
        available_keys = list(registry.keys())
        logger.error(f"No {handler_type} handler found for '{key}'. Available: {available_keys}")
        raise ValueError(f"No existe {handler_type} handler para '{key}'. Disponibles: {available_keys}")
    
    try:
        # 🔧 FIX: Handlers don't take creds in constructor, they receive them in execute()
        return HandlerCls()
    except Exception as e:
        logger.error(f"Error instantiating {handler_type} handler {HandlerCls.__name__}: {e}")
        raise RuntimeError(f"Error creando instancia de {handler_type} handler '{key}': {e}")


def get_tool_handler(
    tool_name: str,
    creds: Dict[str, Any]
) -> ActionHandler:
    """
    Devuelve la instancia del handler registrado como tool `tool_name`.
    """
    return _get_handler_from_registry(_TOOL_REGISTRY, tool_name, creds, "tool")

async def execute_tool(
    tool_name: str,
    params: Dict[str, Any],
    creds: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Ejecuta un tool usando su handler registrado con análisis inteligente de parámetros.
    """
    logger.debug(f"Ejecutando tool: {tool_name}", provided_params=list(params.keys()))
    
    # Análisis inteligente de parámetros
    if smart_parameter_handler.should_request_user_input(tool_name, params):
        missing_info = smart_parameter_handler.get_missing_parameters_info(tool_name, params)
        logger.info(f"Tool {tool_name} requiere input del usuario",
                   missing_count=missing_info["missing_count"])
        raise RequiresUserInputError(tool_name, missing_info)
    
    # Si no necesita input del usuario, ejecutar normalmente
    handler = get_tool_handler(tool_name, creds)
    return await handler.execute(params, creds)


def register_node(name: str):
    """
    Decorador para registrar un handler de nodo workflow.
    name debe coincidir con la clave en tu BD: e.g. "Gmail.send_messages"
    """
    def decorator(cls: Type[ActionHandler]):
        _NODE_REGISTRY[name] = cls
        
        # Auto-registrar especificaciones de parámetros para nodos también
        try:
            parameter_validator.register_handler_specs(name, cls)
            logger.debug(f"Registered node handler and params: {name} -> {cls.__name__}")
        except Exception as e:
            logger.warning(f"Error registrando parámetros para nodo {name}", error=e)
            logger.debug(f"Registered node handler: {name} -> {cls.__name__}")
        
        return cls
    return decorator

def get_node_handler(node_name: str, action_name: str, creds: Dict[str, Any]) -> ActionHandler:
    """
    Devuelve la instancia del handler registrado como node.
    Intenta múltiples estrategias de resolución de keys para máxima compatibilidad.
    """
    # Estrategia 1: Buscar con key construido (backward compatibility)
    constructed_key = f"{node_name}.{action_name}"
    if constructed_key in _NODE_REGISTRY:
        return _get_handler_from_registry(_NODE_REGISTRY, constructed_key, creds, "node")
    
    # Estrategia 2: Buscar node_name directamente (para handlers simples)
    if node_name in _NODE_REGISTRY:
        return _get_handler_from_registry(_NODE_REGISTRY, node_name, creds, "node")
    
    # Estrategia 3: Buscar action_name directamente (para handlers legacy)
    if action_name in _NODE_REGISTRY:
        return _get_handler_from_registry(_NODE_REGISTRY, action_name, creds, "node")
    
    # Si nada funciona, reportar error con información útil
    available_keys = list(_NODE_REGISTRY.keys())
    logger.error(f"No node handler found. Tried keys: ['{constructed_key}', '{node_name}', '{action_name}']. Available: {available_keys}")
    raise RuntimeError(f"No existe node handler para '{constructed_key}'. Intenté: '{node_name}', '{action_name}'. Disponibles: {available_keys}")

async def execute_node(
    node_name: str,
    action_name: str,
    params: Dict[str, Any],
    creds: Dict[str, Any],
    simulate: bool = False
) -> Dict[str, Any]:
    """
    Ejecuta un nodo real o simulado según el parámetro simulate
    
    Args:
        node_name: Nombre del nodo
        action_name: Nombre de la acción
        params: Parámetros del nodo
        creds: Credenciales
        simulate: Si True, genera datos fake. Si False, ejecuta realmente
    
    Returns:
        Dict con resultado real o fake
    """
    node_key = f"{node_name}.{action_name}"
    logger.debug(f"Ejecutando nodo ({'simulado' if simulate else 'real'}): {node_key}")
    
    if simulate:
        # Modo simulación: usar fake data registry
        from app.utils.fake_data import fake_data_registry
        import random
        
        fake_output = fake_data_registry.generate_fake_output(node_key, params)
        
        return {
            "status": "success",
            "output": fake_output,
            "duration_ms": random.randint(50, 1000),
            "simulated": True
        }
    
    # Modo real: ejecutar normalmente
    # Análisis inteligente de parámetros para nodos también
    if smart_parameter_handler.should_request_user_input(node_key, params):
        missing_info = smart_parameter_handler.get_missing_parameters_info(node_key, params)
        logger.info(f"Nodo {node_key} requiere input del usuario",
                   missing_count=missing_info["missing_count"])
        raise RequiresUserInputError(node_key, missing_info)
    
    # Si no necesita input del usuario, ejecutar normalmente
    handler = get_node_handler(node_name, action_name, creds)
    # 🔧 FIX: Pass creds inside params, not as separate argument
    params_with_creds = {**params, "creds": creds}
    return await handler.execute(params_with_creds)

_SCANNED = False

def scan_handlers() -> None:
    global _SCANNED
    if _SCANNED:
        return
    import app.handlers, pkgutil, importlib
    for _, module_name, _ in pkgutil.iter_modules(app.handlers.__path__):
        importlib.import_module(f"app.handlers.{module_name}")
    _SCANNED = True


def get_registered_handlers() -> Dict[str, Type[ActionHandler]]:
    """
    Returns all registered handlers from both tool and node registries.
    """
    # Ensure handlers are scanned first
    scan_handlers()
    
    # Combine both registries
    all_handlers = {}
    all_handlers.update(_TOOL_REGISTRY)
    all_handlers.update(_NODE_REGISTRY)
    
    return all_handlers


def get_registry_status() -> Dict[str, Any]:
    """
    Función de debug para inspeccionar el estado de los registries.
    Útil para debugging y verificación.
    """
    return {
        "tools_registered": len(_TOOL_REGISTRY),
        "nodes_registered": len(_NODE_REGISTRY),
        "tool_keys": list(_TOOL_REGISTRY.keys()),
        "node_keys": list(_NODE_REGISTRY.keys()),
        "scanned": _SCANNED
    }
