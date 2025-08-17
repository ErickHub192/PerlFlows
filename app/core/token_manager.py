# app/core/token_manager.py

from typing import Dict, Any, Optional, Protocol, runtime_checkable
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)

class PlanType(str, Enum):
    BASIC = "basic"
    PRO = "pro" 
    ENTERPRISE = "enterprise"

class OperationType(str, Enum):
    WORKFLOW = "workflow"
    CHAT = "chat"
    AI_AGENT = "ai_agent"
    API_CALL = "api_call"

@dataclass(frozen=True)
class TokenPricing:
    """Inmutable pricing configuration"""
    input_cost_per_1k: Decimal
    output_cost_per_1k: Decimal
    model_name: str
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> Decimal:
        """Calculate total cost for token usage"""
        input_cost = Decimal(input_tokens) * self.input_cost_per_1k / 1000
        output_cost = Decimal(output_tokens) * self.output_cost_per_1k / 1000
        return input_cost + output_cost

@dataclass(frozen=True)
class PlanConfig:
    """Inmutable plan configuration"""
    monthly_token_limit: int
    daily_reset_tokens: int
    price_mxn: int
    features: frozenset[str]

@dataclass
class TokenUsage:
    """Token usage data container"""
    input_tokens: int
    output_tokens: int
    model_used: str
    operation_type: OperationType
    user_id: int
    workflow_id: Optional[str] = None
    execution_id: Optional[str] = None
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

@dataclass
class UsageStatus:
    """User usage status container"""
    can_use: bool
    remaining_tokens: int
    usage_percentage: float
    plan_type: PlanType
    is_over_limit: bool
    next_reset: Optional[str] = None
    reason: Optional[str] = None

@runtime_checkable
class TokenStorage(Protocol):
    """Protocol for token storage backends"""
    
    async def record_usage(self, usage: TokenUsage) -> bool:
        """Record token usage"""
        ...
    
    async def get_monthly_usage(self, user_id: int) -> int:
        """Get monthly token usage for user"""
        ...
    
    async def update_subscription(self, user_id: int, tokens_used: int) -> bool:
        """Update user subscription usage"""
        ...

@runtime_checkable 
class AlertSystem(Protocol):
    """Protocol for alert systems"""
    
    async def send_usage_alert(self, user_id: int, percentage: int) -> bool:
        """Send usage percentage alert"""
        ...
    
    async def send_limit_alert(self, user_id: int) -> bool:
        """Send limit reached alert"""
        ...

class TokenManager:
    """
    Core token management - optimized and modular
    """
    
    # Immutable configurations
    PRICING = {
        "gpt-4.1": TokenPricing(
            input_cost_per_1k=Decimal('0.002'),
            output_cost_per_1k=Decimal('0.008'),
            model_name="gpt-4.1"
        ),
        "gpt-4o": TokenPricing(
            input_cost_per_1k=Decimal('0.005'),
            output_cost_per_1k=Decimal('0.015'),
            model_name="gpt-4o"
        )
    }
    
    PLANS = {
        PlanType.BASIC: PlanConfig(
            monthly_token_limit=100_000,
            daily_reset_tokens=3_333,  # 100k / 30 days
            price_mxn=400,
            features=frozenset(["basic_workflows", "email_support"])
        ),
        PlanType.PRO: PlanConfig(
            monthly_token_limit=300_000,
            daily_reset_tokens=10_000,  # 300k / 30 days
            price_mxn=800,
            features=frozenset(["advanced_workflows", "priority_support", "analytics"])
        ),
        PlanType.ENTERPRISE: PlanConfig(
            monthly_token_limit=1_000_000,
            daily_reset_tokens=33_333,  # 1M / 30 days
            price_mxn=2000,
            features=frozenset(["unlimited_workflows", "dedicated_support", "custom_integrations"])
        )
    }
    
    def __init__(
        self, 
        storage: TokenStorage,
        alert_system: Optional[AlertSystem] = None,
        batch_size: int = 10
    ):
        self.storage = storage
        self.alert_system = alert_system
        self.batch_size = batch_size
        self._usage_cache: Dict[int, int] = {}  # Simple in-memory cache
        self._batch_queue: list[TokenUsage] = []
        self._processing_batch = False
    
    async def can_use_tokens(self, user_id: int, estimated_tokens: int) -> UsageStatus:
        """
        Fast check if user can use estimated tokens
        """
        try:
            # Get cached or fresh usage
            current_usage = await self._get_cached_usage(user_id)
            plan_config = self.PLANS[PlanType.BASIC]  # TODO: Get user's actual plan
            
            remaining = plan_config.monthly_token_limit - current_usage
            usage_percentage = (current_usage / plan_config.monthly_token_limit) * 100
            
            can_use = remaining >= estimated_tokens
            
            return UsageStatus(
                can_use=can_use,
                remaining_tokens=remaining,
                usage_percentage=usage_percentage,
                plan_type=PlanType.BASIC,
                is_over_limit=current_usage >= plan_config.monthly_token_limit,
                reason=None if can_use else f"Insufficient tokens. Need {estimated_tokens}, have {remaining}"
            )
            
        except Exception as e:
            logger.error(f"Error checking token usage for user {user_id}: {e}")
            # Fail open - allow usage but log error
            return UsageStatus(
                can_use=True,
                remaining_tokens=0,
                usage_percentage=0,
                plan_type=PlanType.BASIC,
                is_over_limit=False,
                reason="Error checking limits - allowing usage"
            )
    
    async def record_usage(self, usage: TokenUsage) -> bool:
        """
        Record token usage with batching for performance
        """
        try:
            # Add to batch queue
            self._batch_queue.append(usage)
            
            # Update cache immediately for fast checks
            current = self._usage_cache.get(usage.user_id, 0)
            self._usage_cache[usage.user_id] = current + usage.total_tokens
            
            # Process batch if full
            if len(self._batch_queue) >= self.batch_size:
                asyncio.create_task(self._process_batch())
            
            # Send alerts asynchronously
            if self.alert_system:
                asyncio.create_task(self._check_alerts(usage.user_id))
            
            return True
            
        except Exception as e:
            logger.error(f"Error recording token usage: {e}")
            return False
    
    async def _get_cached_usage(self, user_id: int) -> int:
        """
        Get usage from cache or storage
        """
        if user_id not in self._usage_cache:
            # Cache miss - load from storage
            usage = await self.storage.get_monthly_usage(user_id)
            self._usage_cache[user_id] = usage
        
        return self._usage_cache[user_id]
    
    async def _process_batch(self):
        """
        Process batch of token usage records
        """
        if self._processing_batch or not self._batch_queue:
            return
        
        self._processing_batch = True
        current_batch = self._batch_queue.copy()
        self._batch_queue.clear()
        
        try:
            # Process all records in batch
            tasks = []
            for usage in current_batch:
                tasks.append(self.storage.record_usage(usage))
                tasks.append(self.storage.update_subscription(usage.user_id, usage.total_tokens))
            
            # Execute all storage operations concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log any errors
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Batch processing error {i}: {result}")
                    
        except Exception as e:
            logger.error(f"Critical error in batch processing: {e}")
        finally:
            self._processing_batch = False
    
    async def _check_alerts(self, user_id: int):
        """
        Check and send usage alerts
        """
        if not self.alert_system:
            return
        
        try:
            current_usage = await self._get_cached_usage(user_id)
            plan_config = self.PLANS[PlanType.BASIC]  # TODO: Get user's actual plan
            
            usage_percentage = (current_usage / plan_config.monthly_token_limit) * 100
            
            # Send appropriate alerts
            if usage_percentage >= 100:
                await self.alert_system.send_limit_alert(user_id)
            elif usage_percentage >= 90:
                await self.alert_system.send_usage_alert(user_id, 90)
            elif usage_percentage >= 80:
                await self.alert_system.send_usage_alert(user_id, 80)
                
        except Exception as e:
            logger.error(f"Error checking alerts for user {user_id}: {e}")
    
    def get_pricing(self, model: str) -> TokenPricing:
        """Get pricing for model"""
        return self.PRICING.get(model, self.PRICING["gpt-4.1"])
    
    def get_plan_config(self, plan_type: PlanType) -> PlanConfig:
        """Get plan configuration"""
        return self.PLANS[plan_type]
    
    async def flush_batch(self):
        """Force process remaining batch items"""
        if self._batch_queue:
            await self._process_batch()
    
    def clear_cache(self, user_id: Optional[int] = None):
        """Clear usage cache"""
        if user_id:
            self._usage_cache.pop(user_id, None)
        else:
            self._usage_cache.clear()