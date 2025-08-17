# app/services/token_alert_service.py

from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
import asyncio
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass

from app.core.token_manager import AlertSystem

logger = logging.getLogger(__name__)

@dataclass
class AlertContext:
    """Context for alert notifications"""
    user_id: int
    username: Optional[str] = None
    email: Optional[str] = None
    current_usage: int = 0
    limit: int = 0
    plan_type: str = "basic"
    remaining_tokens: int = 0

class BaseAlertChannel(ABC):
    """Base class for alert channels"""
    
    @abstractmethod
    async def send(self, context: AlertContext, message: str) -> bool:
        """Send alert through this channel"""
        pass

class EmailAlertChannel(BaseAlertChannel):
    """Email alert channel"""
    
    def __init__(self, smtp_config: Optional[Dict[str, Any]] = None):
        self.smtp_config = smtp_config or {}
    
    async def send(self, context: AlertContext, message: str) -> bool:
        """Send email alert"""
        try:
            # TODO: Implement actual email sending
            logger.info(f"📧 EMAIL ALERT to {context.email}: {message}")
            
            # Simulate email sending delay
            await asyncio.sleep(0.1)
            return True
            
        except Exception as e:
            logger.error(f"Error sending email alert: {e}")
            return False

class InAppAlertChannel(BaseAlertChannel):
    """In-app notification channel"""
    
    def __init__(self, notification_service=None):
        self.notification_service = notification_service
    
    async def send(self, context: AlertContext, message: str) -> bool:
        """Send in-app notification"""
        try:
            # TODO: Implement actual in-app notification
            logger.info(f"🔔 IN-APP ALERT to user {context.user_id}: {message}")
            
            # Here you would integrate with your notification system
            # await self.notification_service.send_notification(context.user_id, message)
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending in-app alert: {e}")
            return False

class WebhookAlertChannel(BaseAlertChannel):
    """Webhook alert channel for integrations"""
    
    def __init__(self, webhook_url: str, headers: Optional[Dict[str, str]] = None):
        self.webhook_url = webhook_url
        self.headers = headers or {"Content-Type": "application/json"}
    
    async def send(self, context: AlertContext, message: str) -> bool:
        """Send webhook alert"""
        try:
            import httpx
            
            payload = {
                "user_id": context.user_id,
                "alert_type": "token_usage",
                "message": message,
                "context": {
                    "current_usage": context.current_usage,
                    "limit": context.limit,
                    "plan_type": context.plan_type,
                    "remaining_tokens": context.remaining_tokens
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
            
            logger.info(f"🪝 WEBHOOK ALERT sent to {self.webhook_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending webhook alert: {e}")
            return False

class MultiChannelAlertSystem(AlertSystem):
    """
    Multi-channel alert system with rate limiting and deduplication
    """
    
    def __init__(
        self,
        channels: List[BaseAlertChannel],
        rate_limit_minutes: int = 60,
        max_alerts_per_user: int = 3
    ):
        self.channels = channels
        self.rate_limit_minutes = rate_limit_minutes
        self.max_alerts_per_user = max_alerts_per_user
        
        # Rate limiting tracking
        self._alert_history: Dict[str, List[datetime]] = {}
        
        # Message templates
        self.templates = {
            80: "⚠️ Token Usage Alert: You've used 80% of your monthly tokens ({current_usage:,}/{limit:,}). Remaining: {remaining:,} tokens.",
            90: "🚨 Token Usage Warning: You've used 90% of your monthly tokens ({current_usage:,}/{limit:,}). Only {remaining:,} tokens left!",
            100: "🛑 Token Limit Reached: You've reached your monthly limit of {limit:,} tokens. Upgrade your plan or wait for next reset.",
        }
    
    async def send_usage_alert(self, user_id: int, percentage: int) -> bool:
        """Send usage percentage alert"""
        alert_key = f"{user_id}_usage_{percentage}"
        
        if not self._should_send_alert(alert_key):
            logger.debug(f"Skipping alert {alert_key} due to rate limiting")
            return False
        
        try:
            # Get user context (this would come from a user service)
            context = await self._get_user_context(user_id)
            
            # Get message template
            message = self._format_message(percentage, context)
            
            # Send through all channels concurrently
            tasks = []
            for channel in self.channels:
                tasks.append(channel.send(context, message))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log results
            success_count = sum(1 for r in results if r is True)
            logger.info(f"Alert {alert_key} sent through {success_count}/{len(self.channels)} channels")
            
            # Track successful alert
            self._track_alert(alert_key)
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error sending usage alert: {e}")
            return False
    
    async def send_limit_alert(self, user_id: int) -> bool:
        """Send limit reached alert"""
        alert_key = f"{user_id}_limit"
        
        if not self._should_send_alert(alert_key):
            return False
        
        try:
            context = await self._get_user_context(user_id)
            message = self._format_message(100, context)
            
            # Send through all channels
            tasks = []
            for channel in self.channels:
                tasks.append(channel.send(context, message))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            success_count = sum(1 for r in results if r is True)
            
            self._track_alert(alert_key)
            
            logger.info(f"Limit alert for user {user_id} sent through {success_count}/{len(self.channels)} channels")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error sending limit alert: {e}")
            return False
    
    def _should_send_alert(self, alert_key: str) -> bool:
        """Check if alert should be sent based on rate limiting"""
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=self.rate_limit_minutes)
        
        # Clean old alerts
        if alert_key in self._alert_history:
            self._alert_history[alert_key] = [
                alert_time for alert_time in self._alert_history[alert_key]
                if alert_time > cutoff
            ]
            
            # Check rate limit
            if len(self._alert_history[alert_key]) >= self.max_alerts_per_user:
                return False
        
        return True
    
    def _track_alert(self, alert_key: str):
        """Track sent alert for rate limiting"""
        if alert_key not in self._alert_history:
            self._alert_history[alert_key] = []
        
        self._alert_history[alert_key].append(datetime.utcnow())
    
    async def _get_user_context(self, user_id: int) -> AlertContext:
        """Get user context for alerts"""
        # TODO: Get actual user data from database
        # This is a placeholder - implement actual user lookup
        return AlertContext(
            user_id=user_id,
            username=f"user_{user_id}",
            email=f"user_{user_id}@example.com",
            current_usage=0,  # Will be populated when integrated
            limit=100000,
            plan_type="basic",
            remaining_tokens=0
        )
    
    def _format_message(self, percentage: int, context: AlertContext) -> str:
        """Format alert message"""
        template = self.templates.get(percentage, self.templates[100])
        
        return template.format(
            current_usage=context.current_usage,
            limit=context.limit,
            remaining=context.remaining_tokens,
            percentage=percentage
        )
    
    def add_channel(self, channel: BaseAlertChannel):
        """Add new alert channel"""
        self.channels.append(channel)
    
    def remove_channel(self, channel: BaseAlertChannel):
        """Remove alert channel"""
        if channel in self.channels:
            self.channels.remove(channel)
    
    def clear_alert_history(self, user_id: Optional[int] = None):
        """Clear alert history for debugging"""
        if user_id:
            keys_to_clear = [k for k in self._alert_history.keys() if k.startswith(f"{user_id}_")]
            for key in keys_to_clear:
                del self._alert_history[key]
        else:
            self._alert_history.clear()

# Factory functions for easy setup
def create_basic_alert_system() -> MultiChannelAlertSystem:
    """Create basic alert system with in-app notifications"""
    channels = [
        InAppAlertChannel(),
    ]
    return MultiChannelAlertSystem(channels)

def create_full_alert_system(
    smtp_config: Optional[Dict[str, Any]] = None,
    webhook_url: Optional[str] = None
) -> MultiChannelAlertSystem:
    """Create full alert system with all channels"""
    channels = [
        InAppAlertChannel(),
        EmailAlertChannel(smtp_config),
    ]
    
    if webhook_url:
        channels.append(WebhookAlertChannel(webhook_url))
    
    return MultiChannelAlertSystem(channels)