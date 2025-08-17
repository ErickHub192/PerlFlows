from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any


class PageCustomizationRequestDto(BaseModel):
    """DTO para solicitar personalización de página web"""
    agent_id: str = Field(..., description="ID del agente a personalizar")
    customization_prompt: str = Field(..., description="Prompt en lenguaje natural para personalizar la página")
    target_element: Optional[str] = Field(None, description="Elemento específico a modificar (opcional)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "agent_123",
                "customization_prompt": "Cambia el color de fondo a azul claro y agrega un logo en la esquina superior izquierda",
                "target_element": "body"
            }
        }


class PageCustomizationResponseDto(BaseModel):
    """DTO para respuesta de personalización"""
    success: bool = Field(..., description="Indica si la personalización fue exitosa")
    applied_changes: List[str] = Field(..., description="Lista de cambios aplicados")
    css_styles: str = Field(..., description="CSS generado para los cambios")
    html_modifications: Optional[str] = Field(None, description="Modificaciones HTML si aplica")
    preview_url: Optional[str] = Field(None, description="URL para preview de cambios")
    error_message: Optional[str] = Field(None, description="Mensaje de error si falló")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "applied_changes": [
                    "Cambió color de fondo a #e3f2fd",
                    "Agregó logo en esquina superior izquierda"
                ],
                "css_styles": "body { background-color: #e3f2fd; } .logo { position: absolute; top: 10px; left: 10px; }",
                "html_modifications": "<img class='logo' src='/static/logo.png' alt='Logo'>",
                "preview_url": "/embed/agent_123?preview=true"
            }
        }


class PageTemplateDto(BaseModel):
    """DTO para templates de página"""
    template_id: str = Field(..., description="ID único del template")
    agent_id: str = Field(..., description="ID del agente asociado")
    html_content: str = Field(..., description="Contenido HTML del template")
    css_styles: str = Field(..., description="Estilos CSS del template")
    javascript_code: Optional[str] = Field(None, description="Código JavaScript adicional")
    is_active: bool = Field(True, description="Indica si el template está activo")
    created_at: Optional[str] = Field(None, description="Fecha de creación")
    updated_at: Optional[str] = Field(None, description="Fecha de última actualización")


class PageElementAnalysisDto(BaseModel):
    """DTO para análisis de elementos de la página"""
    element_type: str = Field(..., description="Tipo de elemento (div, button, etc.)")
    element_id: Optional[str] = Field(None, description="ID del elemento")
    element_class: Optional[str] = Field(None, description="Clases CSS del elemento")
    current_styles: Dict[str, Any] = Field(..., description="Estilos actuales del elemento")
    modifiable: bool = Field(..., description="Indica si el elemento puede ser modificado")
    suggestions: List[str] = Field(..., description="Sugerencias de modificación")


class PageValidationDto(BaseModel):
    """DTO para validación de cambios en la página"""
    is_valid: bool = Field(..., description="Indica si los cambios son válidos")
    validation_errors: List[str] = Field(..., description="Lista de errores de validación")
    security_issues: List[str] = Field(..., description="Lista de problemas de seguridad detectados")
    performance_warnings: List[str] = Field(..., description="Advertencias de rendimiento")
    
    class Config:
        json_schema_extra = {
            "example": {
                "is_valid": True,
                "validation_errors": [],
                "security_issues": [],
                "performance_warnings": ["El CSS generado podría afectar el rendimiento en móviles"]
            }
        }