"""
Generadores de datos fake para nodos de Email
Se auto-registran usando decorators
"""

import random
from typing import Dict, Any
from app.utils.fake_data.registry import register_fake_generator
from app.utils.template_engine import template_engine


@register_fake_generator("Gmail.send_messages")
def gmail_send_fake_data(params: Dict[str, Any]) -> Dict[str, Any]:
    """Genera datos fake para envío de Gmail"""
    
    to_email = params.get("to", template_engine.generate_fake_data_for_field("email"))
    subject = params.get("subject", "Asunto de prueba")
    
    return {
        "message_id": f"<{template_engine.generate_fake_data_for_field('uuid')}@gmail.com>",
        "thread_id": template_engine.generate_fake_data_for_field("id"),
        "status": "sent",
        "to": to_email,
        "subject": subject,
        "sent_at": template_engine.generate_fake_data_for_field("datetime"),
        "size_estimate": random.randint(1024, 50000),
        "labels": ["SENT", "INBOX"]
    }


@register_fake_generator("Outlook.send_mail")  
def outlook_send_fake_data(params: Dict[str, Any]) -> Dict[str, Any]:
    """Genera datos fake para envío de Outlook"""
    
    return {
        "message_id": template_engine.generate_fake_data_for_field("uuid"),
        "status": "sent",
        "to": params.get("to", template_engine.generate_fake_data_for_field("email")),
        "subject": params.get("subject", "Fake subject"),
        "sent_at": template_engine.generate_fake_data_for_field("datetime"),
        "conversation_id": template_engine.generate_fake_data_for_field("uuid"),
        "has_attachments": random.choice([True, False])
    }