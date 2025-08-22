# app/constants/webhook_constants.py

"""
Constantes para identificación escalable de webhook triggers
"""

# Nodos que generan webhooks y URLs públicas
WEBHOOK_TRIGGER_NODES = {
    "Webhook": {
        "actions": ["trigger"],
        "generates_urls": True,
        "url_type": "generic_webhook"
    },
    "Form.webhook_trigger": {
        "actions": ["webhook_trigger"],
        "generates_urls": True,
        "url_type": "form_webhook"
    },
    "Github.webhook": {
        "actions": ["webhook_trigger"],
        "generates_urls": True,
        "url_type": "github_webhook"
    },
    "Slack.webhook": {
        "actions": ["webhook_trigger"],
        "generates_urls": True,
        "url_type": "slack_webhook"
    },
    # Triggers que no generan URLs públicas (solo internos)
    "Gmail.trigger": {
        "actions": ["polling_trigger", "push_trigger"],
        "generates_urls": False,
        "url_type": None
    },
    "Drive.trigger": {
        "actions": ["polling_trigger", "push_trigger"],
        "generates_urls": False,
        "url_type": None
    },
    "Sheets.trigger": {
        "actions": ["polling_trigger"],
        "generates_urls": False,
        "url_type": None
    }
}

def is_webhook_trigger(node_name: str, action_name: str = None) -> bool:
    """
    Verifica si un nodo/acción es un webhook trigger
    
    Args:
        node_name: Nombre del nodo (ej: "Form.webhook_trigger")
        action_name: Nombre de la acción (opcional)
    
    Returns:
        True si es webhook trigger
    """
    if node_name not in WEBHOOK_TRIGGER_NODES:
        return False
    
    node_config = WEBHOOK_TRIGGER_NODES[node_name]
    
    # Si no se especifica action_name, verificar si genera URLs
    if action_name is None:
        return node_config["generates_urls"]
    
    # Verificar acción específica
    return action_name in node_config["actions"] and node_config["generates_urls"]

def get_webhook_config(node_name: str):
    """
    Obtiene configuración de webhook para un nodo
    
    Returns:
        Dict con configuración o None
    """
    return WEBHOOK_TRIGGER_NODES.get(node_name)

def get_all_webhook_nodes() -> list:
    """
    Obtiene todos los nodos que generan webhooks
    """
    return [
        node_name for node_name, config in WEBHOOK_TRIGGER_NODES.items()
        if config["generates_urls"]
    ]