# app/repositories/llm_provider_repository.py
"""
Repository for LLM Provider management
Provides data access layer for the llm_providers table
"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from app.db.models import LLMProvider
from app.dtos.llm_provider_dto import LLMProviderDTO
from app.mappers.llm_provider_mapper import to_llm_provider_dto


class LLMProviderRepository:
    """Repository for LLM Provider CRUD operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_active(self) -> List[LLMProviderDTO]:
        """Get all active LLM providers"""
        stmt = select(LLMProvider).where(
            LLMProvider.is_active == True
        ).order_by(LLMProvider.name)
        
        result = await self.session.execute(stmt)
        providers = result.scalars().all()
        return [to_llm_provider_dto(provider) for provider in providers]

    async def get_by_provider_key(self, provider_key: str) -> Optional[LLMProviderDTO]:
        """Get provider by provider_key"""
        stmt = select(LLMProvider).where(
            and_(
                LLMProvider.provider_key == provider_key,
                LLMProvider.is_active == True
            )
        )
        
        result = await self.session.execute(stmt)
        provider = result.scalar_one_or_none()
        return to_llm_provider_dto(provider) if provider else None

    async def get_by_id(self, provider_id: UUID) -> Optional[LLMProviderDTO]:
        """Get provider by ID"""
        stmt = select(LLMProvider).where(
            LLMProvider.provider_id == provider_id
        )
        
        result = await self.session.execute(stmt)
        provider = result.scalar_one_or_none()
        return to_llm_provider_dto(provider) if provider else None

    async def get_by_name(self, name: str) -> Optional[LLMProvider]:
        """Get provider by name"""
        stmt = select(LLMProvider).where(
            and_(
                LLMProvider.name == name,
                LLMProvider.is_active == True
            )
        ).options(
            selectinload(LLMProvider.models)
        )
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_providers(self, search_term: str) -> List[LLMProviderDTO]:
        """Search providers by name or description"""
        stmt = select(LLMProvider).where(
            and_(
                LLMProvider.is_active == True,
                or_(
                    LLMProvider.name.ilike(f"%{search_term}%"),
                    LLMProvider.description.ilike(f"%{search_term}%"),
                    LLMProvider.provider_key.ilike(f"%{search_term}%")
                )
            )
        ).order_by(LLMProvider.name)
        
        result = await self.session.execute(stmt)
        providers = result.scalars().all()
        return [to_llm_provider_dto(provider) for provider in providers]

    async def get_providers_with_capabilities(self, capabilities: List[str]) -> List[LLMProviderDTO]:
        """Get providers that support specific capabilities"""
        # Create JSONB contains conditions for each capability
        conditions = []
        for capability in capabilities:
            conditions.append(
                LLMProvider.capabilities.op('@>')([capability])
            )
        
        stmt = select(LLMProvider).where(
            and_(
                LLMProvider.is_active == True,
                or_(*conditions)
            )
        ).order_by(LLMProvider.name)
        
        result = await self.session.execute(stmt)
        providers = result.scalars().all()
        return [to_llm_provider_dto(provider) for provider in providers]

    async def create_provider(self, provider_data: dict) -> LLMProvider:
        """Create a new LLM provider"""
        provider = LLMProvider(**provider_data)
        self.session.add(provider)
        await self.session.flush()
        await self.session.refresh(provider)
        return provider

    async def update_provider(self, provider_id: UUID, update_data: dict) -> Optional[LLMProvider]:
        """Update an existing provider"""
        provider = await self.get_by_id(provider_id)
        if not provider:
            return None
        
        for key, value in update_data.items():
            if hasattr(provider, key):
                setattr(provider, key, value)
        
        await self.session.flush()
        await self.session.refresh(provider)
        return provider

    async def deactivate_provider(self, provider_id: UUID) -> bool:
        """Deactivate a provider (soft delete)"""
        provider = await self.get_by_id(provider_id)
        if not provider:
            return False
        
        provider.is_active = False
        await self.session.flush()
        return True

    async def health_check_providers(self) -> List[LLMProviderDTO]:
        """Get providers that have health check endpoints configured"""
        stmt = select(LLMProvider).where(
            and_(
                LLMProvider.is_active == True,
                LLMProvider.health_check_endpoint.isnot(None),
                LLMProvider.health_check_endpoint != ""
            )
        ).order_by(LLMProvider.name)
        
        result = await self.session.execute(stmt)
        providers = result.scalars().all()
        return [to_llm_provider_dto(provider) for provider in providers]

    async def get_provider_statistics(self) -> dict:
        """Get basic statistics about providers"""
        from sqlalchemy import func
        
        # Count total providers
        total_stmt = select(func.count(LLMProvider.provider_id))
        total_result = await self.session.execute(total_stmt)
        total_providers = total_result.scalar()
        
        # Count active providers
        active_stmt = select(func.count(LLMProvider.provider_id)).where(
            LLMProvider.is_active == True
        )
        active_result = await self.session.execute(active_stmt)
        active_providers = active_result.scalar()
        
        return {
            "total_providers": total_providers,
            "active_providers": active_providers,
            "inactive_providers": total_providers - active_providers
        }
    
    async def get_by_provider_keys(self, provider_keys: List[str]) -> List[LLMProvider]:
        """Get providers by multiple provider keys for batch operations"""
        if not provider_keys:
            return []
        
        stmt = select(LLMProvider).where(
            LLMProvider.provider_key.in_(provider_keys)
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


# Factory function for dependency injection
def get_llm_provider_repository(session: AsyncSession) -> LLMProviderRepository:
    """Factory function to create LLMProviderRepository instance"""
    return LLMProviderRepository(session)