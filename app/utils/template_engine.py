"""
Template Engine para Workflows estilo n8n
Usa pystache para template processing y genera datos fake realistas para dryrun
"""

import pystache
import re
import random
import uuid
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class WorkflowTemplateEngine:
    """
    Motor de templates para workflows que soporta:
    1. Sintaxis {{step.output.field}} para referenciar outputs de pasos anteriores
    2. Generación automática de datos fake para dryrun
    3. Resolución de templates con datos reales
    """
    
    def __init__(self):
        self.renderer = pystache.Renderer()
        self.fake_data_generators = self._init_fake_generators()
    
    def _init_fake_generators(self) -> Dict[str, callable]:
        """Inicializa generadores de datos fake basados en nombres de campos"""
        return {
            # Emails
            'email': lambda: random.choice([
                'juan.perez@ejemplo.com',
                'maria.garcia@test.com', 
                'carlos.lopez@demo.org',
                'ana.martinez@prueba.es'
            ]),
            'correo': lambda: self.fake_data_generators['email'](),
            
            # Nombres
            'name': lambda: random.choice([
                'Juan Pérez', 'María García', 'Carlos López', 
                'Ana Martínez', 'Luis Rodríguez', 'Carmen Sánchez'
            ]),
            'nombre': lambda: self.fake_data_generators['name'](),
            'full_name': lambda: self.fake_data_generators['name'](),
            'user_name': lambda: self.fake_data_generators['name'](),
            
            # IDs
            'id': lambda: f"abc{random.randint(100, 999)}",
            'user_id': lambda: str(random.randint(10000, 99999)),
            'order_id': lambda: f"ORD-{random.randint(1000, 9999)}",
            'ticket_id': lambda: f"TKT-{random.randint(100, 999)}",
            'uuid': lambda: str(uuid.uuid4()),
            
            # URLs
            'url': lambda: random.choice([
                'https://api.ejemplo.com/data',
                'https://webhook.test.com/endpoint',
                'https://service.demo.org/api/v1/resource'
            ]),
            'webhook_url': lambda: f"https://webhook.test.com/{uuid.uuid4().hex[:8]}",
            'api_url': lambda: 'https://api.ejemplo.com/v1/endpoint',
            
            # Números
            'count': lambda: random.randint(1, 100),
            'total': lambda: random.randint(100, 10000),
            'amount': lambda: round(random.uniform(10.0, 1000.0), 2),
            'price': lambda: round(random.uniform(5.0, 500.0), 2),
            'quantity': lambda: random.randint(1, 50),
            
            # Texto
            'message': lambda: random.choice([
                'Operación completada exitosamente',
                'Datos procesados correctamente',
                'Tarea ejecutada sin errores',
                'Workflow ejecutado satisfactoriamente'
            ]),
            'description': lambda: 'Descripción de ejemplo generada automáticamente',
            'title': lambda: 'Título de ejemplo',
            'subject': lambda: 'Asunto del mensaje de prueba',
            
            # Fechas
            'date': lambda: datetime.now().strftime('%Y-%m-%d'),
            'datetime': lambda: datetime.now().isoformat(),
            'timestamp': lambda: int(datetime.now().timestamp()),
            'created_at': lambda: (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat(),
            
            # Estados
            'status': lambda: random.choice(['success', 'completed', 'active', 'pending']),
            'state': lambda: random.choice(['active', 'inactive', 'draft', 'published']),
            
            # Booleanos
            'active': lambda: random.choice([True, False]),
            'enabled': lambda: random.choice([True, False]),
            'success': lambda: True,  # Para dryrun siempre exitoso
            
            # Genéricos
            'data': lambda: {'ejemplo': 'valor', 'tipo': 'datos_fake'},
            'response': lambda: {'status': 'ok', 'message': 'Respuesta de ejemplo'},
            'result': lambda: {'processed': True, 'items': random.randint(1, 20)}
        }
    
    def generate_fake_data_for_field(self, field_name: str, field_type: str = None) -> Any:
        """
        Genera datos fake basado en el nombre del campo
        
        Args:
            field_name: Nombre del campo (email, name, id, etc.)
            field_type: Tipo opcional para casos específicos
            
        Returns:
            Valor fake apropiado para el campo
        """
        field_lower = field_name.lower()
        
        # Buscar coincidencia exacta primero
        if field_lower in self.fake_data_generators:
            return self.fake_data_generators[field_lower]()
        
        # Buscar coincidencias parciales
        for pattern, generator in self.fake_data_generators.items():
            if pattern in field_lower:
                return generator()
        
        # Fallback basado en tipo
        if field_type:
            type_lower = field_type.lower()
            if 'int' in type_lower or 'number' in type_lower:
                return random.randint(1, 1000)
            elif 'bool' in type_lower:
                return random.choice([True, False])
            elif 'str' in type_lower or 'text' in type_lower:
                return f"valor_fake_{random.randint(100, 999)}"
        
        # Fallback final
        return f"fake_{field_name}_{random.randint(100, 999)}"
    
    def generate_fake_output_structure(self, expected_fields: List[str] = None) -> Dict[str, Any]:
        """
        Genera una estructura de output fake realista
        
        Args:
            expected_fields: Lista opcional de campos esperados
            
        Returns:
            Diccionario con estructura fake
        """
        if expected_fields:
            return {field: self.generate_fake_data_for_field(field) for field in expected_fields}
        
        # Estructura genérica si no se especifican campos
        return {
            'id': self.generate_fake_data_for_field('id'),
            'status': 'success',
            'message': self.generate_fake_data_for_field('message'),
            'data': {
                'processed': True,
                'timestamp': self.generate_fake_data_for_field('timestamp'),
                'count': self.generate_fake_data_for_field('count')
            }
        }
    
    def render_template(self, template: str, context: Dict[str, Any]) -> str:
        """
        Renderiza un template usando pystache con el contexto proporcionado
        
        Args:
            template: String con sintaxis {{step.output.field}}
            context: Contexto con datos de pasos anteriores
            
        Returns:
            String renderizado
        """
        try:
            return self.renderer.render(template, context)
        except Exception as e:
            logger.error(f"Error renderizando template '{template}': {e}")
            return template  # Devolver original si falla
    
    def resolve_template_in_params(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resuelve templates en todos los parámetros de un step
        🔧 FIX: Ensure all UUIDs are converted to strings
        
        Args:
            params: Parámetros que pueden contener templates
            context: Contexto con outputs de pasos anteriores
            
        Returns:
            Parámetros con templates resueltos
        """
        def resolve_value(value):
            from uuid import UUID
            
            # 🔧 FIX: Convert UUID objects to strings immediately
            if isinstance(value, UUID):
                logger.debug(f"🔧 TEMPLATE ENGINE: Converting UUID {value} to string")
                return str(value)
            elif isinstance(value, str):
                resolved = self.render_template(value, context)
                # Double-check resolved value isn't a UUID object
                if isinstance(resolved, UUID):
                    logger.debug(f"🔧 TEMPLATE ENGINE: Template resolved to UUID {resolved}, converting to string")
                    return str(resolved)
                return resolved
            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve_value(item) for item in value]
            else:
                return value
        
        resolved = {key: resolve_value(value) for key, value in params.items()}
        logger.debug(f"🔧 TEMPLATE RESOLVED: {len(resolved)} params processed, no UUID objects remaining")
        return resolved
    
    def build_context_from_outputs(self, step_outputs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Construye el contexto para templates desde los outputs de pasos ejecutados
        
        Args:
            step_outputs: Dict con formato {step_id: {"status": "success", "output": {...}, "duration_ms": 100}}
            
        Returns:
            Contexto formateado para pystache
        """
        context = {}
        
        for step_id, step_result in step_outputs.items():
            # Crear estructura compatible con pystache
            context[step_id] = {
                'output': step_result.get('output', {}),
                'status': step_result.get('status', 'unknown'),
                'duration_ms': step_result.get('duration_ms', 0)
            }
            
            # También agregar alias sin números para facilidad de uso
            # step1 -> step, httpRequest1 -> httpRequest, etc.
            clean_name = re.sub(r'\d+$', '', step_id)
            if clean_name != step_id and clean_name not in context:
                context[clean_name] = context[step_id]
        
        return context
    
    def extract_template_variables(self, template: str) -> List[str]:
        """
        Extrae todas las variables de template de un string
        
        Args:
            template: String que puede contener {{variable.path}}
            
        Returns:
            Lista de variables encontradas
        """
        pattern = r'\{\{([^}]+)\}\}'
        matches = re.findall(pattern, template)
        return [match.strip() for match in matches]
    
    def validate_template_context(self, template: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida que el contexto contiene todas las variables necesarias para el template
        
        Args:
            template: Template a validar
            context: Contexto disponible
            
        Returns:
            Dict con información de validación: {valid: bool, missing: [str], available: [str]}
        """
        required_vars = self.extract_template_variables(template)
        missing_vars = []
        
        for var in required_vars:
            # Navegar path anidado (ej: step1.output.email)
            parts = var.split('.')
            current = context
            
            try:
                for part in parts:
                    current = current[part]
            except (KeyError, TypeError):
                missing_vars.append(var)
        
        return {
            'valid': len(missing_vars) == 0,
            'missing': missing_vars,
            'required': required_vars,
            'available': list(context.keys())
        }


# Instancia global para reutilizar
template_engine = WorkflowTemplateEngine()


# Factory function para dependency injection
def get_template_engine() -> WorkflowTemplateEngine:
    """Factory para inyección de dependencias"""
    return template_engine