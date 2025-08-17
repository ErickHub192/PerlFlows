"""
Comprehensive Handler Validation Framework
Validates handlers before execution with security, performance, and correctness checks
"""
import asyncio
import ast
import inspect
import time
import json
import hashlib
from typing import Dict, Any, List, Optional, Callable, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import importlib.util
import tempfile
import os
import redis
import logging

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """Validation strictness levels"""
    BASIC = "basic"
    STANDARD = "standard" 
    STRICT = "strict"
    PARANOID = "paranoid"

class ValidationResult(Enum):
    """Validation result status"""
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    BLOCKED = "blocked"

@dataclass
class ValidationIssue:
    """Individual validation issue"""
    level: str  # error, warning, info
    category: str  # security, performance, correctness, style
    message: str
    line_number: Optional[int] = None
    suggestion: Optional[str] = None

@dataclass
class HandlerValidationReport:
    """Complete validation report for a handler"""
    handler_name: str
    validation_level: ValidationLevel
    overall_result: ValidationResult
    issues: List[ValidationIssue]
    security_score: float  # 0-100
    performance_score: float  # 0-100
    correctness_score: float  # 0-100
    execution_time: float
    timestamp: float
    handler_hash: str
    
    def __post_init__(self):
        if not self.issues:
            self.issues = []

class HandlerValidator:
    """
    Comprehensive validation framework for AI agent handlers
    Performs static analysis, security checks, and performance validation
    """
    
    # Dangerous patterns that should be blocked
    DANGEROUS_PATTERNS = [
        'eval(', 'exec(', '__import__', 'subprocess', 'os.system',
        'open(', 'file(', 'input(', 'raw_input(',
        'compile(', 'globals()', 'locals()', 'vars()',
        'getattr(', 'setattr(', 'delattr(', 'hasattr(',
        'importlib', 'pkgutil', 'sys.modules',
        'socket.socket', 'urllib.request', 'requests.get',
        'rm -rf', 'del /f', 'format C:', 'DROP TABLE', 'DELETE FROM',
        'ALTER TABLE', 'CREATE TABLE', 'INSERT INTO'
    ]
    
    # Required imports that handlers should have
    REQUIRED_IMPORTS = [
        'typing', 'dataclasses', 'json'
    ]
    
    # Allowed imports by category
    ALLOWED_IMPORTS = {
        'basic': ['json', 'time', 'datetime', 'typing', 'dataclasses', 're', 'uuid'],
        'data': ['pandas', 'numpy', 'csv', 'openpyxl'],
        'web': ['httpx', 'aiohttp', 'fastapi', 'pydantic'],
        'ai': ['openai', 'anthropic', 'langchain'],
        'database': ['sqlalchemy', 'psycopg2', 'redis'],
        'utils': ['validators', 'python-dotenv', 'pyyaml']
    }
    
    def __init__(self, redis_url: str = None):
        self.redis = redis.from_url(redis_url) if redis_url else None
        self.validation_cache = {}
        
    async def validate_handler(
        self,
        handler_code: str,
        handler_name: str,
        validation_level: ValidationLevel = ValidationLevel.STANDARD
    ) -> HandlerValidationReport:
        """
        Perform comprehensive validation of a handler
        """
        start_time = time.time()
        
        # Calculate handler hash for caching
        handler_hash = hashlib.sha256(handler_code.encode()).hexdigest()
        
        # Check cache
        cached_result = await self._get_cached_validation(handler_hash)
        if cached_result:
            return cached_result
        
        issues = []
        
        # Parse the code
        try:
            tree = ast.parse(handler_code)
        except SyntaxError as e:
            issues.append(ValidationIssue(
                level="error",
                category="correctness",
                message=f"Syntax error: {e.msg}",
                line_number=e.lineno,
                suggestion="Fix syntax errors before validation"
            ))
            return self._create_failed_report(handler_name, validation_level, issues, handler_hash, start_time)
        
        # Perform validation checks
        await self._validate_security(tree, handler_code, issues, validation_level)
        await self._validate_performance(tree, handler_code, issues, validation_level)
        await self._validate_correctness(tree, handler_code, issues, validation_level)
        await self._validate_style(tree, handler_code, issues, validation_level)
        
        # Calculate scores
        security_score = self._calculate_security_score(issues)
        performance_score = self._calculate_performance_score(issues)
        correctness_score = self._calculate_correctness_score(issues)
        
        # Determine overall result
        overall_result = self._determine_overall_result(issues, validation_level)
        
        # Create report
        report = HandlerValidationReport(
            handler_name=handler_name,
            validation_level=validation_level,
            overall_result=overall_result,
            issues=issues,
            security_score=security_score,
            performance_score=performance_score,
            correctness_score=correctness_score,
            execution_time=time.time() - start_time,
            timestamp=time.time(),
            handler_hash=handler_hash
        )
        
        # Cache the result
        await self._cache_validation_result(handler_hash, report)
        
        return report
    
    async def validate_handler_execution(
        self,
        handler_func: Callable,
        test_params: Dict[str, Any],
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Validate handler by actually executing it with test parameters
        """
        execution_results = {
            "success": False,
            "execution_time": 0.0,
            "memory_usage": 0,
            "return_value": None,
            "errors": [],
            "warnings": []
        }
        
        start_time = time.time()
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                handler_func(test_params), 
                timeout=timeout
            )
            
            execution_results.update({
                "success": True,
                "return_value": result,
                "execution_time": time.time() - start_time
            })
            
            # Validate return value structure
            if not isinstance(result, dict):
                execution_results["warnings"].append(
                    "Handler should return a dictionary"
                )
            elif "status" not in result:
                execution_results["warnings"].append(
                    "Handler result should include 'status' field"
                )
            
        except asyncio.TimeoutError:
            execution_results["errors"].append(
                f"Handler execution timed out after {timeout}s"
            )
        except Exception as e:
            execution_results["errors"].append(
                f"Handler execution failed: {str(e)}"
            )
        finally:
            execution_results["execution_time"] = time.time() - start_time
        
        return execution_results
    
    async def validate_handler_batch(
        self,
        handlers: Dict[str, str],
        validation_level: ValidationLevel = ValidationLevel.STANDARD
    ) -> Dict[str, HandlerValidationReport]:
        """
        Validate multiple handlers in batch
        """
        results = {}
        
        # Create validation tasks
        tasks = []
        for name, code in handlers.items():
            task = self.validate_handler(code, name, validation_level)
            tasks.append((name, task))
        
        # Execute validations concurrently
        for name, task in tasks:
            try:
                results[name] = await task
            except Exception as e:
                logger.error(f"Validation failed for handler {name}: {e}")
                results[name] = self._create_failed_report(
                    name, validation_level, 
                    [ValidationIssue("error", "system", f"Validation system error: {e}")],
                    "unknown", time.time()
                )
        
        return results
    
    async def _validate_security(
        self, 
        tree: ast.AST, 
        code: str, 
        issues: List[ValidationIssue], 
        level: ValidationLevel
    ):
        """Validate security aspects of the handler"""
        
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern.lower() in code.lower():
                severity = "error" if level in [ValidationLevel.STRICT, ValidationLevel.PARANOID] else "warning"
                issues.append(ValidationIssue(
                    level=severity,
                    category="security",
                    message=f"Potentially dangerous pattern detected: {pattern}",
                    suggestion="Remove dangerous operations or use safer alternatives"
                ))
        
        # Check imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    await self._validate_import(alias.name, issues, level)
            elif isinstance(node, ast.ImportFrom):
                await self._validate_import(node.module, issues, level)
        
        # Check for hardcoded secrets
        secret_patterns = ['password', 'token', 'key', 'secret', 'api_key']
        for pattern in secret_patterns:
            if pattern in code.lower() and '=' in code:
                issues.append(ValidationIssue(
                    level="warning",
                    category="security",
                    message=f"Potential hardcoded secret: {pattern}",
                    suggestion="Use environment variables or secure credential storage"
                ))
    
    async def _validate_import(self, module_name: str, issues: List[ValidationIssue], level: ValidationLevel):
        """Validate individual import"""
        if not module_name:
            return
            
        # Check if import is in allowed list
        allowed = False
        for category, modules in self.ALLOWED_IMPORTS.items():
            if any(module_name.startswith(mod) for mod in modules):
                allowed = True
                break
        
        if not allowed and level in [ValidationLevel.STRICT, ValidationLevel.PARANOID]:
            issues.append(ValidationIssue(
                level="warning",
                category="security",
                message=f"Import not in allowed list: {module_name}",
                suggestion="Only use pre-approved modules for security"
            ))
    
    async def _validate_performance(
        self, 
        tree: ast.AST, 
        code: str, 
        issues: List[ValidationIssue], 
        level: ValidationLevel
    ):
        """Validate performance aspects"""
        
        # Check for potential performance issues
        performance_patterns = {
            'time.sleep(': "Synchronous sleep detected - use asyncio.sleep() instead",
            'while True:': "Infinite loop detected - ensure proper exit conditions",
            'for i in range(10000': "Large range loop - consider batch processing",
            'requests.get(': "Synchronous HTTP request - use httpx or aiohttp for async"
        }
        
        for pattern, message in performance_patterns.items():
            if pattern in code:
                issues.append(ValidationIssue(
                    level="warning",
                    category="performance",
                    message=message,
                    suggestion="Optimize for async execution and resource efficiency"
                ))
        
        # Check function complexity
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                complexity = self._calculate_cyclomatic_complexity(node)
                if complexity > 10:
                    issues.append(ValidationIssue(
                        level="warning",
                        category="performance",
                        message=f"High cyclomatic complexity ({complexity}) in function {node.name}",
                        suggestion="Consider breaking down complex functions"
                    ))
    
    async def _validate_correctness(
        self, 
        tree: ast.AST, 
        code: str, 
        issues: List[ValidationIssue], 
        level: ValidationLevel
    ):
        """Validate correctness aspects"""
        
        # Check for required function signatures
        has_execute_method = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == 'execute':
                has_execute_method = True
                
                # Check if it's async
                if not isinstance(node, ast.AsyncFunctionDef):
                    issues.append(ValidationIssue(
                        level="error",
                        category="correctness",
                        message="execute method should be async",
                        suggestion="Change 'def execute' to 'async def execute'"
                    ))
                
                # Check parameters
                if len(node.args.args) < 2:  # self + params
                    issues.append(ValidationIssue(
                        level="error",
                        category="correctness",
                        message="execute method should accept params argument",
                        suggestion="Add params parameter: async def execute(self, params: Dict[str, Any])"
                    ))
        
        if not has_execute_method:
            issues.append(ValidationIssue(
                level="error",
                category="correctness",
                message="Handler missing required execute method",
                suggestion="Add async def execute(self, params: Dict[str, Any]) method"
            ))
        
        # Check for proper error handling
        has_try_catch = any(isinstance(node, ast.Try) for node in ast.walk(tree))
        if not has_try_catch and level in [ValidationLevel.STRICT, ValidationLevel.PARANOID]:
            issues.append(ValidationIssue(
                level="warning",
                category="correctness",
                message="No error handling detected",
                suggestion="Add try-catch blocks for robust error handling"
            ))
    
    async def _validate_style(
        self, 
        tree: ast.AST, 
        code: str, 
        issues: List[ValidationIssue], 
        level: ValidationLevel
    ):
        """Validate style and best practices"""
        
        lines = code.split('\n')
        
        # Check line length
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                issues.append(ValidationIssue(
                    level="info",
                    category="style",
                    message=f"Line {i} exceeds 120 characters",
                    line_number=i,
                    suggestion="Break long lines for better readability"
                ))
        
        # Check for type hints
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if not node.returns and level in [ValidationLevel.STRICT, ValidationLevel.PARANOID]:
                    issues.append(ValidationIssue(
                        level="info",
                        category="style",
                        message=f"Function {node.name} missing return type hint",
                        suggestion="Add return type annotations for better code documentation"
                    ))
    
    def _calculate_cyclomatic_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of a function"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity
    
    def _calculate_security_score(self, issues: List[ValidationIssue]) -> float:
        """Calculate security score (0-100)"""
        security_issues = [i for i in issues if i.category == "security"]
        if not security_issues:
            return 100.0
        
        penalty = 0
        for issue in security_issues:
            if issue.level == "error":
                penalty += 30
            elif issue.level == "warning":
                penalty += 10
            else:
                penalty += 5
        
        return max(0, 100 - penalty)
    
    def _calculate_performance_score(self, issues: List[ValidationIssue]) -> float:
        """Calculate performance score (0-100)"""
        performance_issues = [i for i in issues if i.category == "performance"]
        if not performance_issues:
            return 100.0
        
        penalty = sum(15 if i.level == "error" else 8 if i.level == "warning" else 3 for i in performance_issues)
        return max(0, 100 - penalty)
    
    def _calculate_correctness_score(self, issues: List[ValidationIssue]) -> float:
        """Calculate correctness score (0-100)"""
        correctness_issues = [i for i in issues if i.category == "correctness"]
        if not correctness_issues:
            return 100.0
        
        penalty = sum(25 if i.level == "error" else 10 if i.level == "warning" else 5 for i in correctness_issues)
        return max(0, 100 - penalty)
    
    def _determine_overall_result(self, issues: List[ValidationIssue], level: ValidationLevel) -> ValidationResult:
        """Determine overall validation result"""
        error_count = len([i for i in issues if i.level == "error"])
        warning_count = len([i for i in issues if i.level == "warning"])
        
        if error_count > 0:
            return ValidationResult.FAILED
        
        if level == ValidationLevel.PARANOID and warning_count > 0:
            return ValidationResult.BLOCKED
        
        if level == ValidationLevel.STRICT and warning_count > 3:
            return ValidationResult.BLOCKED
        
        if warning_count > 0:
            return ValidationResult.WARNING
        
        return ValidationResult.PASSED
    
    def _create_failed_report(
        self, 
        handler_name: str, 
        validation_level: ValidationLevel, 
        issues: List[ValidationIssue], 
        handler_hash: str, 
        start_time: float
    ) -> HandlerValidationReport:
        """Create a failed validation report"""
        return HandlerValidationReport(
            handler_name=handler_name,
            validation_level=validation_level,
            overall_result=ValidationResult.FAILED,
            issues=issues,
            security_score=0.0,
            performance_score=0.0,
            correctness_score=0.0,
            execution_time=time.time() - start_time,
            timestamp=time.time(),
            handler_hash=handler_hash
        )
    
    async def _get_cached_validation(self, handler_hash: str) -> Optional[HandlerValidationReport]:
        """Get cached validation result"""
        if not self.redis:
            return None
        
        cache_key = f"handler_validation:{handler_hash}"
        cached_data = await self.redis.get(cache_key)
        
        if cached_data:
            data = json.loads(cached_data)
            return HandlerValidationReport(**data)
        
        return None
    
    async def _cache_validation_result(self, handler_hash: str, report: HandlerValidationReport):
        """Cache validation result"""
        if not self.redis:
            return
        
        cache_key = f"handler_validation:{handler_hash}"
        cache_data = json.dumps(asdict(report), default=str)
        
        # Cache for 24 hours
        await self.redis.setex(cache_key, 86400, cache_data)