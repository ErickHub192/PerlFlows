import logging
from uuid import UUID
from typing import List, Optional
from fastapi import Depends, HTTPException, status

from app.repositories.marketplace_template_repository import (
    MarketplaceTemplateRepository,
    get_marketplace_template_repository,
)
# Interface removed - using concrete class
from app.services.flow_validator_service import FlowValidatorService
from app.services.flow_validator_service import get_flow_validator_service
from app.db.models import MarketplaceTemplate, Flow, TemplateCategory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class MarketplaceService:
    def __init__(self, repo: MarketplaceTemplateRepository, validator: FlowValidatorService):
        self.repo = repo
        self.validator = validator

    async def list_templates(self, category: Optional[TemplateCategory] = None, tags: Optional[List[str]] = None) -> List[MarketplaceTemplate]:
        """List templates with optional filtering"""
        return await self.repo.list_templates(category=category, tags=tags)

    async def get_template(self, template_id: UUID) -> MarketplaceTemplate:
        """Get specific template by ID"""
        template = await self.repo.get_template(template_id)
        if not template:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
        return template

    async def search_templates(self, query: str) -> List[MarketplaceTemplate]:
        """Search templates by keywords"""
        if not query or len(query.strip()) < 2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Search query must be at least 2 characters")
        return await self.repo.search_templates(query.strip())

    async def install_template(self, template_id: UUID, user_id: int) -> Flow:
        """Install template as workflow and increment usage count"""
        template = await self.repo.get_template(template_id)
        if not template:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
        
        try:
            # Validate template spec
            await self.validator.validate_flow_spec(template.spec_json)
        except Exception as e:
            logger.error(f"Template {template_id} validation failed: {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid template specification: {str(e)}")
        
        # Create flow from template
        flow_name = f"{template.name} - {template.template_id}"
        flow = await self.repo.create_flow(flow_name, user_id, template.spec_json)
        
        # Increment usage count
        await self.repo.increment_usage_count(template_id)
        
        logger.info(f"Template {template_id} ({template.name}) installed by user {user_id} as flow {flow.flow_id}")
        return flow

async def get_marketplace_service(
    repo: MarketplaceTemplateRepository = Depends(get_marketplace_template_repository),
    validator: FlowValidatorService = Depends(get_flow_validator_service),
) -> MarketplaceService:
    return MarketplaceService(repo, validator)
