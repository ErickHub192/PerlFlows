from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.db.database import get_db
from app.db.models import MarketplaceTemplate, Flow, TemplateCategory

class MarketplaceTemplateRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_templates(self, category: Optional[TemplateCategory] = None, tags: Optional[List[str]] = None) -> List[MarketplaceTemplate]:
        query = select(MarketplaceTemplate).where(MarketplaceTemplate.is_active == True)
        
        if category:
            query = query.where(MarketplaceTemplate.category == category)
        
        if tags:
            # Filter by tags using PostgreSQL array operators
            for tag in tags:
                query = query.where(func.array_position(MarketplaceTemplate.tags, tag) != None)
        
        # Order by usage count desc, then by created_at desc
        query = query.order_by(
            MarketplaceTemplate.usage_count.desc(),
            MarketplaceTemplate.created_at.desc()
        )
        
        res = await self.db.execute(query)
        return res.scalars().all()

    async def get_template(self, template_id: UUID) -> Optional[MarketplaceTemplate]:
        res = await self.db.execute(
            select(MarketplaceTemplate).where(
                and_(
                    MarketplaceTemplate.template_id == template_id,
                    MarketplaceTemplate.is_active == True
                )
            )
        )
        return res.scalar_one_or_none()

    async def increment_usage_count(self, template_id: UUID) -> bool:
        """Increment usage count when template is installed"""
        template = await self.get_template(template_id)
        if template:
            template.usage_count += 1
            await self.db.flush()
            return True
        return False

    async def search_templates(self, query: str) -> List[MarketplaceTemplate]:
        """Search templates by name, description, or tags"""
        search_filter = select(MarketplaceTemplate).where(
            and_(
                MarketplaceTemplate.is_active == True,
                func.or_(
                    MarketplaceTemplate.name.ilike(f"%{query}%"),
                    MarketplaceTemplate.description.ilike(f"%{query}%"),
                    func.array_to_string(MarketplaceTemplate.tags, ' ').ilike(f"%{query}%")
                )
            )
        ).order_by(MarketplaceTemplate.usage_count.desc())
        
        res = await self.db.execute(search_filter)
        return res.scalars().all()

    async def create_flow(self, name: str, owner_id: int, spec: dict) -> Flow:
        flow = Flow(name=name, owner_id=owner_id, spec=spec, is_active=False)
        self.db.add(flow)
        await self.db.flush()
        await self.db.refresh(flow)
        return flow

async def get_marketplace_template_repository(
    db: AsyncSession = Depends(get_db),
) -> MarketplaceTemplateRepository:
    return MarketplaceTemplateRepository(db)
