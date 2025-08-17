from typing import Dict, List, Any, Optional
import json
import re
import logging
from app.connectors.factory import register_tool
from app.dtos.page_customization_dto import PageElementAnalysisDto, PageValidationDto

# Simplified HTML parsing without external dependencies
try:
    from bs4 import BeautifulSoup
except ImportError:
    # Fallback if BeautifulSoup is not available
    BeautifulSoup = None

from app.ai.llm_clients.llm_service import get_llm_service, LLMService

logger = logging.getLogger(__name__)


@register_tool("modify_web_page")
class WebPageModifierHandler:
    """
    Handler especializado en modificar páginas web usando LLM.
    Genera cambios CSS/HTML seguros basados en prompts en lenguaje natural.
    """
    
    def __init__(self):
        self.llm_service = LLMService()
        self.allowed_css_properties = {
            'background-color', 'color', 'font-family', 'font-size', 'font-weight',
            'margin', 'padding', 'border', 'border-radius', 'width', 'height',
            'display', 'position', 'top', 'left', 'right', 'bottom', 'z-index',
            'opacity', 'box-shadow', 'text-align', 'line-height', 'letter-spacing'
        }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Ejecuta la modificación de página web
        
        Args:
            customization_prompt: Prompt en lenguaje natural
            current_html: HTML actual de la página
            target_element: Elemento específico a modificar (opcional)
            
        Returns:
            Dict con cambios generados y validaciones
        """
        try:
            customization_prompt = kwargs.get('customization_prompt', '')
            current_html = kwargs.get('current_html', '')
            target_element = kwargs.get('target_element', 'body')
            
            if not customization_prompt:
                return {
                    "success": False,
                    "error": "customization_prompt is required"
                }
            
            # 1. Analizar estructura HTML actual
            html_analysis = await self._analyze_html_structure(current_html)
            
            # 2. Generar modificaciones con LLM
            modifications = await self._generate_modifications(
                customization_prompt, 
                html_analysis, 
                target_element
            )
            
            # 3. Validar cambios generados
            validation = await self._validate_modifications(modifications)
            
            if not validation.is_valid:
                return {
                    "success": False,
                    "error": "Generated modifications failed validation",
                    "validation_errors": validation.validation_errors,
                    "security_issues": validation.security_issues
                }
            
            # 4. Aplicar cambios de manera segura
            applied_changes = await self._apply_modifications(current_html, modifications)
            
            return {
                "success": True,
                "applied_changes": applied_changes.get("changes_description", []),
                "css_styles": applied_changes.get("css", ""),
                "html_modifications": applied_changes.get("html", ""),
                "original_prompt": customization_prompt,
                "target_element": target_element
            }
            
        except Exception as e:
            logger.error(f"Error in WebPageModifierHandler: {str(e)}")
            return {
                "success": False,
                "error": f"Internal error: {str(e)}"
            }
    
    async def _analyze_html_structure(self, html_content: str) -> List[PageElementAnalysisDto]:
        """Analiza la estructura HTML para identificar elementos modificables"""
        if not html_content:
            return []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            elements = []
            
            # Analizar elementos principales
            for tag in soup.find_all(['body', 'div', 'header', 'nav', 'main', 'section', 'footer']):
                element_analysis = PageElementAnalysisDto(
                    element_type=tag.name,
                    element_id=tag.get('id'),
                    element_class=' '.join(tag.get('class', [])),
                    current_styles=self._extract_inline_styles(tag),
                    modifiable=True,
                    suggestions=self._generate_element_suggestions(tag)
                )
                elements.append(element_analysis)
            
            return elements
            
        except Exception as e:
            logger.error(f"Error analyzing HTML structure: {str(e)}")
            return []
    
    def _extract_inline_styles(self, tag) -> Dict[str, Any]:
        """Extrae estilos inline de un elemento"""
        style_attr = tag.get('style', '')
        styles = {}
        
        if style_attr:
            # Parse inline styles
            style_pairs = style_attr.split(';')
            for pair in style_pairs:
                if ':' in pair:
                    prop, value = pair.split(':', 1)
                    styles[prop.strip()] = value.strip()
        
        return styles
    
    def _generate_element_suggestions(self, tag) -> List[str]:
        """Genera sugerencias de modificación para un elemento"""
        suggestions = []
        
        if tag.name == 'body':
            suggestions = [
                "Cambiar color de fondo",
                "Modificar familia de fuente",
                "Ajustar márgenes y padding"
            ]
        elif tag.name in ['div', 'section']:
            suggestions = [
                "Cambiar colores",
                "Agregar bordes o sombras",
                "Modificar espaciado interno"
            ]
        elif tag.name in ['header', 'nav']:
            suggestions = [
                "Personalizar navegación",
                "Cambiar colores de header",
                "Agregar logo o branding"
            ]
        
        return suggestions
    
    async def _generate_modifications(self, prompt: str, html_analysis: List[PageElementAnalysisDto], target_element: str) -> Dict[str, Any]:
        """Genera modificaciones CSS/HTML usando LLM"""
        
        # Crear contexto para el LLM
        context = f"""
        TAREA: Generar modificaciones CSS/HTML seguras basadas en el siguiente prompt:
        PROMPT DEL USUARIO: {prompt}
        ELEMENTO OBJETIVO: {target_element}
        
        ESTRUCTURA HTML ACTUAL:
        {json.dumps([elem.dict() for elem in html_analysis], indent=2)}
        
        INSTRUCCIONES:
        1. Genera SOLO cambios CSS seguros (colores, fuentes, espaciado, etc.)
        2. NO agregues JavaScript ejecutable
        3. NO modifiques funcionalidad existente
        4. Enfócate en aspectos visuales únicamente
        5. Proporciona CSS válido y compatible con navegadores modernos
        
        RESPONDE EN JSON con esta estructura:
        {{
            "css_changes": "código CSS aquí",
            "html_additions": "HTML adicional si es necesario (ej: logos, imágenes)",
            "changes_description": ["descripción del cambio 1", "descripción del cambio 2"],
            "reasoning": "explicación de los cambios realizados"
        }}
        """
        
        try:
            # ✅ Usar LLM service real
            llm_service = get_llm_service()
            
            llm_response = await llm_service.generate_completion(
                model="gpt-4",  # Usar GPT-4 para mejor calidad CSS
                prompt=context,
                temperature=0.3,
                max_tokens=1000
            )
            
            # Parse JSON response
            modifications = json.loads(llm_response)
            return modifications
            
        except json.JSONDecodeError:
            logger.error("LLM response is not valid JSON")
            return {
                "css_changes": "",
                "html_additions": "",
                "changes_description": [],
                "reasoning": "Failed to parse LLM response"
            }
        except Exception as e:
            logger.error(f"Error generating modifications: {str(e)}")
            return {
                "css_changes": "",
                "html_additions": "",
                "changes_description": [],
                "reasoning": f"Error: {str(e)}"
            }
    
    async def _validate_modifications(self, modifications: Dict[str, Any]) -> PageValidationDto:
        """Valida que las modificaciones sean seguras"""
        validation_errors = []
        security_issues = []
        performance_warnings = []
        
        css_changes = modifications.get("css_changes", "")
        html_additions = modifications.get("html_additions", "")
        
        # Validar CSS
        if css_changes:
            css_validation = self._validate_css(css_changes)
            validation_errors.extend(css_validation.get("errors", []))
            security_issues.extend(css_validation.get("security", []))
            performance_warnings.extend(css_validation.get("performance", []))
        
        # Validar HTML
        if html_additions:
            html_validation = self._validate_html(html_additions)
            validation_errors.extend(html_validation.get("errors", []))
            security_issues.extend(html_validation.get("security", []))
        
        is_valid = len(validation_errors) == 0 and len(security_issues) == 0
        
        return PageValidationDto(
            is_valid=is_valid,
            validation_errors=validation_errors,
            security_issues=security_issues,
            performance_warnings=performance_warnings
        )
    
    def _validate_css(self, css_content: str) -> Dict[str, List[str]]:
        """Valida CSS para seguridad y validez"""
        errors = []
        security_issues = []
        performance_warnings = []
        
        # Buscar propiedades CSS peligrosas
        dangerous_patterns = [
            r'javascript:',
            r'expression\s*\(',
            r'@import',
            r'url\s*\(\s*["\']?javascript:',
            r'<script',
            r'</script'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, css_content, re.IGNORECASE):
                security_issues.append(f"Detected potentially dangerous CSS pattern: {pattern}")
        
        # Validar propiedades permitidas
        css_rules = css_content.split(';')
        for rule in css_rules:
            if ':' in rule:
                prop = rule.split(':')[0].strip().lower()
                if prop and prop not in self.allowed_css_properties:
                    errors.append(f"CSS property not allowed: {prop}")
        
        # Advertencias de rendimiento
        if len(css_content) > 5000:
            performance_warnings.append("Generated CSS is quite large, may affect performance")
        
        return {
            "errors": errors,
            "security": security_issues,
            "performance": performance_warnings
        }
    
    def _validate_html(self, html_content: str) -> Dict[str, List[str]]:
        """Valida HTML para seguridad"""
        errors = []
        security_issues = []
        
        # Buscar elementos peligrosos
        dangerous_patterns = [
            r'<script',
            r'javascript:',
            r'on\w+\s*=',  # event handlers like onclick, onload, etc.
            r'<iframe',
            r'<object',
            r'<embed'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, html_content, re.IGNORECASE):
                security_issues.append(f"Detected potentially dangerous HTML pattern: {pattern}")
        
        # Validar estructura HTML básica
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            # HTML parsing successful
        except Exception:
            errors.append("Invalid HTML structure")
        
        return {
            "errors": errors,
            "security": security_issues
        }
    
    async def _apply_modifications(self, current_html: str, modifications: Dict[str, Any]) -> Dict[str, Any]:
        """Aplica las modificaciones de manera segura"""
        css_changes = modifications.get("css_changes", "")
        html_additions = modifications.get("html_additions", "")
        changes_description = modifications.get("changes_description", [])
        
        return {
            "css": css_changes,
            "html": html_additions,
            "changes_description": changes_description
        }