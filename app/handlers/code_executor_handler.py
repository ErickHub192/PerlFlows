"""
Code Executor Handler - Para workflows normales de Kyra
Similar a n8n Code Node para formateo y transformación de datos
"""
import asyncio
import ast
import sys
import time
import io
import contextlib
import traceback
import logging
from typing import Dict, Any, List, Optional
from uuid import uuid4
import tempfile
import os
import json
from dataclasses import dataclass

from .connector_handler import ActionHandler
from app.connectors.factory import register_node, register_tool
from app.exceptions.api_exceptions import HandlerError

logger = logging.getLogger(__name__)

@dataclass
class CodeExecutionResult:
    """Resultado de ejecución de código"""
    success: bool
    result: Any = None
    output: str = ""
    error: str = ""
    execution_time: float = 0.0
    variables: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.variables is None:
            self.variables = {}

@register_node("Code.execute")
@register_tool("Code.execute")
class CodeExecutorHandler(ActionHandler):
    """
    Handler para ejecución de código Python en workflows de Kyra
    
    Uso común:
    - Formatear datos de un nodo para el siguiente
    - Transformar respuestas de APIs
    - Cálculos y procesamiento de datos
    - Lógica condicional avanzada
    
    Más permisivo que el AGI handler pero aún seguro
    """
    
    def __init__(self, creds: Dict[str, Any]):
        super().__init__(creds)
        
        # Bibliotecas permitidas (más amplio que AGI)
        self.allowed_imports = {
            # Básicas
            'json', 'math', 'datetime', 'time', 'random', 're', 'urllib.parse',
            'collections', 'itertools', 'functools', 'operator', 'statistics',
            'decimal', 'fractions', 'base64', 'hashlib', 'uuid', 'csv',
            
            # Para datos
            'pandas', 'numpy', 'requests', 'xml.etree.ElementTree',
            
            # Para texto y strings
            'string', 'textwrap', 'unicodedata',
            
            # Para fechas
            'calendar', 'dateutil',
        }
        
        # Funciones built-in permitidas (más permisivo)
        self.allowed_builtins = {
            'abs', 'all', 'any', 'bool', 'dict', 'enumerate', 'filter', 'float',
            'int', 'len', 'list', 'map', 'max', 'min', 'range', 'reversed',
            'round', 'set', 'sorted', 'str', 'sum', 'tuple', 'zip', 'chr', 'ord',
            'isinstance', 'type', 'hasattr', 'getattr', 'setattr', 'delattr',
            'slice', 'format', 'repr', 'print', 'input'  # Permitir print e input para workflows
        }
        
        # Patrones prohibidos (más relajado para workflows)
        self.forbidden_patterns = [
            # System access crítico
            'import os', 'import sys', 'import subprocess', 'import socket',
            'import shutil', '__import__', 'importlib',
            
            # Code execution peligroso
            'eval(', 'exec(', 'compile(',
            
            # File operations sin control
            'open(', 'file(',
            
            # Process/thread operations
            'threading', 'multiprocessing', 'subprocess',
            'os.system', 'os.popen',
            
            # Exit/quit
            'exit(', 'quit(', 'sys.exit', 'os._exit'
        ]
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta código Python para workflows
        
        Parameters:
        - code: Código Python a ejecutar
        - input_data: Datos de entrada del workflow (disponibles como 'input_data')
        - variables: Variables adicionales disponibles en el contexto
        - return_variable: Nombre de la variable a retornar (default: 'result')
        - timeout: Timeout en segundos (default: 30)
        """
        start_time = time.time()
        
        try:
            # Extraer parámetros
            code = params.get("code", "")
            input_data = params.get("input_data", {})
            variables = params.get("variables", {})
            return_variable = params.get("return_variable", "result")
            timeout = min(params.get("timeout", 30), 120)  # Máximo 2 minutos
            
            if not code.strip():
                raise HandlerError("No code provided for execution")
            
            # Validar código básico
            security_check = self._validate_code_safety(code)
            if not security_check["safe"]:
                raise HandlerError(f"Unsafe code detected: {', '.join(security_check['violations'])}")
            
            # Ejecutar código
            execution_result = await self._execute_code_safely(
                code, input_data, variables, return_variable, timeout
            )
            
            # Preparar respuesta
            result_data = execution_result.result
            
            # Si el resultado es None, intentar obtener variables modificadas
            if result_data is None and execution_result.variables:
                # Buscar variables que podrían ser el resultado
                potential_results = {k: v for k, v in execution_result.variables.items() 
                                   if not k.startswith('_') and k not in ['input_data', 'variables']}
                if len(potential_results) == 1:
                    result_data = list(potential_results.values())[0]
                elif potential_results:
                    result_data = potential_results
            
            return {
                "status": "success",
                "data": {
                    "result": result_data,
                    "output": execution_result.output,
                    "variables": execution_result.variables,
                    "execution_time": execution_result.execution_time
                },
                "metadata": {
                    "code_length": len(code),
                    "total_time": time.time() - start_time,
                    "return_variable": return_variable
                },
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Code execution failed: {e}")
            return {
                "status": "error",
                "data": None,
                "error": f"Code execution failed: {str(e)}",
                "metadata": {
                    "total_time": time.time() - start_time
                }
            }
    
    def _validate_code_safety(self, code: str) -> Dict[str, Any]:
        """Validación básica de seguridad del código"""
        violations = []
        
        # Check forbidden patterns
        for pattern in self.forbidden_patterns:
            if pattern in code:
                violations.append(f"Forbidden pattern: {pattern}")
        
        # Check for obvious infinite loops
        if "while True:" in code and "break" not in code:
            violations.append("Potential infinite loop: while True without break")
        
        # Check imports básico
        lines = code.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                try:
                    # Extract module name
                    if line.startswith('import '):
                        module = line.split()[1].split('.')[0]
                    else:  # from import
                        module = line.split()[1].split('.')[0]
                    
                    if module not in self.allowed_imports:
                        violations.append(f"Unauthorized import: {module}")
                except:
                    violations.append(f"Could not parse import: {line}")
        
        return {
            "safe": len(violations) == 0,
            "violations": violations,
            "risk_level": "high" if len(violations) > 2 else "medium" if len(violations) > 0 else "low"
        }
    
    async def _execute_code_safely(
        self, 
        code: str, 
        input_data: Any, 
        variables: Dict[str, Any],
        return_variable: str,
        timeout: int
    ) -> CodeExecutionResult:
        """Ejecuta el código de forma segura"""
        start_time = time.time()
        
        try:
            # Preparar contexto de ejecución
            execution_context = {
                '__builtins__': {name: getattr(__builtins__, name) for name in self.allowed_builtins 
                               if hasattr(__builtins__, name)},
                'input_data': input_data,
                'variables': variables.copy() if variables else {},
                return_variable: None
            }
            
            # Agregar módulos permitidos
            for module_name in self.allowed_imports:
                try:
                    if module_name == 'pandas':
                        try:
                            import pandas as pd
                            execution_context['pd'] = pd
                            execution_context['pandas'] = pd
                        except ImportError:
                            pass
                    elif module_name == 'numpy':
                        try:
                            import numpy as np
                            execution_context['np'] = np
                            execution_context['numpy'] = np
                        except ImportError:
                            pass
                    elif module_name == 'requests':
                        try:
                            import requests
                            execution_context['requests'] = requests
                        except ImportError:
                            pass
                    else:
                        execution_context[module_name] = __import__(module_name)
                except ImportError:
                    pass  # Módulo no disponible, continuar
            
            # Capturar output
            captured_output = io.StringIO()
            
            # Ejecutar con timeout
            try:
                with contextlib.redirect_stdout(captured_output):
                    # Simple timeout usando asyncio
                    await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None,
                            self._execute_in_context,
                            code,
                            execution_context
                        ),
                        timeout=timeout
                    )
                
                # Obtener resultado
                result = execution_context.get(return_variable)
                output = captured_output.getvalue()
                
                # Obtener variables finales (excluyendo las internas)
                final_variables = {k: v for k, v in execution_context.items() 
                                 if not k.startswith('__') and k not in ['input_data', 'variables']}
                
                return CodeExecutionResult(
                    success=True,
                    result=result,
                    output=output,
                    execution_time=time.time() - start_time,
                    variables=final_variables
                )
                
            except asyncio.TimeoutError:
                return CodeExecutionResult(
                    success=False,
                    error=f"Code execution timeout after {timeout} seconds",
                    execution_time=timeout
                )
                
        except Exception as e:
            return CodeExecutionResult(
                success=False,
                error=f"Execution error: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def _execute_in_context(self, code: str, context: Dict[str, Any]):
        """Ejecuta el código en el contexto dado"""
        exec(code, context)


# Función auxiliar para uso directo en workflows
async def execute_workflow_code(
    code: str,
    input_data: Any = None,
    variables: Dict[str, Any] = None,
    return_variable: str = "result",
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Función auxiliar para ejecutar código en workflows
    
    Ejemplo de uso:
    ```python
    # Formatear datos de una API
    code = '''
    # input_data contiene la respuesta de la API anterior
    formatted_data = []
    for item in input_data.get('items', []):
        formatted_data.append({
            'name': item['name'].title(),
            'price': round(float(item['price']), 2),
            'available': item.get('in_stock', False)
        })
    
    result = {
        'total_items': len(formatted_data),
        'items': formatted_data
    }
    '''
    
    result = await execute_workflow_code(
        code=code,
        input_data=api_response,
        return_variable="result"
    )
    ```
    """
    executor = CodeExecutorHandler({})
    
    params = {
        "code": code,
        "input_data": input_data,
        "variables": variables or {},
        "return_variable": return_variable,
        "timeout": timeout
    }
    
    return await executor.execute(params)