# app/core/token_system.py

from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.token_manager import TokenManager
from app.services.token_storage_service import DatabaseTokenStorage
from app.services.token_alert_service import (
    MultiChannelAlertSystem, 
    create_basic_alert_system,
    create_full_alert_system
)
# from app.decorators.token_tracking import TokenTracker  # LEGACY - Removed

logger = logging.getLogger(__name__)

class TokenSystemFactory:
    """
    Factory for creating optimized token system components
    """
    
    @staticmethod
    def create_token_manager(
        db: AsyncSession,
        alert_config: Optional[Dict[str, Any]] = None,
        batch_size: int = 10
    ) -> TokenManager:
        """
        Create optimized token manager with all components
        """
        # Create storage
        storage = DatabaseTokenStorage(db)
        
        # Create alert system
        if alert_config:
            alert_system = create_full_alert_system(
                smtp_config=alert_config.get("smtp"),
                webhook_url=alert_config.get("webhook_url")
            )
        else:
            alert_system = create_basic_alert_system()
        
        # Create manager
        return TokenManager(
            storage=storage,
            alert_system=alert_system,
            batch_size=batch_size
        )
    
    # @staticmethod
    # def create_token_tracker(token_manager: TokenManager) -> TokenTracker:
    #     """Create token tracker decorator - LEGACY"""
    #     return TokenTracker(token_manager)

# Global instances (to be configured in app startup)
_token_manager: Optional[TokenManager] = None
# _token_tracker: Optional[TokenTracker] = None  # LEGACY

def initialize_token_system(
    db: AsyncSession,
    alert_config: Optional[Dict[str, Any]] = None,
    batch_size: int = 10
):
    """
    Initialize global token system
    """
    global _token_manager
    
    _token_manager = TokenSystemFactory.create_token_manager(
        db=db,
        alert_config=alert_config,
        batch_size=batch_size
    )
    
    # _token_tracker = TokenSystemFactory.create_token_tracker(_token_manager)  # LEGACY
    
    logger.info("✅ Token system initialized")

def get_token_manager() -> TokenManager:
    """Get global token manager"""
    if _token_manager is None:
        raise RuntimeError("Token system not initialized. Call initialize_token_system() first.")
    return _token_manager

# def get_token_tracker() -> TokenTracker:
#     """Get global token tracker - LEGACY"""
#     if _token_tracker is None:
#         raise RuntimeError("Token system not initialized. Call initialize_token_system() first.")
#     return _token_tracker

# Convenience decorators - COMMENTED OUT (legacy dependencies)
# def track_workflow_tokens(
#     estimate_tokens = None,
#     check_limits: bool = True
# ):
#     """
#     Convenience decorator for workflow token tracking
#     """
#     from app.core.token_manager import OperationType
#     from app.decorators.token_tracking import TokenEstimators
#     
#     tracker = get_token_tracker()
#     return tracker.track(
#         operation_type=OperationType.WORKFLOW,
#         estimate_tokens=estimate_tokens or TokenEstimators.workflow_tokens,
#         check_limits=check_limits
#     )

# def track_chat_tokens(
#     estimate_tokens = None,
#     check_limits: bool = True
# ):
#     """
#     Convenience decorator for chat token tracking
#     """
#     from app.core.token_manager import OperationType
#     from app.decorators.token_tracking import TokenEstimators
#     
#     tracker = get_token_tracker()
#     return tracker.track(
#         operation_type=OperationType.CHAT,
#         estimate_tokens=estimate_tokens or TokenEstimators.chat_tokens,
#         check_limits=check_limits
#     )

# def track_ai_agent_tokens(
#     estimate_tokens = None,
#     check_limits: bool = True
# ):
#     """
#     Convenience decorator for AI agent token tracking
#     """
#     from app.core.token_manager import OperationType
#     from app.decorators.token_tracking import TokenEstimators
#     
#     tracker = get_token_tracker()
#     return tracker.track(
#         operation_type=OperationType.AI_AGENT,
#         estimate_tokens=estimate_tokens or TokenEstimators.ai_agent_tokens,
#         check_limits=check_limits
#     )

# Health check function
async def health_check() -> Dict[str, Any]:
    """
    Health check for token system
    """
    try:
        manager = get_token_manager()
        
        # Basic connectivity test
        test_status = await manager.can_use_tokens(user_id=1, estimated_tokens=100)
        
        return {
            "status": "healthy",
            "components": {
                "token_manager": "ok",
                "storage": "ok", 
                "alerts": "ok"
            },
            "test_result": {
                "can_use_tokens": test_status.can_use
            }
        }
    except Exception as e:
        logger.error(f"Token system health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

# Configuration helpers
class TokenSystemConfig:
    """Configuration helper for token system"""
    
    @staticmethod
    def get_development_config() -> Dict[str, Any]:
        """Development configuration"""
        return {
            "batch_size": 5,  # Smaller batches for dev
            "alert_config": None  # Basic alerts only
        }
    
    @staticmethod
    def get_production_config() -> Dict[str, Any]:
        """Production configuration"""
        return {
            "batch_size": 20,  # Larger batches for performance
            "alert_config": {
                "smtp": {
                    "host": "smtp.gmail.com",
                    "port": 587,
                    "username": "alerts@yourapp.com",
                    "password": "your-password"  # Use env var
                },
                "webhook_url": "https://your-webhook-endpoint.com/token-alerts"
            }
        }