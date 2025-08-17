from typing import Dict, List, Optional, Any
import json
import uuid
from datetime import datetime
from uuid import UUID
from fastapi import Depends
from app.dtos.page_customization_dto import (
    PageCustomizationRequestDto,
    PageCustomizationResponseDto,
    PageTemplateDto,
    PageValidationDto
)
from app.handlers.web_page_modifier_handler import WebPageModifierHandler
from app.repositories.ai_agent_repository import AIAgentRepository
from app.repositories.page_template_repository import PageTemplateRepository, get_page_template_repository
import logging

logger = logging.getLogger(__name__)


class PageCustomizationService:
    """
    Servicio para manejar la personalización de páginas web deployadas.
    Coordina entre el agente modificador y la persistencia de templates.
    """
    
    def __init__(self, agent_repository: AIAgentRepository, template_repository: PageTemplateRepository):
        self.web_modifier = WebPageModifierHandler()
        self.agent_repository = agent_repository
        self.template_repository = template_repository
    
    async def customize_page(self, request: PageCustomizationRequestDto) -> PageCustomizationResponseDto:
        """
        Personaliza una página web basada en prompt de lenguaje natural
        
        Args:
            request: Datos de la solicitud de personalización
            
        Returns:
            Respuesta con los cambios aplicados o errores
        """
        try:
            # 1. Validar que el agente existe
            agent = await self.agent_repository.get_by_id(request.agent_id)
            if not agent:
                return PageCustomizationResponseDto(
                    success=False,
                    applied_changes=[],
                    css_styles="",
                    error_message=f"Agent with ID {request.agent_id} not found"
                )
            
            # 2. Obtener template actual o crear uno base
            current_template = await self.get_current_template(request.agent_id)
            
            # 3. Ejecutar modificaciones usando el handler especializado
            modification_result = await self.web_modifier.execute(
                customization_prompt=request.customization_prompt,
                current_html=current_template.html_content,
                target_element=request.target_element or "body"
            )
            
            if not modification_result.get("success", False):
                return PageCustomizationResponseDto(
                    success=False,
                    applied_changes=[],
                    css_styles="",
                    error_message=modification_result.get("error", "Unknown error occurred")
                )
            
            # 4. Crear nuevo template con las modificaciones
            updated_template = await self._create_updated_template(
                current_template,
                modification_result,
                request.customization_prompt
            )
            
            # 5. Guardar template actualizado
            save_success = await self.save_template(request.agent_id, updated_template)
            
            if not save_success:
                logger.warning(f"Failed to save template for agent {request.agent_id}")
            
            # 6. Preparar respuesta
            return PageCustomizationResponseDto(
                success=True,
                applied_changes=modification_result.get("applied_changes", []),
                css_styles=modification_result.get("css_styles", ""),
                html_modifications=modification_result.get("html_modifications"),
                preview_url=f"/embed/{request.agent_id}?preview=true"
            )
            
        except Exception as e:
            logger.error(f"Error in customize_page: {str(e)}")
            return PageCustomizationResponseDto(
                success=False,
                applied_changes=[],
                css_styles="",
                error_message=f"Internal server error: {str(e)}"
            )
    
    async def get_current_template(self, agent_id: str) -> PageTemplateDto:
        """
        Obtiene el template actual de un agente o crea uno base
        
        Args:
            agent_id: ID del agente
            
        Returns:
            Template actual o template base
        """
        try:
            # ✅ Buscar en base de datos
            template = await self.template_repository.get_active_template(UUID(agent_id))
            
            if template:
                return PageTemplateDto(
                    id=str(template.id),
                    agent_id=str(template.agent_id),
                    name=template.template_name,
                    html_content=template.html_content or self._get_base_html(),
                    css_content=template.css_content or "",
                    js_content=template.js_content or "",
                    description=template.description or "Current template",
                    created_at=template.created_at.isoformat(),
                    updated_at=template.updated_at.isoformat(),
                    version=template.version
                )
            
            # Si no existe, crear template base
            return self._create_base_template(agent_id)
            
        except Exception as e:
            logger.error(f"Error getting template for agent {agent_id}: {str(e)}")
            return self._create_base_template(agent_id)
        base_template = self._get_base_template(agent_id)
        
    
    def _create_base_template(self, agent_id: str) -> PageTemplateDto:
        """Crea un template base para un agente"""
        return PageTemplateDto(
            id="base",
            agent_id=agent_id,
            name="default",
            html_content=self._get_base_html(),
            css_content="",
            js_content="",
            description="Base template",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            version=1,
            is_active=True
        )
    
    def _get_base_html(self) -> str:
        """Retorna HTML base para nuevos templates"""
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@3.4.1/dist/tailwind.min.css" rel="stylesheet" />
    <style id="custom-styles">
        /* Estilos personalizados se agregan aquí */
    </style>
</head>
<body class="bg-gray-50 text-gray-900">
    <!-- Botón de Edición -->
    <button id="edit-page-btn" class="fixed top-4 right-4 z-50 bg-blue-500 text-white px-3 py-2 rounded-lg shadow-lg hover:bg-blue-600 transition-colors">
        ✏️ Editar Página
    </button>
    
    <!-- Aplicación Principal -->
    <div id="app" class="h-screen p-4">
        <div class="max-w-4xl mx-auto">
            <h1 class="text-2xl font-bold mb-4">Chat con Agente IA</h1>
            <div id="chat-container" class="bg-white rounded-lg shadow-md p-4">
                <!-- El chat se carga aquí dinámicamente -->
            </div>
        </div>
    </div>
    
    <!-- Modal de Edición -->
    <div id="edit-modal" class="hidden fixed inset-0 bg-black bg-opacity-50 z-40">
        <!-- Modal content se carga dinámicamente -->
    </div>
    
    <script type="module" src="/static/embed/main.js"></script>
</body>
</html>"""
    
    async def _create_updated_template(
        self, 
        current_template: PageTemplateDto, 
        modification_result: Dict[str, Any],
        original_prompt: str
    ) -> PageTemplateDto:
        """Crea un template actualizado con las modificaciones"""
        
        # Combinar CSS existente con nuevos estilos
        existing_css = current_template.css_styles
        new_css = modification_result.get("css_styles", "")
        combined_css = f"{existing_css}\n\n/* Personalización: {original_prompt} */\n{new_css}"
        
        # Actualizar HTML si hay modificaciones
        updated_html = current_template.html_content
        html_modifications = modification_result.get("html_modifications", "")
        
        if html_modifications:
            # Insertar HTML modifications en un lugar apropiado
            # Por ejemplo, antes del cierre de </body>
            updated_html = updated_html.replace(
                "</body>",
                f"{html_modifications}\n</body>"
            )
        
        # Actualizar el <style> tag con el nuevo CSS
        if "<style id=\"custom-styles\">" in updated_html:
            # Reemplazar el contenido del style tag
            import re
            pattern = r'(<style id="custom-styles">)(.*?)(</style>)'
            replacement = f'\\1\n{combined_css}\n\\3'
            updated_html = re.sub(pattern, replacement, updated_html, flags=re.DOTALL)
        
        return PageTemplateDto(
            template_id=str(uuid.uuid4()),
            agent_id=current_template.agent_id,
            html_content=updated_html,
            css_styles=combined_css,
            javascript_code=current_template.javascript_code,
            is_active=True,
            created_at=current_template.created_at,
            updated_at=datetime.now().isoformat()
        )
    
    async def save_template(self, agent_id: str, template: PageTemplateDto) -> bool:
        """
        Guarda un template de página en base de datos
        
        Args:
            agent_id: ID del agente
            template: Template a guardar
            
        Returns:
            True si se guardó exitosamente
        """
        try:
            # ✅ Persistencia real en base de datos
            template_data = {
                "template_name": getattr(template, 'name', 'default'),
                "html_content": getattr(template, 'html_content', ''),
                "css_content": getattr(template, 'css_content', ''),
                "js_content": getattr(template, 'js_content', ''),
                "description": getattr(template, 'description', 'Auto-generated template'),
                "customization_prompt": getattr(template, 'last_prompt', ''),
                "applied_changes": getattr(template, 'changes_history', {}),
                "is_active": True
            }
            
            saved_template = await self.template_repository.create_template(
                agent_id=UUID(agent_id),
                template_data=template_data
            )
            
            logger.info(f"Template saved for agent {agent_id}, version {saved_template.version}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving template for agent {agent_id}: {str(e)}")
            return False
    
    async def preview_changes(self, agent_id: str, changes: Dict[str, Any]) -> str:
        """
        Genera un preview de los cambios sin aplicarlos permanentemente
        
        Args:
            agent_id: ID del agente
            changes: Cambios a previsualizar
            
        Returns:
            HTML con los cambios aplicados temporalmente
        """
        try:
            current_template = await self.get_current_template(agent_id)
            
            # Aplicar cambios temporalmente
            preview_template = await self._create_updated_template(
                current_template,
                changes,
                "Preview"
            )
            
            return preview_template.html_content
            
        except Exception as e:
            logger.error(f"Error generating preview for agent {agent_id}: {str(e)}")
            return ""
    
    async def get_template_history(self, agent_id: str) -> List[PageTemplateDto]:
        """
        Obtiene el historial de templates de un agente
        
        Args:
            agent_id: ID del agente
            
        Returns:
            Lista de templates históricos
        """
        try:
            # ✅ Obtener historial de base de datos
            templates = await self.template_repository.get_template_history(UUID(agent_id))
            
            return [
                PageTemplateDto(
                    id=str(template.id),
                    agent_id=str(template.agent_id),
                    name=template.template_name,
                    html_content=template.html_content or "",
                    css_content=template.css_content or "",
                    js_content=template.js_content or "",
                    description=template.description or f"Version {template.version}",
                    created_at=template.created_at.isoformat(),
                    updated_at=template.updated_at.isoformat(),
                    version=template.version,
                    is_active=template.is_active
                )
                for template in templates
            ]
            
        except Exception as e:
            logger.error(f"Error getting template history for agent {agent_id}: {str(e)}")
            return []
    
    async def rollback_template(self, agent_id: str, template_id: str) -> bool:
        """
        Revierte a una versión anterior del template
        
        Args:
            agent_id: ID del agente
            template_id: ID del template al que revertir
            
        Returns:
            True si se revirtió exitosamente
        """
        try:
            # ✅ Activar template específico usando repositorio
            success = await self.template_repository.activate_template(
                agent_id=UUID(agent_id),
                template_id=int(template_id)
            )
            
            if success:
                logger.info(f"Successfully rolled back agent {agent_id} to template {template_id}")
            else:
                logger.warning(f"Failed to rollback agent {agent_id} to template {template_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error rolling back template for agent {agent_id}: {str(e)}")
            return False


# Factory para FastAPI DI
def get_page_customization_service(
    agent_repository: AIAgentRepository = Depends(lambda: AIAgentRepository()),
    template_repository: PageTemplateRepository = Depends(get_page_template_repository)
) -> PageCustomizationService:
    """
    Factory para inyección de dependencias
    ✅ Inyecta repositorios usando dependency injection
    """
    return PageCustomizationService(agent_repository, template_repository)