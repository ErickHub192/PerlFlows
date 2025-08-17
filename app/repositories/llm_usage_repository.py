# app/repositories/llm_usage_repository.py
"""
Repository for LLM Usage Analytics
Provides data access layer for the llm_usage_logs table
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc, asc
from sqlalchemy.orm import selectinload

from app.db.models import LLMUsageLog, LLMProvider, LLMModel, User


class LLMUsageRepository:
    """Repository for LLM Usage logging and analytics"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_usage(self, usage_data: dict) -> LLMUsageLog:
        """Log a new LLM usage event"""
        usage_log = LLMUsageLog(**usage_data)
        self.session.add(usage_log)
        await self.session.flush()
        await self.session.refresh(usage_log)
        return usage_log

    async def get_usage_by_user(
        self, 
        user_id: int, 
        start_date: datetime = None, 
        end_date: datetime = None,
        limit: int = 100
    ) -> List[LLMUsageLog]:
        """Get usage logs for a specific user"""
        conditions = [LLMUsageLog.user_id == user_id]
        
        if start_date:
            conditions.append(LLMUsageLog.created_at >= start_date)
        if end_date:
            conditions.append(LLMUsageLog.created_at <= end_date)
        
        stmt = select(LLMUsageLog).where(
            and_(*conditions)
        ).options(
            selectinload(LLMUsageLog.provider),
            selectinload(LLMUsageLog.model)
        ).order_by(
            desc(LLMUsageLog.created_at)
        ).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_usage_summary(
        self, 
        user_id: int, 
        start_date: datetime = None, 
        end_date: datetime = None
    ) -> Dict[str, Any]:
        """Get usage summary for a user"""
        conditions = [LLMUsageLog.user_id == user_id]
        
        if start_date:
            conditions.append(LLMUsageLog.created_at >= start_date)
        if end_date:
            conditions.append(LLMUsageLog.created_at <= end_date)
        
        # Aggregate query
        stmt = select(
            func.count(LLMUsageLog.usage_id).label('total_requests'),
            func.sum(LLMUsageLog.input_tokens).label('total_input_tokens'),
            func.sum(LLMUsageLog.output_tokens).label('total_output_tokens'),
            func.sum(LLMUsageLog.total_cost).label('total_cost'),
            func.avg(LLMUsageLog.response_time_ms).label('avg_response_time'),
            func.count().filter(LLMUsageLog.status == 'success').label('successful_requests'),
            func.count().filter(LLMUsageLog.status == 'error').label('failed_requests')
        ).where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        row = result.first()
        
        return {
            'total_requests': row.total_requests or 0,
            'total_input_tokens': row.total_input_tokens or 0,
            'total_output_tokens': row.total_output_tokens or 0,
            'total_tokens': (row.total_input_tokens or 0) + (row.total_output_tokens or 0),
            'total_cost': float(row.total_cost or 0),
            'avg_response_time_ms': float(row.avg_response_time or 0),
            'successful_requests': row.successful_requests or 0,
            'failed_requests': row.failed_requests or 0,
            'success_rate': (row.successful_requests or 0) / max(row.total_requests or 1, 1) * 100
        }

    async def get_provider_usage_stats(
        self, 
        start_date: datetime = None, 
        end_date: datetime = None
    ) -> List[Dict[str, Any]]:
        """Get usage statistics by provider"""
        conditions = []
        
        if start_date:
            conditions.append(LLMUsageLog.created_at >= start_date)
        if end_date:
            conditions.append(LLMUsageLog.created_at <= end_date)
        
        stmt = select(
            LLMProvider.name.label('provider_name'),
            LLMProvider.provider_key.label('provider_key'),
            func.count(LLMUsageLog.usage_id).label('total_requests'),
            func.sum(LLMUsageLog.input_tokens).label('total_input_tokens'),
            func.sum(LLMUsageLog.output_tokens).label('total_output_tokens'),
            func.sum(LLMUsageLog.total_cost).label('total_cost'),
            func.avg(LLMUsageLog.response_time_ms).label('avg_response_time'),
            func.count().filter(LLMUsageLog.status == 'success').label('successful_requests')
        ).select_from(
            LLMUsageLog
        ).join(
            LLMProvider, LLMUsageLog.provider_id == LLMProvider.provider_id
        ).where(
            and_(*conditions) if conditions else True
        ).group_by(
            LLMProvider.provider_id, LLMProvider.name, LLMProvider.provider_key
        ).order_by(
            desc('total_requests')
        )
        
        result = await self.session.execute(stmt)
        
        stats = []
        for row in result:
            stats.append({
                'provider_name': row.provider_name,
                'provider_key': row.provider_key,
                'total_requests': row.total_requests,
                'total_input_tokens': row.total_input_tokens or 0,
                'total_output_tokens': row.total_output_tokens or 0,
                'total_tokens': (row.total_input_tokens or 0) + (row.total_output_tokens or 0),
                'total_cost': float(row.total_cost or 0),
                'avg_response_time_ms': float(row.avg_response_time or 0),
                'successful_requests': row.successful_requests,
                'success_rate': row.successful_requests / max(row.total_requests, 1) * 100
            })
        
        return stats

    async def get_model_usage_stats(
        self, 
        provider_key: str = None,
        start_date: datetime = None, 
        end_date: datetime = None
    ) -> List[Dict[str, Any]]:
        """Get usage statistics by model"""
        conditions = []
        
        if provider_key:
            conditions.append(LLMProvider.provider_key == provider_key)
        if start_date:
            conditions.append(LLMUsageLog.created_at >= start_date)
        if end_date:
            conditions.append(LLMUsageLog.created_at <= end_date)
        
        stmt = select(
            LLMProvider.name.label('provider_name'),
            LLMModel.display_name.label('model_name'),
            LLMModel.model_key.label('model_key'),
            func.count(LLMUsageLog.usage_id).label('total_requests'),
            func.sum(LLMUsageLog.input_tokens).label('total_input_tokens'),
            func.sum(LLMUsageLog.output_tokens).label('total_output_tokens'),
            func.sum(LLMUsageLog.total_cost).label('total_cost'),
            func.avg(LLMUsageLog.response_time_ms).label('avg_response_time'),
            func.count().filter(LLMUsageLog.status == 'success').label('successful_requests')
        ).select_from(
            LLMUsageLog
        ).join(
            LLMModel, LLMUsageLog.model_id == LLMModel.model_id
        ).join(
            LLMProvider, LLMModel.provider_id == LLMProvider.provider_id
        ).where(
            and_(*conditions) if conditions else True
        ).group_by(
            LLMProvider.name, LLMModel.model_id, LLMModel.display_name, LLMModel.model_key
        ).order_by(
            desc('total_requests')
        )
        
        result = await self.session.execute(stmt)
        
        stats = []
        for row in result:
            stats.append({
                'provider_name': row.provider_name,
                'model_name': row.model_name,
                'model_key': row.model_key,
                'total_requests': row.total_requests,
                'total_input_tokens': row.total_input_tokens or 0,
                'total_output_tokens': row.total_output_tokens or 0,
                'total_tokens': (row.total_input_tokens or 0) + (row.total_output_tokens or 0),
                'total_cost': float(row.total_cost or 0),
                'avg_response_time_ms': float(row.avg_response_time or 0),
                'successful_requests': row.successful_requests,
                'success_rate': row.successful_requests / max(row.total_requests, 1) * 100
            })
        
        return stats

    async def get_daily_usage_trend(
        self, 
        user_id: int = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get daily usage trends"""
        start_date = datetime.now() - timedelta(days=days)
        conditions = [LLMUsageLog.created_at >= start_date]
        
        if user_id:
            conditions.append(LLMUsageLog.user_id == user_id)
        
        stmt = select(
            func.date(LLMUsageLog.created_at).label('usage_date'),
            func.count(LLMUsageLog.usage_id).label('total_requests'),
            func.sum(LLMUsageLog.input_tokens).label('total_input_tokens'),
            func.sum(LLMUsageLog.output_tokens).label('total_output_tokens'),
            func.sum(LLMUsageLog.total_cost).label('total_cost'),
            func.count().filter(LLMUsageLog.status == 'success').label('successful_requests')
        ).where(
            and_(*conditions)
        ).group_by(
            func.date(LLMUsageLog.created_at)
        ).order_by(
            asc('usage_date')
        )
        
        result = await self.session.execute(stmt)
        
        trends = []
        for row in result:
            trends.append({
                'date': row.usage_date.isoformat(),
                'total_requests': row.total_requests,
                'total_input_tokens': row.total_input_tokens or 0,
                'total_output_tokens': row.total_output_tokens or 0,
                'total_tokens': (row.total_input_tokens or 0) + (row.total_output_tokens or 0),
                'total_cost': float(row.total_cost or 0),
                'successful_requests': row.successful_requests,
                'success_rate': row.successful_requests / max(row.total_requests, 1) * 100
            })
        
        return trends

    async def get_error_analysis(
        self, 
        start_date: datetime = None, 
        end_date: datetime = None
    ) -> List[Dict[str, Any]]:
        """Get error analysis"""
        conditions = [LLMUsageLog.status == 'error']
        
        if start_date:
            conditions.append(LLMUsageLog.created_at >= start_date)
        if end_date:
            conditions.append(LLMUsageLog.created_at <= end_date)
        
        stmt = select(
            LLMProvider.name.label('provider_name'),
            LLMModel.display_name.label('model_name'),
            LLMUsageLog.error_message,
            func.count(LLMUsageLog.usage_id).label('error_count')
        ).select_from(
            LLMUsageLog
        ).join(
            LLMModel, LLMUsageLog.model_id == LLMModel.model_id, isouter=True
        ).join(
            LLMProvider, LLMUsageLog.provider_id == LLMProvider.provider_id, isouter=True
        ).where(
            and_(*conditions)
        ).group_by(
            LLMProvider.name, LLMModel.display_name, LLMUsageLog.error_message
        ).order_by(
            desc('error_count')
        )
        
        result = await self.session.execute(stmt)
        
        errors = []
        for row in result:
            errors.append({
                'provider_name': row.provider_name,
                'model_name': row.model_name,
                'error_message': row.error_message,
                'error_count': row.error_count
            })
        
        return errors

    async def get_cost_breakdown(
        self, 
        user_id: int = None,
        start_date: datetime = None, 
        end_date: datetime = None
    ) -> Dict[str, Any]:
        """Get detailed cost breakdown"""
        conditions = []
        
        if user_id:
            conditions.append(LLMUsageLog.user_id == user_id)
        if start_date:
            conditions.append(LLMUsageLog.created_at >= start_date)
        if end_date:
            conditions.append(LLMUsageLog.created_at <= end_date)
        
        # Total cost
        total_stmt = select(
            func.sum(LLMUsageLog.total_cost).label('total_cost')
        ).where(and_(*conditions) if conditions else True)
        
        total_result = await self.session.execute(total_stmt)
        total_cost = float(total_result.scalar() or 0)
        
        # Cost by provider
        provider_stmt = select(
            LLMProvider.name.label('provider_name'),
            func.sum(LLMUsageLog.total_cost).label('provider_cost')
        ).select_from(
            LLMUsageLog
        ).join(
            LLMProvider, LLMUsageLog.provider_id == LLMProvider.provider_id
        ).where(
            and_(*conditions) if conditions else True
        ).group_by(
            LLMProvider.name
        ).order_by(
            desc('provider_cost')
        )
        
        provider_result = await self.session.execute(provider_stmt)
        provider_costs = [
            {
                'provider_name': row.provider_name,
                'cost': float(row.provider_cost or 0),
                'percentage': (float(row.provider_cost or 0) / total_cost * 100) if total_cost > 0 else 0
            }
            for row in provider_result
        ]
        
        return {
            'total_cost': total_cost,
            'provider_breakdown': provider_costs
        }

    async def cleanup_old_logs(self, days_to_keep: int = 90) -> int:
        """Clean up old usage logs"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Count logs to be deleted
        count_stmt = select(func.count(LLMUsageLog.usage_id)).where(
            LLMUsageLog.created_at < cutoff_date
        )
        count_result = await self.session.execute(count_stmt)
        logs_to_delete = count_result.scalar()
        
        # Delete old logs
        from sqlalchemy import delete
        delete_stmt = delete(LLMUsageLog).where(
            LLMUsageLog.created_at < cutoff_date
        )
        await self.session.execute(delete_stmt)
        
        return logs_to_delete


# Factory function for dependency injection
def get_llm_usage_repository(session: AsyncSession) -> LLMUsageRepository:
    """Factory function to create LLMUsageRepository instance"""
    return LLMUsageRepository(session)