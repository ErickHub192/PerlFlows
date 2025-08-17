# app/repositories/llm_model_repository.py
"""
Repository for LLM Model management
Provides data access layer for the llm_models table
"""
from typing import List, Optional
from uuid import UUID
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.orm import selectinload

from app.db.models import LLMModel, LLMProvider


class LLMModelRepository:
    """Repository for LLM Model CRUD operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_active(self) -> List[LLMModel]:
        """Get all active models"""
        stmt = select(LLMModel).where(
            LLMModel.is_active == True
        ).options(
            selectinload(LLMModel.provider)
        ).order_by(LLMModel.display_name)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_provider(self, provider_id: UUID, active_only: bool = True) -> List[LLMModel]:
        """Get models by provider ID"""
        conditions = [LLMModel.provider_id == provider_id]
        if active_only:
            conditions.append(LLMModel.is_active == True)
        
        stmt = select(LLMModel).where(
            and_(*conditions)
        ).options(
            selectinload(LLMModel.provider)
        ).order_by(
            desc(LLMModel.is_recommended),
            desc(LLMModel.is_default),
            LLMModel.display_name
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_provider_key(self, provider_key: str, active_only: bool = True) -> List[LLMModel]:
        """Get models by provider key"""
        conditions = [
            LLMProvider.provider_key == provider_key,
            LLMModel.provider_id == LLMProvider.provider_id
        ]
        if active_only:
            conditions.extend([
                LLMModel.is_active == True,
                LLMProvider.is_active == True
            ])
        
        stmt = select(LLMModel).join(LLMProvider).where(
            and_(*conditions)
        ).options(
            selectinload(LLMModel.provider)
        ).order_by(
            desc(LLMModel.is_recommended),
            desc(LLMModel.is_default),
            LLMModel.display_name
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_model_key(self, provider_key: str, model_key: str) -> Optional[LLMModel]:
        """Get specific model by provider_key and model_key"""
        stmt = select(LLMModel).join(LLMProvider).where(
            and_(
                LLMProvider.provider_key == provider_key,
                LLMModel.model_key == model_key,
                LLMModel.is_active == True,
                LLMProvider.is_active == True
            )
        ).options(
            selectinload(LLMModel.provider)
        )
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, model_id: UUID) -> Optional[LLMModel]:
        """Get model by ID"""
        stmt = select(LLMModel).where(
            LLMModel.model_id == model_id
        ).options(
            selectinload(LLMModel.provider)
        )
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_model_key(self, model_key: str) -> Optional[LLMModel]:
        """Get model by model key (without provider constraint)"""
        stmt = select(LLMModel).where(
            and_(
                LLMModel.model_key == model_key,
                LLMModel.is_active == True
            )
        ).options(
            selectinload(LLMModel.provider)
        )
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_provider_by_model_id(self, model_id: UUID) -> Optional[LLMProvider]:
        """Get provider information for a model ID"""
        stmt = select(LLMProvider).join(LLMModel).where(
            LLMModel.model_id == model_id
        )
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_recommended_models(self, provider_key: str = None) -> List[LLMModel]:
        """Get recommended models, optionally filtered by provider"""
        conditions = [
            LLMModel.is_recommended == True,
            LLMModel.is_active == True,
            LLMProvider.is_active == True
        ]
        
        if provider_key:
            conditions.append(LLMProvider.provider_key == provider_key)
        
        stmt = select(LLMModel).join(LLMProvider).where(
            and_(*conditions)
        ).options(
            selectinload(LLMModel.provider)
        ).order_by(
            LLMProvider.name,
            desc(LLMModel.is_default),
            LLMModel.display_name
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_default_model(self, provider_key: str) -> Optional[LLMModel]:
        """Get the default model for a provider"""
        stmt = select(LLMModel).join(LLMProvider).where(
            and_(
                LLMProvider.provider_key == provider_key,
                LLMModel.is_default == True,
                LLMModel.is_active == True,
                LLMProvider.is_active == True
            )
        ).options(
            selectinload(LLMModel.provider)
        )
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_models(self, search_term: str) -> List[LLMModel]:
        """Search models by name, description, or model family"""
        stmt = select(LLMModel).join(LLMProvider).where(
            and_(
                LLMModel.is_active == True,
                LLMProvider.is_active == True,
                or_(
                    LLMModel.display_name.ilike(f"%{search_term}%"),
                    LLMModel.description.ilike(f"%{search_term}%"),
                    LLMModel.model_key.ilike(f"%{search_term}%"),
                    LLMModel.model_family.ilike(f"%{search_term}%")
                )
            )
        ).options(
            selectinload(LLMModel.provider)
        ).order_by(
            desc(LLMModel.is_recommended),
            LLMModel.display_name
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_models_with_capabilities(self, capabilities: List[str]) -> List[LLMModel]:
        """Get models that support specific capabilities"""
        conditions = []
        for capability in capabilities:
            conditions.append(
                LLMModel.capabilities.op('@>')([capability])
            )
        
        stmt = select(LLMModel).join(LLMProvider).where(
            and_(
                LLMModel.is_active == True,
                LLMProvider.is_active == True,
                or_(*conditions)
            )
        ).options(
            selectinload(LLMModel.provider)
        ).order_by(
            desc(LLMModel.is_recommended),
            LLMModel.display_name
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_models_by_context_length(self, min_context_length: int) -> List[LLMModel]:
        """Get models with context length >= min_context_length"""
        stmt = select(LLMModel).join(LLMProvider).where(
            and_(
                LLMModel.is_active == True,
                LLMProvider.is_active == True,
                LLMModel.context_length >= min_context_length
            )
        ).options(
            selectinload(LLMModel.provider)
        ).order_by(
            LLMModel.context_length,
            desc(LLMModel.is_recommended)
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_models_by_cost_range(self, max_input_cost: float = None, max_output_cost: float = None) -> List[LLMModel]:
        """Get models within cost range"""
        conditions = [
            LLMModel.is_active == True,
            LLMProvider.is_active == True
        ]
        
        if max_input_cost is not None:
            conditions.append(LLMModel.input_cost_per_1k <= max_input_cost)
        if max_output_cost is not None:
            conditions.append(LLMModel.output_cost_per_1k <= max_output_cost)
        
        stmt = select(LLMModel).join(LLMProvider).where(
            and_(*conditions)
        ).options(
            selectinload(LLMModel.provider)
        ).order_by(
            LLMModel.input_cost_per_1k,
            LLMModel.output_cost_per_1k
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_model(self, model_data: dict) -> LLMModel:
        """Create a new LLM model"""
        model = LLMModel(**model_data)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def update_model(self, model_id: UUID, update_data: dict) -> Optional[LLMModel]:
        """Update an existing model"""
        model = await self.get_by_id(model_id)
        if not model:
            return None
        
        for key, value in update_data.items():
            if hasattr(model, key):
                setattr(model, key, value)
        
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def deactivate_model(self, model_id: UUID) -> bool:
        """Deactivate a model (soft delete)"""
        model = await self.get_by_id(model_id)
        if not model:
            return False
        
        model.is_active = False
        await self.session.flush()
        return True

    async def get_deprecated_models(self, as_of_date: date = None) -> List[LLMModel]:
        """Get models that are deprecated"""
        if as_of_date is None:
            as_of_date = date.today()
        
        stmt = select(LLMModel).join(LLMProvider).where(
            and_(
                LLMModel.deprecation_date <= as_of_date,
                LLMModel.deprecation_date.isnot(None),
                LLMProvider.is_active == True
            )
        ).options(
            selectinload(LLMModel.provider)
        ).order_by(LLMModel.deprecation_date)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_model_statistics(self) -> dict:
        """Get basic statistics about models"""
        from sqlalchemy import func
        
        # Count total models
        total_stmt = select(func.count(LLMModel.model_id))
        total_result = await self.session.execute(total_stmt)
        total_models = total_result.scalar()
        
        # Count active models
        active_stmt = select(func.count(LLMModel.model_id)).where(
            LLMModel.is_active == True
        )
        active_result = await self.session.execute(active_stmt)
        active_models = active_result.scalar()
        
        # Count recommended models
        recommended_stmt = select(func.count(LLMModel.model_id)).where(
            and_(
                LLMModel.is_active == True,
                LLMModel.is_recommended == True
            )
        )
        recommended_result = await self.session.execute(recommended_stmt)
        recommended_models = recommended_result.scalar()
        
        return {
            "total_models": total_models,
            "active_models": active_models,
            "inactive_models": total_models - active_models,
            "recommended_models": recommended_models
        }
    
    async def get_by_model_keys(self, model_keys: List[str]) -> List[LLMModel]:
        """Get models by multiple model keys for batch operations"""
        if not model_keys:
            return []
        
        stmt = select(LLMModel).where(
            LLMModel.model_key.in_(model_keys)
        ).options(
            selectinload(LLMModel.provider)
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


# Factory function for dependency injection
def get_llm_model_repository(session: AsyncSession) -> LLMModelRepository:
    """Factory function to create LLMModelRepository instance"""
    return LLMModelRepository(session)