import time
import json
from uuid import uuid4, UUID
from typing import Any, Dict, List, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.connectors.factory import register_node
from app.routers.webhook_router import register_webhook, unregister_webhook
from .connector_handler import ActionHandler
from .trigger_registry import register_trigger_capability


@register_node("Form.webhook_trigger")
@register_trigger_capability("form_webhook", "Form.webhook_trigger", unschedule_method="unregister")
class FormWebhookTriggerHandler(ActionHandler):
    """
    🚀 FORM WEBHOOK TRIGGER HANDLER 2025
    
    Handler específico para webhooks de formularios (Typeform, Google Forms, Gravity Forms, etc.)
    
    Características:
    - ✅ Soporte multi-proveedor (Typeform, Google Forms, Gravity Forms)
    - ✅ Validación automática de payloads de formulario
    - ✅ Extracción estructurada de datos de campos
    - ✅ Filtrado por tipo de formulario y campos
    - ✅ Transformación a formato estándar
    - ✅ URLs de webhook dinámicas con tokens únicos
    - ✅ Validación de seguridad (HMAC, tokens, etc.)
    
    Parámetros esperados:
      • form_provider: "typeform" | "google_forms" | "gravity_forms" | "generic"
      • form_id: ID del formulario específico (opcional, para filtrado)
      • webhook_secret: Secret para validación HMAC/signature
      • field_mapping: Mapeo de campos del formulario a variables workflow
      • required_fields: Lista de campos requeridos para activar trigger
      • response_format: Formato de respuesta deseado ("json" | "form_data")
      • allowed_origins: Orígenes permitidos para CORS
      • auth_type: Tipo de autenticación ("none" | "token" | "hmac" | "signature")
    """

    # Mapeo de providers conocidos y sus características
    PROVIDER_CONFIGS = {
        "typeform": {
            "validation_header": "Typeform-Signature", 
            "payload_path": "form_response",
            "fields_path": "answers",
            "timestamp_field": "submitted_at"
        },
        "google_forms": {
            "validation_header": None,  # Google Forms no tiene HMAC nativo
            "payload_path": "responses",
            "fields_path": "responses",
            "timestamp_field": "timestamp"
        },
        "gravity_forms": {
            "validation_header": "X-GF-Signature",
            "payload_path": None,  # Payload directo
            "fields_path": "form",
            "timestamp_field": "date_created"
        },
        "generic": {
            "validation_header": "X-Webhook-Signature",
            "payload_path": None,
            "fields_path": "data",
            "timestamp_field": "timestamp"
        }
    }

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start = time.perf_counter()
        
        # Validar parámetros requeridos
        flow_id = params.get("flow_id")
        user_id = params.get("user_id")
        form_provider = params.get("form_provider", "generic").lower()
        
        if not flow_id:
            return {
                "status": "error",
                "error": "flow_id requerido para Form Webhook Trigger",
                "duration_ms": int((time.perf_counter() - start) * 1000),
            }

        if form_provider not in self.PROVIDER_CONFIGS:
            return {
                "status": "error", 
                "error": f"Provider '{form_provider}' no soportado. Opciones: {list(self.PROVIDER_CONFIGS.keys())}",
                "duration_ms": int((time.perf_counter() - start) * 1000),
            }

        # Generar token único para el webhook
        token = uuid4().hex
        provider_config = self.PROVIDER_CONFIGS[form_provider]
        
        # Preparar configuración específica del trigger
        trigger_args = {
            "production_path": f"/api/webhooks/forms/{token}",
            "test_path": f"/api/webhooks-test/forms/{token}",
            "provider": form_provider,
            "provider_config": provider_config,
            "form_id": params.get("form_id"),
            "webhook_secret": params.get("webhook_secret"),
            "field_mapping": params.get("field_mapping", {}),
            "required_fields": params.get("required_fields", []),
            "response_format": params.get("response_format", "json"),
            "allowed_origins": params.get("allowed_origins", ["*"]),
            "auth_type": params.get("auth_type", "hmac" if form_provider != "google_forms" else "none"),
            "methods": ["POST", "OPTIONS"],  # CORS support
            "token": token,
            # Configuración específica de validación
            "validation": {
                "validate_signature": form_provider in ["typeform", "gravity_forms"],
                "signature_header": provider_config["validation_header"],
                "require_form_id": params.get("require_form_id", False),
                "min_fields": params.get("min_fields", 1)
            }
        }

        # Si es solo validación/preparación, retornar configuración
        scheduler = params.get("scheduler")
        first_step = params.get("first_step")
        
        if not scheduler or not user_id or not first_step:
            duration_ms = int((time.perf_counter() - start) * 1000)
            return {
                "status": "success",
                "output": {
                    "trigger_type": "form_webhook",
                    "provider": form_provider,
                    "trigger_args": trigger_args,
                    "webhook_url": trigger_args["production_path"],
                    "test_url": trigger_args["test_path"],
                    "setup_instructions": self._get_setup_instructions(form_provider, trigger_args),
                    "supported_fields": self._get_supported_fields(form_provider)
                },
                "duration_ms": duration_ms,
            }

        # Registrar webhook dinámico especializado para formularios
        try:
            webhook_id = register_webhook(
                flow_id=UUID(flow_id) if isinstance(flow_id, str) else flow_id,
                user_id=user_id,
                trigger_args=trigger_args,
                webhook_type="form_webhook"  # Tipo especial para manejo diferenciado
            )
            
            duration_ms = int((time.perf_counter() - start) * 1000)
            return {
                "status": "success",
                "output": {
                    "trigger_type": "form_webhook",
                    "provider": form_provider,
                    "webhook_id": webhook_id,
                    "registered": True,
                    "trigger_args": trigger_args,
                    "webhook_url": trigger_args["production_path"],
                    "test_url": trigger_args["test_path"],
                    "token": token,
                    "setup_instructions": self._get_setup_instructions(form_provider, trigger_args),
                    "data_format": self._get_data_format_example(form_provider)
                },
                "duration_ms": duration_ms,
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error registrando Form Webhook: {str(e)}",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }

    def _get_setup_instructions(self, provider: str, trigger_args: Dict[str, Any]) -> Dict[str, Any]:
        """Genera instrucciones de configuración específicas por provider"""
        base_url = trigger_args["production_path"]
        
        instructions = {
            "typeform": {
                "steps": [
                    "1. Ve a tu panel de Typeform → Connect → Webhooks",
                    f"2. Agrega webhook URL: {base_url}",
                    "3. Selecciona eventos: 'form_response'",
                    f"4. Configura secret (opcional): {trigger_args.get('webhook_secret', 'N/A')}",
                    "5. Test webhook desde Typeform panel"
                ],
                "docs_url": "https://developer.typeform.com/webhooks/"
            },
            "google_forms": {
                "steps": [
                    "1. Instala add-on 'Email Notifications for Google Forms'",
                    "2. En el add-on, configura webhook notifications",
                    f"3. Webhook URL: {base_url}",
                    "4. Selecciona formato: JSON",
                    "5. Test enviando respuesta de prueba"
                ],
                "docs_url": "https://digitalinspiration.com/docs/form-notifications/webhooks",
                "note": "Google Forms requiere add-on para webhooks nativos"
            },
            "gravity_forms": {
                "steps": [
                    "1. Instala Gravity Forms Webhooks Add-On",
                    "2. Ve a Form Settings → Webhooks",
                    f"3. Request URL: {base_url}",
                    "4. Request Method: POST",
                    "5. Request Format: JSON",
                    f"6. Request Headers: X-GF-Signature: {trigger_args.get('webhook_secret', '[secret]')}"
                ],
                "docs_url": "https://docs.gravityforms.com/webhooks/"
            },
            "generic": {
                "steps": [
                    f"1. Configura tu sistema para enviar POST a: {base_url}",
                    "2. Content-Type: application/json",
                    f"3. Include signature header: X-Webhook-Signature (opcional)",
                    "4. Payload debe incluir 'data' object con campos del formulario",
                    "5. Test con herramientas like Postman/curl"
                ],
                "example_payload": {
                    "data": {
                        "name": "Juan Pérez",
                        "email": "juan@example.com",
                        "message": "Hola, me interesa el producto"
                    },
                    "timestamp": "2025-01-31T10:30:00Z",
                    "form_id": "contact_form"
                }
            }
        }
        
        return instructions.get(provider, instructions["generic"])

    def _get_supported_fields(self, provider: str) -> Dict[str, Any]:
        """Retorna tipos de campos soportados por provider"""
        common_fields = {
            "text": "Campos de texto simple",
            "email": "Direcciones de email", 
            "number": "Valores numéricos",
            "boolean": "Checkboxes/switches",
            "date": "Fechas y timestamps",
            "choice": "Selecciones múltiples",
            "file": "Archivos subidos"
        }
        
        provider_specific = {
            "typeform": {
                **common_fields,
                "rating": "Campos de rating/estrellas",
                "opinion_scale": "Escalas de opinión",
                "dropdown": "Menús desplegables"
            },
            "google_forms": {
                **common_fields,
                "paragraph": "Texto largo",
                "multiple_choice": "Opción múltiple",
                "checkboxes": "Casillas de verificación",
                "linear_scale": "Escala lineal"
            },
            "gravity_forms": {
                **common_fields,
                "textarea": "Áreas de texto",
                "select": "Campos select",
                "radio": "Botones radio",
                "checkbox": "Checkboxes"
            }
        }
        
        return provider_specific.get(provider, common_fields)

    def _get_data_format_example(self, provider: str) -> Dict[str, Any]:
        """Retorna ejemplo del formato de datos que recibirá el workflow"""
        examples = {
            "typeform": {
                "form_id": "ABC123",
                "form_response": {
                    "form_id": "ABC123",
                    "submitted_at": "2025-01-31T10:30:00Z",
                    "answers": [
                        {
                            "field": {"id": "name", "type": "short_text"},
                            "text": "Juan Pérez"
                        },
                        {
                            "field": {"id": "email", "type": "email"},
                            "email": "juan@example.com"
                        }
                    ]
                }
            },
            "google_forms": {
                "responses": [
                    {
                        "timestamp": "2025-01-31T10:30:00Z",
                        "responses": {
                            "¿Cuál es tu nombre?": "Juan Pérez",
                            "Email": "juan@example.com",
                            "Mensaje": "Me interesa el producto"
                        }
                    }
                ]
            },
            "gravity_forms": {
                "form": {
                    "id": "1",
                    "title": "Formulario Contacto",
                    "date_created": "2025-01-31 10:30:00"
                },
                "entry": {
                    "1": "Juan Pérez",
                    "2": "juan@example.com", 
                    "3": "Me interesa el producto"
                }
            }
        }
        
        return examples.get(provider, {
            "data": {
                "field_name": "field_value",
                "another_field": "another_value"
            },
            "timestamp": "2025-01-31T10:30:00Z"
        })

    async def unregister(self, webhook_id: str) -> Dict[str, Any]:
        """Cancela el webhook registrado"""
        try:
            unregister_webhook(webhook_id)
            return {
                "status": "success",
                "message": f"Form Webhook {webhook_id} cancelado exitosamente"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error cancelando Form Webhook {webhook_id}: {str(e)}"
            }

    @staticmethod
    def validate_form_payload(payload: Dict[str, Any], provider: str, trigger_args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Método estático para validar y transformar payloads de formularios
        Será usado por el webhook router para procesar datos entrantes
        """
        try:
            provider_config = FormWebhookTriggerHandler.PROVIDER_CONFIGS.get(provider, {})
            
            # Extraer datos según el provider
            if provider == "typeform":
                form_response = payload.get("form_response", {})
                answers = form_response.get("answers", [])
                
                # Transformar a formato estándar
                form_data = {}
                for answer in answers:
                    field_id = answer.get("field", {}).get("id", "unknown")
                    field_type = answer.get("field", {}).get("type", "text")
                    
                    # Extraer valor según tipo de campo
                    if field_type == "email":
                        form_data[field_id] = answer.get("email")
                    elif field_type in ["short_text", "long_text"]:
                        form_data[field_id] = answer.get("text")  
                    elif field_type == "number":
                        form_data[field_id] = answer.get("number")
                    elif field_type == "boolean":
                        form_data[field_id] = answer.get("boolean")
                    elif field_type == "choice":
                        form_data[field_id] = answer.get("choice", {}).get("label")
                    else:
                        # Fallback: buscar cualquier valor
                        form_data[field_id] = answer.get("text") or answer.get("email") or answer.get("number")
                
                return {
                    "status": "success",
                    "form_data": form_data,
                    "metadata": {
                        "provider": provider,
                        "form_id": form_response.get("form_id"),
                        "submitted_at": form_response.get("submitted_at"),
                        "total_fields": len(answers)
                    }
                }
                
            elif provider == "google_forms":
                responses = payload.get("responses", [])
                if not responses:
                    return {"status": "error", "error": "No responses found in Google Forms payload"}
                
                # Google Forms puede tener múltiples respuestas
                latest_response = responses[-1] if responses else {}
                form_data = latest_response.get("responses", {})
                
                return {
                    "status": "success", 
                    "form_data": form_data,
                    "metadata": {
                        "provider": provider,
                        "timestamp": latest_response.get("timestamp"),
                        "total_responses": len(responses),
                        "total_fields": len(form_data)
                    }
                }
                
            elif provider == "gravity_forms":
                entry = payload.get("entry", {})
                form_info = payload.get("form", {})
                
                # Gravity Forms usa IDs numéricos para campos
                form_data = {}
                for field_id, field_value in entry.items():
                    if field_id.isdigit():  # Solo campos de formulario (no metadata)
                        form_data[f"field_{field_id}"] = field_value
                
                return {
                    "status": "success",
                    "form_data": form_data,
                    "metadata": {
                        "provider": provider,
                        "form_id": form_info.get("id"),
                        "form_title": form_info.get("title"),
                        "date_created": form_info.get("date_created"),
                        "total_fields": len(form_data)
                    }
                }
                
            else:  # generic provider
                data = payload.get("data", payload)  # Fallback al payload completo
                
                return {
                    "status": "success",
                    "form_data": data,
                    "metadata": {
                        "provider": provider,
                        "timestamp": payload.get("timestamp"),
                        "form_id": payload.get("form_id"),
                        "total_fields": len(data) if isinstance(data, dict) else 0
                    }
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error validating {provider} payload: {str(e)}",
                "raw_payload": payload
            }