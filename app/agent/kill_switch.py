"""
Emergency Kill Switch System for AI Agent Operations
Provides immediate shutdown capabilities with multiple trigger mechanisms
"""
import asyncio
import time
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import redis
import signal
import os
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class ThreatLevel(Enum):
    """Threat level classification"""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"

class KillSwitchTrigger(Enum):
    """Types of kill switch triggers"""
    MANUAL = "manual"
    COST_EXCEEDED = "cost_exceeded"
    ERROR_RATE = "error_rate"
    SECURITY_VIOLATION = "security_violation"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    ADMIN_OVERRIDE = "admin_override"

@dataclass
class KillSwitchEvent:
    """Kill switch event record"""
    event_id: str
    agent_id: str
    trigger: KillSwitchTrigger
    threat_level: ThreatLevel
    timestamp: float
    reason: str
    metadata: Dict[str, Any]
    triggered_by: str = "system"
    actions_taken: List[str] = None
    
    def __post_init__(self):
        if self.actions_taken is None:
            self.actions_taken = []

@dataclass
class KillSwitchConfig:
    """Kill switch configuration"""
    enabled: bool = True
    auto_triggers: Dict[str, Any] = None
    notification_webhooks: List[str] = None
    emergency_contacts: List[str] = None
    grace_period_seconds: int = 5
    
    def __post_init__(self):
        if self.auto_triggers is None:
            self.auto_triggers = {
                "max_cost_per_hour": 100.0,
                "max_error_rate": 0.5,
                "max_security_violations": 3,
                "max_concurrent_violations": 5
            }
        if self.notification_webhooks is None:
            self.notification_webhooks = []
        if self.emergency_contacts is None:
            self.emergency_contacts = []

class EmergencyKillSwitch:
    """
    Emergency kill switch system for AI agent operations
    Provides multiple trigger mechanisms and immediate shutdown capabilities
    """
    
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.active_agents: Dict[str, Dict[str, Any]] = {}
        self.shutdown_callbacks: List[Callable] = []
        self.notification_executor = ThreadPoolExecutor(max_workers=2)
        self._monitoring_task = None
        self._is_monitoring = False
        
    async def start_monitoring(self):
        """Start continuous monitoring for kill switch triggers"""
        if self._is_monitoring:
            return
            
        self._is_monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitor_threats())
        logger.info("Kill switch monitoring started")
    
    async def stop_monitoring(self):
        """Stop monitoring"""
        self._is_monitoring = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
        self.notification_executor.shutdown(wait=False)
        logger.info("Kill switch monitoring stopped")
    
    async def register_agent(self, agent_id: str, metadata: Dict[str, Any] = None):
        """Register an agent for monitoring"""
        self.active_agents[agent_id] = {
            "registered_at": time.time(),
            "last_activity": time.time(),
            "metadata": metadata or {},
            "violations": [],
            "status": "active"
        }
        
        # Store in Redis for persistence
        await self.redis.hset(
            "kill_switch:active_agents",
            agent_id,
            json.dumps(self.active_agents[agent_id], default=str)
        )
        
        logger.info(f"Agent {agent_id} registered with kill switch")
    
    async def unregister_agent(self, agent_id: str):
        """Unregister an agent"""
        if agent_id in self.active_agents:
            del self.active_agents[agent_id]
        
        await self.redis.hdel("kill_switch:active_agents", agent_id)
        logger.info(f"Agent {agent_id} unregistered from kill switch")
    
    async def trigger_kill_switch(
        self,
        agent_id: str,
        trigger: KillSwitchTrigger,
        threat_level: ThreatLevel,
        reason: str,
        metadata: Dict[str, Any] = None,
        triggered_by: str = "system"
    ) -> KillSwitchEvent:
        """
        Trigger kill switch for specific agent or globally
        """
        event_id = f"ks_{int(time.time())}_{agent_id}"
        
        event = KillSwitchEvent(
            event_id=event_id,
            agent_id=agent_id,
            trigger=trigger,
            threat_level=threat_level,
            timestamp=time.time(),
            reason=reason,
            metadata=metadata or {},
            triggered_by=triggered_by
        )
        
        # Log the event
        await self._log_kill_switch_event(event)
        
        # Execute shutdown based on threat level
        if threat_level == ThreatLevel.CRITICAL:
            await self._execute_global_shutdown(event)
        elif threat_level == ThreatLevel.HIGH:
            await self._execute_agent_shutdown(agent_id, event)
        elif threat_level == ThreatLevel.MEDIUM:
            await self._execute_agent_suspension(agent_id, event)
        else:
            await self._execute_warning(agent_id, event)
        
        # Send notifications
        await self._send_notifications(event)
        
        logger.critical(f"Kill switch triggered: {trigger.value} for agent {agent_id} - {reason}")
        return event
    
    async def manual_shutdown(
        self,
        agent_id: str,
        reason: str,
        triggered_by: str = "manual"
    ) -> KillSwitchEvent:
        """Manual kill switch trigger"""
        return await self.trigger_kill_switch(
            agent_id=agent_id,
            trigger=KillSwitchTrigger.MANUAL,
            threat_level=ThreatLevel.HIGH,
            reason=reason,
            triggered_by=triggered_by
        )
    
    async def emergency_global_shutdown(
        self,
        reason: str,
        triggered_by: str = "emergency"
    ) -> List[KillSwitchEvent]:
        """Emergency shutdown of all agents"""
        events = []
        
        for agent_id in list(self.active_agents.keys()):
            event = await self.trigger_kill_switch(
                agent_id=agent_id,
                trigger=KillSwitchTrigger.ADMIN_OVERRIDE,
                threat_level=ThreatLevel.CRITICAL,
                reason=f"Global emergency: {reason}",
                triggered_by=triggered_by
            )
            events.append(event)
        
        return events
    
    async def add_shutdown_callback(self, callback: Callable):
        """Add callback to be executed during shutdown"""
        self.shutdown_callbacks.append(callback)
    
    async def check_auto_triggers(self, agent_id: str) -> Optional[KillSwitchEvent]:
        """Check if any automatic triggers should fire"""
        config = await self._get_kill_switch_config(agent_id)
        if not config.enabled:
            return None
        
        # Check cost limits
        cost_key = f"cost:{agent_id}:{int(time.time() // 3600)}"
        hour_cost = float(await self.redis.get(cost_key) or 0)
        
        if hour_cost > config.auto_triggers.get("max_cost_per_hour", 100.0):
            return await self.trigger_kill_switch(
                agent_id=agent_id,
                trigger=KillSwitchTrigger.COST_EXCEEDED,
                threat_level=ThreatLevel.HIGH,
                reason=f"Hourly cost limit exceeded: ${hour_cost:.2f}",
                metadata={"hour_cost": hour_cost}
            )
        
        # Check error rate
        performance = await self._get_performance_metrics(agent_id)
        error_rate = 1.0 - performance.get("success_rate", 1.0)
        
        if error_rate > config.auto_triggers.get("max_error_rate", 0.5):
            return await self.trigger_kill_switch(
                agent_id=agent_id,
                trigger=KillSwitchTrigger.ERROR_RATE,
                threat_level=ThreatLevel.MEDIUM,
                reason=f"High error rate: {error_rate:.2%}",
                metadata={"error_rate": error_rate}
            )
        
        # Check security violations
        violations = await self._get_recent_violations(agent_id)
        if len(violations) > config.auto_triggers.get("max_security_violations", 3):
            return await self.trigger_kill_switch(
                agent_id=agent_id,
                trigger=KillSwitchTrigger.SECURITY_VIOLATION,
                threat_level=ThreatLevel.HIGH,
                reason=f"Multiple security violations: {len(violations)}",
                metadata={"violations": violations}
            )
        
        return None
    
    async def get_kill_switch_status(self) -> Dict[str, Any]:
        """Get current kill switch status"""
        active_count = len(self.active_agents)
        
        # Get recent events
        recent_events = await self._get_recent_events(limit=10)
        
        # Get global statistics
        stats = await self._get_statistics()
        
        return {
            "monitoring_enabled": self._is_monitoring,
            "active_agents": active_count,
            "recent_events": recent_events,
            "statistics": stats,
            "system_status": "operational" if self._is_monitoring else "disabled"
        }
    
    async def _execute_global_shutdown(self, event: KillSwitchEvent):
        """Execute global shutdown of all systems"""
        logger.critical("EXECUTING GLOBAL SHUTDOWN")
        
        # Stop all active agents
        for agent_id in list(self.active_agents.keys()):
            await self._stop_agent_immediately(agent_id)
            event.actions_taken.append(f"stopped_agent_{agent_id}")
        
        # Execute shutdown callbacks
        for callback in self.shutdown_callbacks:
            try:
                await callback(event)
                event.actions_taken.append(f"executed_callback_{callback.__name__}")
            except Exception as e:
                logger.error(f"Shutdown callback failed: {e}")
        
        # Set global kill switch state
        await self.redis.setex("kill_switch:global_shutdown", 3600, "active")
        event.actions_taken.append("global_shutdown_activated")
    
    async def _execute_agent_shutdown(self, agent_id: str, event: KillSwitchEvent):
        """Shutdown specific agent"""
        logger.warning(f"SHUTTING DOWN AGENT: {agent_id}")
        
        await self._stop_agent_immediately(agent_id)
        
        # Block agent from restarting
        await self.redis.setex(f"kill_switch:blocked:{agent_id}", 3600, "blocked")
        
        event.actions_taken.extend([
            f"stopped_agent_{agent_id}",
            f"blocked_agent_{agent_id}"
        ])
    
    async def _execute_agent_suspension(self, agent_id: str, event: KillSwitchEvent):
        """Suspend agent temporarily"""
        logger.warning(f"SUSPENDING AGENT: {agent_id}")
        
        if agent_id in self.active_agents:
            self.active_agents[agent_id]["status"] = "suspended"
        
        # Temporary suspension
        await self.redis.setex(f"kill_switch:suspended:{agent_id}", 1800, "suspended")  # 30 min
        
        event.actions_taken.append(f"suspended_agent_{agent_id}")
    
    async def _execute_warning(self, agent_id: str, event: KillSwitchEvent):
        """Issue warning for agent"""
        logger.warning(f"WARNING ISSUED FOR AGENT: {agent_id}")
        
        if agent_id in self.active_agents:
            self.active_agents[agent_id]["violations"].append({
                "timestamp": time.time(),
                "reason": event.reason,
                "threat_level": event.threat_level.value
            })
        
        event.actions_taken.append(f"warning_issued_{agent_id}")
    
    async def _stop_agent_immediately(self, agent_id: str):
        """Immediately stop agent execution"""
        # Send termination signal to agent processes
        processes_key = f"agent_processes:{agent_id}"
        process_ids = await self.redis.smembers(processes_key)
        
        for pid_bytes in process_ids:
            try:
                pid = int(pid_bytes.decode())
                os.kill(pid, signal.SIGTERM)
                logger.info(f"Sent SIGTERM to process {pid} for agent {agent_id}")
            except (ValueError, ProcessLookupError) as e:
                logger.warning(f"Could not terminate process {pid_bytes}: {e}")
        
        # Clear from active agents
        if agent_id in self.active_agents:
            self.active_agents[agent_id]["status"] = "terminated"
    
    async def _monitor_threats(self):
        """Continuous monitoring for automatic triggers"""
        while self._is_monitoring:
            try:
                for agent_id in list(self.active_agents.keys()):
                    await self.check_auto_triggers(agent_id)
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in threat monitoring: {e}")
                await asyncio.sleep(10)
    
    async def _log_kill_switch_event(self, event: KillSwitchEvent):
        """Log kill switch event for audit"""
        events_key = "kill_switch:events"
        
        event_data = json.dumps(asdict(event), default=str)
        await self.redis.lpush(events_key, event_data)
        await self.redis.ltrim(events_key, 0, 999)  # Keep last 1000 events
        await self.redis.expire(events_key, 2592000)  # 30 days
    
    async def _send_notifications(self, event: KillSwitchEvent):
        """Send notifications about kill switch event"""
        config = await self._get_kill_switch_config(event.agent_id)
        
        # Send webhook notifications
        for webhook_url in config.notification_webhooks:
            self.notification_executor.submit(
                self._send_webhook_notification, webhook_url, event
            )
        
        # Log notification sent
        logger.info(f"Notifications sent for kill switch event {event.event_id}")
    
    def _send_webhook_notification(self, webhook_url: str, event: KillSwitchEvent):
        """Send webhook notification (sync function for thread executor)"""
        try:
            import requests
            
            payload = {
                "event_type": "kill_switch_triggered",
                "agent_id": event.agent_id,
                "trigger": event.trigger.value,
                "threat_level": event.threat_level.value,
                "reason": event.reason,
                "timestamp": event.timestamp
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
    
    async def _get_kill_switch_config(self, agent_id: str) -> KillSwitchConfig:
        """Get kill switch configuration for agent"""
        config_key = f"kill_switch:config:{agent_id}"
        config_data = await self.redis.get(config_key)
        
        if config_data:
            data = json.loads(config_data)
            return KillSwitchConfig(**data)
        
        # Return default config
        return KillSwitchConfig()
    
    async def _get_performance_metrics(self, agent_id: str) -> Dict[str, float]:
        """Get performance metrics for agent"""
        metrics_key = f"performance:{agent_id}"
        metrics = await self.redis.get(metrics_key)
        
        if metrics:
            return json.loads(metrics)
        
        return {"success_rate": 1.0, "avg_response_time": 0.0}
    
    async def _get_recent_violations(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get recent security violations for agent"""
        violations_key = f"security_violations:{agent_id}"
        violations = await self.redis.lrange(violations_key, 0, 10)
        
        return [json.loads(v) for v in violations]
    
    async def _get_recent_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent kill switch events"""
        events_key = "kill_switch:events"
        events = await self.redis.lrange(events_key, 0, limit - 1)
        
        return [json.loads(e) for e in events]
    
    async def _get_statistics(self) -> Dict[str, Any]:
        """Get kill switch statistics"""
        events = await self._get_recent_events(100)
        
        trigger_counts = {}
        threat_counts = {}
        
        for event in events:
            trigger = event.get("trigger", "unknown")
            threat = event.get("threat_level", "unknown")
            
            trigger_counts[trigger] = trigger_counts.get(trigger, 0) + 1
            threat_counts[threat] = threat_counts.get(threat, 0) + 1
        
        return {
            "total_events": len(events),
            "trigger_breakdown": trigger_counts,
            "threat_level_breakdown": threat_counts,
            "last_24h_events": len([e for e in events if time.time() - e.get("timestamp", 0) < 86400])
        }