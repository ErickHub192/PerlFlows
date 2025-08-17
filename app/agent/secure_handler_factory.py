"""
Secure Handler Factory Orchestrator
Central system that coordinates all security components for safe handler execution
"""
import asyncio
import time
import uuid
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
import logging

from .security_sandbox import SecuritySandbox, SecurityLimits, execute_in_sandbox
from .rate_limiter import IntelligentRateLimiter, RateLimitExceededError
from .kill_switch import EmergencyKillSwitch, ThreatLevel, KillSwitchTrigger
from .handler_validator import HandlerValidator, ValidationLevel, ValidationResult
from .security_monitor import SecurityMonitor, AgentMetrics, AlertSeverity, MetricType

logger = logging.getLogger(__name__)

class ExecutionStatus(Enum):
    """Handler execution status"""
    PENDING = "pending"
    VALIDATING = "validating"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    KILLED = "killed"

@dataclass
class HandlerRequest:
    """Handler execution request"""
    request_id: str
    agent_id: str
    handler_name: str
    handler_code: str
    params: Dict[str, Any]
    priority: int = 1
    timeout: int = 30
    validation_level: ValidationLevel = ValidationLevel.STANDARD
    security_limits: Optional[SecurityLimits] = None

@dataclass
class ExecutionResult:
    """Complete execution result with security metrics"""
    request_id: str
    status: ExecutionStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    validation_report: Optional[Dict[str, Any]] = None
    execution_metrics: Optional[Dict[str, Any]] = None
    security_violations: List[str] = None
    execution_time: float = 0.0
    cost_estimate: float = 0.0
    
    def __post_init__(self):
        if self.security_violations is None:
            self.security_violations = []

class SecureHandlerFactory:
    """
    Central orchestrator for secure handler execution
    Integrates sandbox, rate limiter, kill switch, validator, and monitor
    """
    
    def __init__(self, redis_url: str):
        # Initialize all security components
        self.sandbox = SecuritySandbox()
        self.rate_limiter = IntelligentRateLimiter(redis_url)
        self.kill_switch = EmergencyKillSwitch(redis_url)
        self.validator = HandlerValidator(redis_url)
        self.monitor = SecurityMonitor(redis_url)
        
        # Execution tracking
        self.active_executions: Dict[str, HandlerRequest] = {}
        self.execution_history: List[ExecutionResult] = []
        
        # System state
        self._is_running = False
        self._monitoring_task = None
        
    async def start(self):
        """Start the secure handler factory system"""
        if self._is_running:
            return
        
        logger.info("Starting Secure Handler Factory...")
        
        # Start all subsystems
        await self.kill_switch.start_monitoring()
        await self.monitor.start_monitoring()
        
        # Add kill switch callbacks
        await self.kill_switch.add_shutdown_callback(self._emergency_shutdown_callback)
        
        # Start internal monitoring
        self._monitoring_task = asyncio.create_task(self._internal_monitoring_loop())
        
        self._is_running = True
        logger.info("Secure Handler Factory started successfully")
    
    async def stop(self):
        """Stop the secure handler factory system"""
        if not self._is_running:
            return
        
        logger.info("Stopping Secure Handler Factory...")
        
        # Cancel all active executions
        for request_id in list(self.active_executions.keys()):
            await self._cancel_execution(request_id, "System shutdown")
        
        # Stop subsystems
        await self.kill_switch.stop_monitoring()
        await self.monitor.stop_monitoring()
        await self.sandbox.cleanup()
        
        # Stop internal monitoring
        if self._monitoring_task:
            self._monitoring_task.cancel()
        
        self._is_running = False
        logger.info("Secure Handler Factory stopped")
    
    async def execute_handler(self, request: HandlerRequest) -> ExecutionResult:
        """
        Execute a handler with full security orchestration
        """
        start_time = time.time()
        execution_result = ExecutionResult(
            request_id=request.request_id,
            status=ExecutionStatus.PENDING
        )
        
        try:
            # Register with kill switch
            await self.kill_switch.register_agent(
                request.agent_id, 
                {"handler": request.handler_name, "request_id": request.request_id}
            )
            
            # Track active execution
            self.active_executions[request.request_id] = request
            
            # Phase 1: Rate Limiting Check
            logger.info(f"Checking rate limits for {request.agent_id}")
            rate_check = await self.rate_limiter.check_limits(
                request.agent_id,
                operation_cost=0.01,  # Estimated cost
                estimated_tokens=1000
            )
            
            if not rate_check["allowed"]:
                execution_result.status = ExecutionStatus.BLOCKED
                execution_result.error = f"Rate limit exceeded: {rate_check['violations']}"
                return execution_result
            
            # Phase 2: Handler Validation
            logger.info(f"Validating handler {request.handler_name}")
            execution_result.status = ExecutionStatus.VALIDATING
            
            validation_report = await self.validator.validate_handler(
                request.handler_code,
                request.handler_name,
                request.validation_level
            )
            
            execution_result.validation_report = {
                "overall_result": validation_report.overall_result.value,
                "security_score": validation_report.security_score,
                "performance_score": validation_report.performance_score,
                "correctness_score": validation_report.correctness_score,
                "issues_count": len(validation_report.issues)
            }
            
            # Block execution if validation fails
            if validation_report.overall_result in [ValidationResult.FAILED, ValidationResult.BLOCKED]:
                execution_result.status = ExecutionStatus.BLOCKED
                execution_result.error = f"Validation failed: {validation_report.overall_result.value}"
                
                # Create security alert
                await self.monitor.create_alert(
                    agent_id=request.agent_id,
                    severity=AlertSeverity.WARNING,
                    metric_type=MetricType.SECURITY_VIOLATIONS,
                    message=f"Handler validation failed: {request.handler_name}",
                    value=len(validation_report.issues),
                    threshold=0
                )
                
                return execution_result
            
            # Phase 3: Acquire Concurrent Slot
            slot_id = await self.rate_limiter.acquire_concurrent_slot(request.agent_id)
            
            try:
                # Phase 4: Secure Execution
                logger.info(f"Executing handler {request.handler_name} in sandbox")
                execution_result.status = ExecutionStatus.EXECUTING
                
                # Create handler function from code
                handler_func = await self._create_handler_function(
                    request.handler_code, 
                    request.handler_name
                )
                
                # Execute in sandbox
                sandbox_result = await execute_in_sandbox(
                    handler_func,
                    request.handler_name,
                    request.params,
                    request.security_limits
                )
                
                execution_result.execution_metrics = sandbox_result.get("metrics", {})
                
                if sandbox_result["status"] == "success":
                    execution_result.status = ExecutionStatus.COMPLETED
                    execution_result.result = sandbox_result["result"]
                elif sandbox_result["status"] == "security_violation":
                    execution_result.status = ExecutionStatus.BLOCKED
                    execution_result.error = sandbox_result["error"]
                    execution_result.security_violations.append(sandbox_result["error"])
                    
                    # Trigger kill switch for security violation
                    await self.kill_switch.trigger_kill_switch(
                        agent_id=request.agent_id,
                        trigger=KillSwitchTrigger.SECURITY_VIOLATION,
                        threat_level=ThreatLevel.HIGH,
                        reason=f"Security violation in handler {request.handler_name}",
                        metadata={"request_id": request.request_id, "violation": sandbox_result["error"]}
                    )
                else:
                    execution_result.status = ExecutionStatus.FAILED
                    execution_result.error = sandbox_result["error"]
            
            finally:
                # Release concurrent slot
                await self.rate_limiter.release_concurrent_slot(request.agent_id, slot_id)
        
        except RateLimitExceededError as e:
            execution_result.status = ExecutionStatus.BLOCKED
            execution_result.error = f"Rate limit exceeded: {e}"
            
        except Exception as e:
            execution_result.status = ExecutionStatus.FAILED
            execution_result.error = f"Execution failed: {str(e)}"
            logger.error(f"Handler execution failed: {e}")
            
        finally:
            # Calculate final metrics
            execution_result.execution_time = time.time() - start_time
            execution_result.cost_estimate = self._estimate_cost(execution_result.execution_time)
            
            # Record operation metrics
            await self.rate_limiter.record_operation(
                agent_id=request.agent_id,
                operation_cost=execution_result.cost_estimate,
                tokens_used=execution_result.execution_metrics.get("tokens_used", 0) if execution_result.execution_metrics else 0,
                success=(execution_result.status == ExecutionStatus.COMPLETED),
                response_time=execution_result.execution_time,
                operation_type=request.handler_name
            )
            
            # Update monitoring metrics
            await self._update_agent_metrics(request.agent_id, execution_result)
            
            # Clean up
            self.active_executions.pop(request.request_id, None)
            await self.kill_switch.unregister_agent(request.agent_id)
            
            # Store result in history
            self.execution_history.append(execution_result)
            if len(self.execution_history) > 1000:
                self.execution_history.pop(0)
        
        return execution_result
    
    async def create_handler_request(
        self,
        agent_id: str,
        handler_name: str,
        handler_code: str,
        params: Dict[str, Any],
        priority: int = 1,
        timeout: int = 30,
        validation_level: ValidationLevel = ValidationLevel.STANDARD
    ) -> HandlerRequest:
        """Create a new handler execution request"""
        request_id = f"req_{uuid.uuid4().hex[:8]}"
        
        return HandlerRequest(
            request_id=request_id,
            agent_id=agent_id,
            handler_name=handler_name,
            handler_code=handler_code,
            params=params,
            priority=priority,
            timeout=timeout,
            validation_level=validation_level
        )
    
    async def get_execution_status(self, request_id: str) -> Optional[ExecutionStatus]:
        """Get current execution status"""
        if request_id in self.active_executions:
            return ExecutionStatus.EXECUTING
        
        # Check history
        for result in reversed(self.execution_history):
            if result.request_id == request_id:
                return result.status
        
        return None
    
    async def cancel_execution(self, request_id: str, reason: str = "User cancelled") -> bool:
        """Cancel an active execution"""
        return await self._cancel_execution(request_id, reason)
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        kill_switch_status = await self.kill_switch.get_kill_switch_status()
        dashboard_data = await self.monitor.get_dashboard_data()
        
        return {
            "factory_status": "running" if self._is_running else "stopped",
            "active_executions": len(self.active_executions),
            "total_executions": len(self.execution_history),
            "kill_switch": kill_switch_status,
            "monitoring": dashboard_data,
            "recent_executions": [
                {
                    "request_id": r.request_id,
                    "status": r.status.value,
                    "execution_time": r.execution_time,
                    "agent_id": self.active_executions.get(r.request_id, HandlerRequest("", "", "", "", {})).agent_id
                }
                for r in self.execution_history[-10:]
            ]
        }
    
    async def emergency_shutdown(self, reason: str) -> List[str]:
        """Emergency shutdown of all operations"""
        logger.critical(f"EMERGENCY SHUTDOWN: {reason}")
        
        # Trigger global kill switch
        events = await self.kill_switch.emergency_global_shutdown(reason, "factory")
        
        # Cancel all executions
        cancelled = []
        for request_id in list(self.active_executions.keys()):
            if await self._cancel_execution(request_id, f"Emergency shutdown: {reason}"):
                cancelled.append(request_id)
        
        # Stop the factory
        await self.stop()
        
        return cancelled
    
    async def _create_handler_function(self, handler_code: str, handler_name: str) -> Callable:
        """Create executable function from handler code"""
        # This is a simplified implementation
        # In production, you'd want more sophisticated code compilation and sandboxing
        
        # Create a safe execution environment
        safe_globals = {
            '__builtins__': {
                'len': len, 'str': str, 'int': int, 'float': float,
                'dict': dict, 'list': list, 'tuple': tuple,
                'range': range, 'enumerate': enumerate,
                'print': print, 'isinstance': isinstance
            },
            'json': __import__('json'),
            'time': __import__('time'),
            'asyncio': __import__('asyncio')
        }
        
        # Execute the handler code to define the function
        exec(handler_code, safe_globals)
        
        # Find the handler function (assuming it's a class with execute method)
        handler_class = None
        for name, obj in safe_globals.items():
            if hasattr(obj, 'execute') and callable(getattr(obj, 'execute')):
                handler_class = obj
                break
        
        if not handler_class:
            raise ValueError("No valid handler class found with execute method")
        
        # Create instance and return execute method
        handler_instance = handler_class({})  # Empty creds for now
        return handler_instance.execute
    
    async def _cancel_execution(self, request_id: str, reason: str) -> bool:
        """Cancel an active execution"""
        if request_id not in self.active_executions:
            return False
        
        request = self.active_executions[request_id]
        
        # Create cancellation result
        result = ExecutionResult(
            request_id=request_id,
            status=ExecutionStatus.KILLED,
            error=f"Execution cancelled: {reason}",
            execution_time=time.time()
        )
        
        # Clean up
        self.active_executions.pop(request_id, None)
        self.execution_history.append(result)
        
        # Unregister from kill switch
        await self.kill_switch.unregister_agent(request.agent_id)
        
        logger.info(f"Cancelled execution {request_id}: {reason}")
        return True
    
    async def _update_agent_metrics(self, agent_id: str, result: ExecutionResult):
        """Update agent metrics in the monitoring system"""
        # Get current metrics or create new
        current_metrics = await self.monitor.get_agent_metrics(agent_id)
        
        if current_metrics is None:
            current_metrics = AgentMetrics(agent_id=agent_id, timestamp=time.time())
        
        # Update metrics
        current_metrics.executions_per_minute += 1
        current_metrics.last_activity = time.time()
        
        if result.status == ExecutionStatus.FAILED:
            # Update error rate (simple moving average)
            current_metrics.error_rate = (current_metrics.error_rate * 0.9) + (1.0 * 0.1)
        else:
            current_metrics.error_rate = current_metrics.error_rate * 0.9
        
        if result.execution_time > 0:
            # Update average response time
            current_metrics.avg_response_time = (
                (current_metrics.avg_response_time * 0.8) + 
                (result.execution_time * 0.2)
            )
        
        if result.execution_metrics:
            current_metrics.memory_usage_mb = result.execution_metrics.get("memory_peak_mb", 0)
        
        current_metrics.cost_per_hour += result.cost_estimate * 60  # Convert to hourly rate
        
        if result.security_violations:
            current_metrics.security_violations += len(result.security_violations)
        
        # Record updated metrics
        await self.monitor.record_agent_metrics(agent_id, current_metrics)
    
    def _estimate_cost(self, execution_time: float) -> float:
        """Estimate execution cost based on time and resources"""
        base_cost_per_second = 0.001  # $0.001 per second
        return execution_time * base_cost_per_second
    
    async def _emergency_shutdown_callback(self, event):
        """Callback for kill switch emergency shutdown"""
        logger.critical(f"Kill switch triggered emergency shutdown: {event.reason}")
        await self.emergency_shutdown(f"Kill switch: {event.reason}")
    
    async def _internal_monitoring_loop(self):
        """Internal monitoring and maintenance loop"""
        while self._is_running:
            try:
                # Check for stuck executions
                current_time = time.time()
                stuck_executions = []
                
                for request_id, request in self.active_executions.items():
                    # If execution has been running for more than timeout + 60 seconds, it's stuck
                    if current_time - request.timeout > 60:
                        stuck_executions.append(request_id)
                
                # Cancel stuck executions
                for request_id in stuck_executions:
                    await self._cancel_execution(request_id, "Execution timeout")
                
                # Clean up old history
                if len(self.execution_history) > 1000:
                    self.execution_history = self.execution_history[-500:]
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in internal monitoring: {e}")
                await asyncio.sleep(60)