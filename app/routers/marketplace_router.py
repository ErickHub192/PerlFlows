from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, Query

from app.dtos.flow_dtos import FlowSummaryDTO
from app.dtos.marketplace_template_dto import MarketplaceTemplateDTO
from app.services.IMarketplaceService import IMarketplaceService
from app.services.marketplace_service import get_marketplace_service
from app.core.auth import get_current_user_id
from app.db.models import TemplateCategory

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])


@router.get("/templates", response_model=List[MarketplaceTemplateDTO])
async def list_templates(
    category: Optional[TemplateCategory] = Query(None, description="Filter by template category"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    search: Optional[str] = Query(None, description="Search templates by name, description, or tags"),
    service: IMarketplaceService = Depends(get_marketplace_service)
):
    """
    List marketplace templates with optional filtering and search.
    
    - **category**: Filter by specific category (business_sales, mexico_latam, etc.)
    - **tags**: Filter by tags (comma-separated, e.g., "sat,mexico")
    - **search**: Search by keywords in name, description, or tags
    """
    if search:
        return await service.search_templates(search)
    
    tag_list = tags.split(",") if tags else None
    return await service.list_templates(category=category, tags=tag_list)


@router.get("/templates/{template_id}", response_model=MarketplaceTemplateDTO)
async def get_template(
    template_id: UUID,
    service: IMarketplaceService = Depends(get_marketplace_service)
):
    """Get specific template details by ID"""
    return await service.get_template(template_id)


@router.get("/categories")
async def list_categories():
    """List all available template categories"""
    return [{"value": cat.value, "label": cat.value.replace("_", " ").title()} 
            for cat in TemplateCategory]


@router.post("/install", response_model=FlowSummaryDTO)
async def install_template(
    template_id: UUID,
    user_id: int = Depends(get_current_user_id),
    service: IMarketplaceService = Depends(get_marketplace_service),
):
    """Install a marketplace template as a new workflow"""
    flow = await service.install_template(template_id, user_id)
    return FlowSummaryDTO.from_orm(flow)
