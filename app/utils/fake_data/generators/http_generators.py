"""
Generadores de datos fake para nodos HTTP
Se auto-registran usando el decorator @register_fake_generator
"""

import random
from typing import Dict, Any
from app.utils.fake_data.registry import register_fake_generator
from app.utils.template_engine import template_engine


@register_fake_generator("HTTP_Request.request")
def http_request_fake_data(params: Dict[str, Any]) -> Dict[str, Any]:
    """Genera datos fake realistas para HTTP requests"""
    
    method = params.get("method", "GET").upper()
    url = params.get("url", "https://api.ejemplo.com/endpoint")
    
    # Status codes realistas según método
    status_codes = {
        "GET": [200, 404, 403],
        "POST": [200, 201, 400, 422],
        "PUT": [200, 404, 400],
        "DELETE": [200, 204, 404],
        "PATCH": [200, 400, 404]
    }
    
    status_code = random.choice(status_codes.get(method, [200]))
    
    # Body dinámico según status
    if status_code >= 400:
        body = {
            "error": True,
            "message": f"Fake error for {method} request",
            "code": status_code
        }
    else:
        body = {
            "success": True,
            "data": {
                "id": template_engine.generate_fake_data_for_field("id"),
                "timestamp": template_engine.generate_fake_data_for_field("timestamp"),
                "processed": True
            },
            "meta": {
                "method": method,
                "url": url
            }
        }
    
    return {
        "status_code": status_code,
        "headers": {
            "content-type": "application/json",
            "x-request-id": template_engine.generate_fake_data_for_field("uuid"),
            "date": template_engine.generate_fake_data_for_field("datetime")
        },
        "body": body,
        "url": url,
        "method": method,
        "duration_ms": random.randint(100, 2000)
    }