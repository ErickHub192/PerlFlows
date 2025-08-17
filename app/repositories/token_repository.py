# app/repositories/token_repository.py

from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, asc
from sqlalchemy.orm import selectinload
import logging

from app.db.models import UserTokenUsage, UserSubscription
from app.exceptions.api_exceptions import WorkflowProcessingException

logger = logging.getLogger(__name__)

class TokenRepository:
    """
    Repository para manejo de datos de tokens y suscripciones
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ==================== UserTokenUsage Methods ====================
    
    async def create_token_usage(self, usage_data: Dict[str, Any]) -> UserTokenUsage:
        """
        Crea un nuevo registro de uso de tokens
        """
        usage = UserTokenUsage(**usage_data)
        self.db.add(usage)
        await self.db.flush()
        return usage
    
    async def get_user_token_usage_by_period(
        self, 
        user_id: int, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[UserTokenUsage]:
        """
        Obtiene el uso de tokens de un usuario en un período específico
        """
        result = await self.db.execute(
            select(UserTokenUsage)
            .where(
                and_(
                    UserTokenUsage.user_id == user_id,
                    UserTokenUsage.created_at >= start_date,
                    UserTokenUsage.created_at <= end_date
                )
            )
            .order_by(desc(UserTokenUsage.created_at))
        )
        return result.scalars().all()
    
    async def get_total_tokens_by_user_current_month(self, user_id: int) -> int:
        """
        Obtiene el total de tokens usados por un usuario en el mes actual
        """
        current_month_start = date.today().replace(day=1)
        
        result = await self.db.execute(
            select(func.coalesce(func.sum(UserTokenUsage.total_tokens), 0))
            .where(
                and_(
                    UserTokenUsage.user_id == user_id,
                    func.date(UserTokenUsage.created_at) >= current_month_start
                )
            )
        )
        return result.scalar() or 0
    
    async def get_workflow_token_analytics(
        self, 
        workflow_id: str, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Obtiene analytics de tokens para un workflow específico
        """
        result = await self.db.execute(
            select(
                UserTokenUsage.execution_id,
                UserTokenUsage.total_tokens,
                UserTokenUsage.total_cost,
                UserTokenUsage.model_used,
                UserTokenUsage.created_at
            )
            .where(UserTokenUsage.workflow_id == workflow_id)
            .order_by(desc(UserTokenUsage.created_at))
            .limit(limit)
        )
        
        return [
            {
                "execution_id": str(row.execution_id),
                "total_tokens": row.total_tokens,
                "total_cost": float(row.total_cost),
                "model_used": row.model_used,
                "created_at": row.created_at.isoformat()
            }
            for row in result.fetchall()
        ]
    
    async def get_daily_token_usage_summary(
        self, 
        user_id: int, 
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Obtiene resumen diario de uso de tokens
        """
        start_date = datetime.now() - timedelta(days=days)
        
        result = await self.db.execute(
            select(
                func.date(UserTokenUsage.created_at).label('usage_date'),
                func.sum(UserTokenUsage.input_tokens).label('input_tokens'),
                func.sum(UserTokenUsage.output_tokens).label('output_tokens'),
                func.sum(UserTokenUsage.total_tokens).label('total_tokens'),
                func.sum(UserTokenUsage.total_cost).label('total_cost'),
                func.count().label('executions')
            )
            .where(
                and_(
                    UserTokenUsage.user_id == user_id,
                    UserTokenUsage.created_at >= start_date
                )
            )
            .group_by(func.date(UserTokenUsage.created_at))
            .order_by(asc('usage_date'))
        )
        
        return [
            {
                "date": row.usage_date.isoformat(),
                "input_tokens": int(row.input_tokens or 0),
                "output_tokens": int(row.output_tokens or 0),
                "total_tokens": int(row.total_tokens or 0),
                "total_cost": float(row.total_cost or 0),
                "executions": int(row.executions or 0)
            }
            for row in result.fetchall()
        ]
    
    # ==================== UserSubscription Methods ====================
    
    async def get_user_subscription(self, user_id: int) -> Optional[UserSubscription]:
        """
        Obtiene la suscripción de un usuario
        """
        result = await self.db.execute(
            select(UserSubscription)
            .options(selectinload(UserSubscription.user))
            .where(UserSubscription.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def create_user_subscription(self, subscription_data: Dict[str, Any]) -> UserSubscription:
        """
        Crea una nueva suscripción de usuario
        """
        subscription = UserSubscription(**subscription_data)
        self.db.add(subscription)
        await self.db.flush()
        return subscription
    
    async def update_user_subscription(
        self, 
        user_id: int, 
        update_data: Dict[str, Any]
    ) -> Optional[UserSubscription]:
        """
        Actualiza una suscripción de usuario
        """
        subscription = await self.get_user_subscription(user_id)
        if not subscription:
            return None
        
        for key, value in update_data.items():
            if hasattr(subscription, key):
                setattr(subscription, key, value)
        
        await self.db.flush()
        return subscription
    
    async def increment_monthly_usage(self, user_id: int, tokens: int) -> UserSubscription:
        """
        Incrementa el uso mensual de tokens de un usuario
        """
        subscription = await self.get_user_subscription(user_id)
        if not subscription:
            raise WorkflowProcessingException(f"No subscription found for user {user_id}")
        
        subscription.tokens_used_current_month += tokens
        await self.db.flush()
        return subscription
    
    async def reset_monthly_usage(self, user_id: int) -> UserSubscription:
        """
        Resetea el uso mensual de tokens de un usuario
        """
        subscription = await self.get_user_subscription(user_id)
        if not subscription:
            raise WorkflowProcessingException(f"No subscription found for user {user_id}")
        
        subscription.tokens_used_current_month = 0
        subscription.billing_cycle_start = date.today()
        subscription.next_reset_date = date.today() + timedelta(days=30)
        subscription.alert_80_sent = False
        subscription.alert_90_sent = False
        subscription.limit_reached = False
        
        await self.db.flush()
        return subscription
    
    async def get_users_near_limit(self, threshold_percentage: float = 80.0) -> List[UserSubscription]:
        """
        Obtiene usuarios que están cerca del límite de tokens
        """
        result = await self.db.execute(
            select(UserSubscription)
            .where(
                (UserSubscription.tokens_used_current_month * 100.0 / UserSubscription.monthly_token_limit) >= threshold_percentage
            )
            .options(selectinload(UserSubscription.user))
        )
        return result.scalars().all()
    
    async def get_subscription_analytics(self) -> Dict[str, Any]:
        """
        Obtiene analytics generales de suscripciones
        """
        # Total de usuarios por plan
        plan_distribution = await self.db.execute(
            select(
                UserSubscription.plan_type,
                func.count().label('user_count')
            )
            .group_by(UserSubscription.plan_type)
        )
        
        # Usuarios cerca del límite
        near_limit = await self.db.execute(
            select(func.count())
            .where(
                (UserSubscription.tokens_used_current_month * 100.0 / UserSubscription.monthly_token_limit) >= 80.0
            )
        )
        
        # Total de tokens consumidos este mes
        total_tokens_month = await self.db.execute(
            select(func.sum(UserSubscription.tokens_used_current_month))
        )
        
        return {
            "plan_distribution": [
                {"plan": row.plan_type, "users": row.user_count}
                for row in plan_distribution.fetchall()
            ],
            "users_near_limit": near_limit.scalar() or 0,
            "total_tokens_consumed_month": int(total_tokens_month.scalar() or 0)
        }