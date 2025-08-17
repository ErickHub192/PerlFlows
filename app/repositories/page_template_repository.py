"""
Repository para manejo de Page Templates
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, desc
from fastapi import Depends

from app.db.models import PageTemplate
from app.db.database import get_db


class PageTemplateRepository:
    """Repository para operaciones de Page Templates"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_active_template(self, agent_id: UUID, template_name: str = "default") -> Optional[PageTemplate]:
        """Obtiene el template activo para un agente"""
        stmt = select(PageTemplate).where(
            and_(
                PageTemplate.agent_id == agent_id,
                PageTemplate.template_name == template_name,
                PageTemplate.is_active == True
            )
        ).order_by(desc(PageTemplate.version)).limit(1)
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_template_by_version(self, agent_id: UUID, template_name: str, version: int) -> Optional[PageTemplate]:
        """Obtiene un template específico por versión"""
        stmt = select(PageTemplate).where(
            and_(
                PageTemplate.agent_id == agent_id,
                PageTemplate.template_name == template_name,
                PageTemplate.version == version
            )
        )
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_template_history(self, agent_id: UUID, template_name: str = "default") -> List[PageTemplate]:
        """Obtiene historial de versiones de un template"""
        stmt = select(PageTemplate).where(
            and_(
                PageTemplate.agent_id == agent_id,
                PageTemplate.template_name == template_name
            )
        ).order_by(desc(PageTemplate.version))
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def create_template(self, agent_id: UUID, template_data: Dict[str, Any]) -> PageTemplate:
        """Crea un nuevo template"""
        # Obtener la próxima versión
        next_version = await self._get_next_version(agent_id, template_data.get("template_name", "default"))
        
        # Desactivar template anterior si existe
        if template_data.get("is_active", True):
            await self._deactivate_previous_templates(agent_id, template_data.get("template_name", "default"))
        
        template = PageTemplate(
            agent_id=agent_id,
            template_name=template_data.get("template_name", "default"),
            html_content=template_data.get("html_content"),
            css_content=template_data.get("css_content"),
            js_content=template_data.get("js_content"),
            version=next_version,
            is_active=template_data.get("is_active", True),
            description=template_data.get("description"),
            customization_prompt=template_data.get("customization_prompt"),
            applied_changes=template_data.get("applied_changes", {})
        )
        
        self.session.add(template)
        await self.session.commit()
        await self.session.refresh(template)
        
        return template
    
    async def update_template(self, template_id: int, updates: Dict[str, Any]) -> Optional[PageTemplate]:
        """Actualiza un template existente"""
        stmt = update(PageTemplate).where(
            PageTemplate.id == template_id
        ).values(**updates).returning(PageTemplate)
        
        result = await self.session.execute(stmt)
        await self.session.commit()
        
        return result.scalar_one_or_none()
    
    async def activate_template(self, agent_id: UUID, template_id: int) -> bool:
        """Activa un template específico y desactiva los demás"""
        # Obtener el template a activar
        template = await self.session.get(PageTemplate, template_id)
        if not template or template.agent_id != agent_id:
            return False
        
        # Desactivar todos los templates del mismo nombre
        await self._deactivate_previous_templates(agent_id, template.template_name)
        
        # Activar el template seleccionado
        template.is_active = True
        await self.session.commit()
        
        return True
    
    async def delete_template(self, template_id: int, agent_id: UUID) -> bool:
        """Elimina un template (solo si no es el activo)"""
        template = await self.session.get(PageTemplate, template_id)
        if not template or template.agent_id != agent_id or template.is_active:
            return False
        
        await self.session.delete(template)
        await self.session.commit()
        
        return True
    
    async def _get_next_version(self, agent_id: UUID, template_name: str) -> int:
        """Obtiene el próximo número de versión"""
        stmt = select(PageTemplate.version).where(
            and_(
                PageTemplate.agent_id == agent_id,
                PageTemplate.template_name == template_name
            )
        ).order_by(desc(PageTemplate.version)).limit(1)
        
        result = await self.session.execute(stmt)
        max_version = result.scalar_one_or_none()
        
        return (max_version or 0) + 1
    
    async def _deactivate_previous_templates(self, agent_id: UUID, template_name: str):
        """Desactiva templates anteriores del mismo nombre"""
        stmt = update(PageTemplate).where(
            and_(
                PageTemplate.agent_id == agent_id,
                PageTemplate.template_name == template_name,
                PageTemplate.is_active == True
            )
        ).values(is_active=False)
        
        await self.session.execute(stmt)


async def get_page_template_repository(session: AsyncSession = Depends(get_db)) -> PageTemplateRepository:
    """Dependency injection para PageTemplateRepository"""
    return PageTemplateRepository(session)