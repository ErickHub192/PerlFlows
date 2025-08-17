import json
import logging
from typing import List, Any

from app.core.config import settings
from app.exceptions import get_kyra_logger, PlannerError

logger = get_kyra_logger(__name__)

_DEFAULT_PROMPT = (
    "Eres un planificador que decide la secuencia de herramientas a ejecutar."\
    " Devuelve exclusivamente un JSON con la lista ordenada de herramientas"\
    " a usar para cumplir el objetivo dado."
)

class Planner:
    """LLM based planner that returns an ordered list of tool names."""

    def __init__(self, llm: Any | None = None):
        logger.info("PLANNER: Inicializando planner")
        if llm is None:
            logger.debug("PLANNER: Creando cliente LLM con modelo: %s", settings.DEFAULT_LLM_MODEL)
            from app.ai.llm_factory import create as create_llm_client
            llm = create_llm_client(
                api_key=settings.LLM_API_KEY,
                model=settings.DEFAULT_LLM_MODEL,
            )
        self.llm = llm
        logger.info("PLANNER: Planner inicializado exitosamente")

    async def plan(self, goal: str, available_tools: List[str]) -> List[str]:
        """Generate a plan using the underlying LLM."""
        logger.info("PLANNER: Iniciando planificación para objetivo: %s", goal[:100] if len(goal) > 100 else goal)
        logger.debug("PLANNER: Herramientas disponibles: %d", len(available_tools))
        logger.debug("PLANNER: Lista de herramientas: %s", available_tools)
        
        try:
            tools_str = ", ".join(available_tools)
            messages = [
                {"role": "system", "content": _DEFAULT_PROMPT},
                {
                    "role": "user",
                    "content": f"Goal: {goal}\nAvailable tools: {tools_str}"
                },
            ]
            
            logger.debug("PLANNER: Enviando petición al LLM para planificación")
            resp = await self.llm.chat_completion(messages=messages, temperature=0.0)
            
            content = getattr(resp.choices[0].message, "content", "")
            logger.debug("PLANNER: Respuesta del LLM recibida: %s", content[:200] if len(content) > 200 else content)
            
            try:
                steps = json.loads(content)
                if not isinstance(steps, list):
                    logger.error("PLANNER: El plan devuelto no es una lista: %s", type(steps))
                    raise ValueError("Plan debe ser una lista")
                
                logger.info("PLANNER: Plan generado exitosamente con %d pasos: %s", len(steps), steps)
                return [str(s) for s in steps]
                
            except json.JSONDecodeError as e:
                logger.error("Error al parsear JSON del plan", error=e, content_preview=content[:100])
                raise PlannerError(
                    f"Formato de plan inválido - JSON malformado: {e}",
                    goal=goal,
                    available_tools=available_tools
                )
                
        except PlannerError:
            # Re-raise PlannerError (ya tiene logging automático)
            raise
        except Exception as e:
            logger.error("Error durante planificación", error=e, goal=goal[:100])
            raise PlannerError(
                f"Error en planificación: {e}",
                goal=goal,
                available_tools=available_tools
            )
