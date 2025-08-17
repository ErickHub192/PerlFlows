# app/ai/tool_executor.py

import time
import logging
from typing import Any, Dict
from uuid import UUID

from app.ai.llm_clients.tool_router import ToolRouter
from app.ai.memories.manager import MemoryManager
from app.exceptions import get_kyra_logger, ToolExecutionError

logger = get_kyra_logger(__name__)


class ToolExecutor:
    """
    Ejecuta todos los pasos de herramientas que devuelve el LLM,
    actualiza memoria corta y, si existe, reinyecta resultados al LLM.
    """

    def __init__(
        self,
        tool_router: ToolRouter,
        mem_mgr: MemoryManager,
        llm: Any,
    ):
        logger.info("TOOL_EXECUTOR: Inicializando ToolExecutor")
        self.tool_router = tool_router
        self.mem_mgr = mem_mgr
        self.llm = llm
        logger.debug("TOOL_EXECUTOR: ToolExecutor inicializado correctamente")

    async def execute(
        self,
        agent_id: UUID,
        llm_response: Dict[str, Any],
        creds: Dict[str, Any],
    ) -> Dict[str, Any]:
        logger.info(f"TOOL_EXECUTOR: Iniciando ejecución de herramientas para agent_id: {agent_id}")
        start = time.perf_counter()
        
        steps = llm_response.get("steps", [])
        logger.info(f"TOOL_EXECUTOR: Ejecutando {len(steps)} pasos de herramientas")
        
        # Recorremos cada paso planificado por el LLM
        for i, step in enumerate(steps):
            tool_name = step.get("tool")
            params = step.get("params", {})
            
            logger.info(f"TOOL_EXECUTOR: Ejecutando paso {i+1}/{len(steps)} - tool: {tool_name}")
            logger.debug(f"TOOL_EXECUTOR: Parámetros del tool {tool_name}: {params}")

            # 1) Llamada a la herramienta
            try:
                logger.debug(f"TOOL_EXECUTOR: Llamando al tool_router para: {tool_name}")
                result = await self.tool_router.call(tool_name, params, creds)
                logger.info(f"TOOL_EXECUTOR: Tool {tool_name} ejecutado exitosamente")
                logger.debug(f"TOOL_EXECUTOR: Resultado del tool {tool_name}: {str(result)[:200]}")
                
            except Exception as e:
                logger.error(f"Error ejecutando tool {tool_name}", error=e, tool_params=params)
                # Si falla, abortamos toda la ejecución
                raise ToolExecutionError(tool_name, str(e), params)

            # 2) Guardar en memoria corta (ignorar errores aquí)
            try:
                logger.debug(f"TOOL_EXECUTOR: Guardando resultado en memoria corta para agent_id: {agent_id}")
                await self.mem_mgr.append_short_term(agent_id, {
                    "tool": tool_name,
                    "params": params,
                    "result": result,
                })
                logger.debug(f"TOOL_EXECUTOR: Resultado guardado en memoria corta")
            except Exception as e:
                logger.warning(f"TOOL_EXECUTOR: Error guardando en memoria corta: {str(e)}")
                pass

            # 3) Reinyectar el resultado en la respuesta del LLM (si está soportado)
            if hasattr(self.llm, "inject_tool_result"):
                try:
                    logger.debug(f"TOOL_EXECUTOR: Reinyectando resultado del tool {tool_name} al LLM")
                    llm_response = await self.llm.inject_tool_result(llm_response, result)
                except Exception as e:
                    logger.warning(f"TOOL_EXECUTOR: Error reinyectando resultado al LLM: {str(e)}")
                    pass

        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info(f"TOOL_EXECUTOR: Ejecución de herramientas completada en {duration_ms}ms para agent_id: {agent_id}")
        
        # Opcional: podrías medir aquí el tiempo total y añadir a llm_response si te interesa
        llm_response["_tools_duration_ms"] = duration_ms
        return llm_response
