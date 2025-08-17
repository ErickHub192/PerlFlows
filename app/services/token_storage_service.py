# app/services/token_storage_service.py

from typing import Optional, Dict, Any
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text
from sqlalchemy.dialects.postgresql import insert
import logging

from app.core.token_manager import TokenStorage, TokenUsage, PlanType
from app.db.models import UserTokenUsage, UserSubscription
from app.repositories.token_repository import TokenRepository

logger = logging.getLogger(__name__)

class DatabaseTokenStorage(TokenStorage):
    """
    Optimized database storage for tokens with batching and caching
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.token_repo = TokenRepository(db)
    
    async def record_usage(self, usage: TokenUsage) -> bool:
        """
        Record token usage with optimized insert
        """
        try:
            # Use UPSERT for better performance
            pricing = self._get_pricing_for_model(usage.model_used)
            input_cost = (usage.input_tokens * pricing["input_cost"]) / 1000
            output_cost = (usage.output_tokens * pricing["output_cost"]) / 1000
            
            usage_data = {
                "user_id": usage.user_id,
                "workflow_id": usage.workflow_id,
                "execution_id": usage.execution_id,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "input_cost": input_cost,
                "output_cost": output_cost,
                "model_used": usage.model_used,
                "operation_type": usage.operation_type.value,
                "created_at": datetime.utcnow()
            }
            
            # Fast insert without returning data
            stmt = insert(UserTokenUsage).values(usage_data)
            await self.db.execute(stmt)
            
            return True
            
        except Exception as e:
            logger.error(f"Error recording usage: {e}")
            return False
    
    async def get_monthly_usage(self, user_id: int) -> int:
        """
        Get monthly usage with optimized query
        """
        try:
            # Single optimized query with date calculation in SQL
            query = text("""
                SELECT COALESCE(SUM(total_tokens), 0) as total
                FROM user_token_usage 
                WHERE user_id = :user_id 
                AND created_at >= DATE_TRUNC('month', CURRENT_DATE)
            """)
            
            result = await self.db.execute(query, {"user_id": user_id})
            return result.scalar() or 0
            
        except Exception as e:
            logger.error(f"Error getting monthly usage: {e}")
            return 0
    
    async def update_subscription(self, user_id: int, tokens_used: int) -> bool:
        """
        Update subscription with UPSERT for performance
        """
        try:
            # UPSERT subscription record
            stmt = text("""
                INSERT INTO user_subscriptions (user_id, tokens_used_current_month, monthly_token_limit, plan_type)
                VALUES (:user_id, :tokens_used, 100000, 'basic')
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    tokens_used_current_month = user_subscriptions.tokens_used_current_month + :tokens_used,
                    updated_at = CURRENT_TIMESTAMP
            """)
            
            await self.db.execute(stmt, {
                "user_id": user_id,
                "tokens_used": tokens_used
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating subscription: {e}")
            return False
    
    async def get_user_subscription_fast(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Fast subscription lookup with minimal data
        """
        try:
            query = text("""
                SELECT 
                    plan_type,
                    monthly_token_limit,
                    tokens_used_current_month,
                    CASE 
                        WHEN next_reset_date <= CURRENT_DATE THEN true 
                        ELSE false 
                    END as needs_reset
                FROM user_subscriptions 
                WHERE user_id = :user_id
            """)
            
            result = await self.db.execute(query, {"user_id": user_id})
            row = result.fetchone()
            
            if not row:
                # Create default subscription
                await self._create_default_subscription(user_id)
                return {
                    "plan_type": "basic",
                    "monthly_token_limit": 100000,
                    "tokens_used_current_month": 0,
                    "needs_reset": False
                }
            
            return {
                "plan_type": row[0],
                "monthly_token_limit": row[1], 
                "tokens_used_current_month": row[2],
                "needs_reset": row[3]
            }
            
        except Exception as e:
            logger.error(f"Error getting subscription: {e}")
            return None
    
    async def _create_default_subscription(self, user_id: int):
        """Create default subscription"""
        stmt = text("""
            INSERT INTO user_subscriptions (user_id, plan_type, monthly_token_limit) 
            VALUES (:user_id, 'basic', 100000)
            ON CONFLICT (user_id) DO NOTHING
        """)
        await self.db.execute(stmt, {"user_id": user_id})
    
    def _get_pricing_for_model(self, model: str) -> Dict[str, float]:
        """Get pricing configuration for model"""
        pricing_map = {
            "gpt-4.1": {"input_cost": 0.002, "output_cost": 0.008},
            "gpt-4o": {"input_cost": 0.005, "output_cost": 0.015},
        }
        return pricing_map.get(model, pricing_map["gpt-4.1"])
    
    async def batch_record_usage(self, usages: list[TokenUsage]) -> bool:
        """
        Batch record multiple usage records for performance
        """
        try:
            if not usages:
                return True
            
            # Prepare batch data
            batch_data = []
            user_updates = {}
            
            for usage in usages:
                pricing = self._get_pricing_for_model(usage.model_used)
                input_cost = (usage.input_tokens * pricing["input_cost"]) / 1000
                output_cost = (usage.output_tokens * pricing["output_cost"]) / 1000
                
                batch_data.append({
                    "user_id": usage.user_id,
                    "workflow_id": usage.workflow_id,
                    "execution_id": usage.execution_id,
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "input_cost": input_cost,
                    "output_cost": output_cost,
                    "model_used": usage.model_used,
                    "operation_type": usage.operation_type.value,
                    "created_at": datetime.utcnow()
                })
                
                # Aggregate user updates
                user_id = usage.user_id
                if user_id not in user_updates:
                    user_updates[user_id] = 0
                user_updates[user_id] += usage.total_tokens
            
            # Batch insert usage records
            if batch_data:
                stmt = insert(UserTokenUsage).values(batch_data)
                await self.db.execute(stmt)
            
            # Batch update subscriptions
            for user_id, total_tokens in user_updates.items():
                await self.update_subscription(user_id, total_tokens)
            
            await self.db.commit()
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error in batch record: {e}")
            return False