from abc import ABC, abstractmethod
from uuid import UUID
from typing import List, Optional

from app.db.models import MarketplaceTemplate, Flow, TemplateCategory


class IMarketplaceService(ABC):
    """Interface for marketplace service operations"""

    @abstractmethod
    async def list_templates(
        self, 
        category: Optional[TemplateCategory] = None, 
        tags: Optional[List[str]] = None
    ) -> List[MarketplaceTemplate]:
        """List templates with optional filtering"""
        pass

    @abstractmethod
    async def get_template(self, template_id: UUID) -> MarketplaceTemplate:
        """Get specific template by ID"""
        pass

    @abstractmethod
    async def search_templates(self, query: str) -> List[MarketplaceTemplate]:
        """Search templates by keywords"""
        pass

    @abstractmethod
    async def install_template(self, template_id: UUID, user_id: int) -> Flow:
        """Install template as workflow and increment usage count"""
        pass