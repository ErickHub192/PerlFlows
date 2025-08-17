"""
Carl - Traductor de respuestas técnicas a conversación natural
Solo traduce, NO hace planning ni trabajo pesado
"""
import logging
from typing import Dict, Any
from app.ai.llm_clients.llm_service import LLMService
from app.core.config import settings
from app.workflow_engine.constants.workflow_statuses import WorkflowStatus

logger = logging.getLogger(__name__)

class CarlTranslatorService:
    """
    Carl - Traductor conversacional que usa gpt-4o-mini
    Recibe respuestas estructuradas de Kyra y las traduce a lenguaje natural
    NO hace planning, discovery, OAuth ni nada pesado - solo traduce
    """
    
    def __init__(self):
        # Carl usa cliente directo sin validación JSON
        from openai import AsyncOpenAI
        self.carl_client = AsyncOpenAI(api_key=settings.LLM_API_KEY)
        self.model = "gpt-4o-mini"
    
    async def translate_kyra_response(
        self, 
        kyra_response: Dict[str, Any], 
        user_message: str
    ) -> str:
        """
        Traduce cualquier respuesta de Kyra a conversación natural
        Kyra ya hizo todo el trabajo pesado, Carl solo traduce
        """
        
        # Detectar tipo de respuesta de Kyra
        has_clarification = self._has_clarification_step(kyra_response)
        has_workflow = kyra_response.get("steps") and len(kyra_response.get("steps", [])) > 1
        has_oauth = kyra_response.get("oauth_requirements") or kyra_response.get("needs_oauth")
        has_errors = kyra_response.get("errors") or kyra_response.get("status") == "error"
        is_workflow_review = kyra_response.get("status") == WorkflowStatus.WORKFLOW_READY_FOR_REVIEW
        
        # 🚫 DISABLED: Workflow management statuses - now handled by buttons
        # is_save_workflow = kyra_response.get("status") == WorkflowStatus.SAVE_WORKFLOW
        # is_activate_workflow = kyra_response.get("status") == WorkflowStatus.ACTIVATE_WORKFLOW
        # is_execute_workflow = kyra_response.get("status") == WorkflowStatus.EXECUTE_WORKFLOW
        is_save_workflow = False
        is_activate_workflow = False
        is_execute_workflow = False
        
        # 🎯 SPECIAL CASE: workflow_ready_for_review - Format complete workflow review
        if is_workflow_review:
            workflow_summary = kyra_response.get("workflow_summary", {})
            approval_message = kyra_response.get("approval_message", "")
            main_message = kyra_response.get("message", "")
            
            # 🎯 BUILD COMPLETE WORKFLOW REVIEW MESSAGE
            if workflow_summary or approval_message or main_message:
                review_message_parts = []
                
                # Add main message
                if main_message:
                    review_message_parts.append(main_message)
                
                # Add structured workflow summary with NEW detailed format
                if workflow_summary:
                    title = workflow_summary.get("title", "Tu Workflow")
                    description = workflow_summary.get("description", "")
                    trigger_data = workflow_summary.get("trigger", {})
                    flow_steps = workflow_summary.get("flow_steps", [])
                    connections = workflow_summary.get("connections", "")
                    final_outcome = workflow_summary.get("final_outcome", "")
                    estimated_time = workflow_summary.get("estimated_time", "")
                    
                    # Legacy support for old format
                    if isinstance(trigger_data, str):
                        trigger_text = trigger_data
                    else:
                        trigger_service = trigger_data.get("service", "")
                        trigger_event = trigger_data.get("event", "")
                        trigger_desc = trigger_data.get("description", "")
                        trigger_text = f"{trigger_service}: {trigger_event}" if trigger_service and trigger_event else trigger_desc
                    
                    summary_text = f"\n\n📋 **{title}**"
                    if description:
                        summary_text += f"\n{description}"
                    
                    if trigger_text:
                        summary_text += f"\n\n⏰ **Cuándo se ejecuta:** {trigger_text}"
                    
                    # NEW: Detailed flow steps
                    if flow_steps:
                        summary_text += f"\n\n🎯 **Cómo funciona paso a paso:**"
                        for step in flow_steps:
                            step_num = step.get("step", "")
                            service = step.get("service", "")
                            action = step.get("action", "")
                            desc = step.get("description", "")
                            params = step.get("key_params", "")
                            
                            step_text = f"\n**{step_num}.** {service} - {action}"
                            if desc:
                                step_text += f"\n   • {desc}"
                            if params:
                                step_text += f"\n   • Configuración: {params}"
                            
                            summary_text += step_text
                    # Legacy support for old actions format
                    elif workflow_summary.get("actions"):
                        actions = workflow_summary.get("actions", [])
                        actions_text = "\n".join([f"• {action}" for action in actions])
                        summary_text += f"\n\n🎯 **Qué hace:**\n{actions_text}"
                    
                    if connections:
                        summary_text += f"\n\n🔗 **Flujo:** {connections}"
                    
                    if final_outcome:
                        summary_text += f"\n\n✨ **Resultado final:** {final_outcome}"
                    
                    if estimated_time:
                        summary_text += f"\n\n⚡ **Tiempo estimado:** {estimated_time}"
                    
                    review_message_parts.append(summary_text)
                
                # Add approval question
                if approval_message:
                    review_message_parts.append(f"\n\n{approval_message}")
                elif not approval_message and workflow_summary:
                    review_message_parts.append("\n\n¿Te parece bien este workflow? Puedes decirme si quieres modificar algo o si está listo para ejecutar. ✨")
                
                complete_message = "".join(review_message_parts)
                logger.info("🎯 CARL: Generated complete workflow review message")
                return complete_message
            else:
                logger.warning("🎯 CARL: workflow_ready_for_review detected but no workflow data found - proceeding with translation")
        
        # 🆕 SPECIAL CASES: Workflow management decisions
        elif is_save_workflow:
            workflow_name = kyra_response.get("workflow_name", "tu workflow")
            return f"✅ **Workflow guardado exitosamente!**\n\nTu workflow '{workflow_name}' ha sido guardado en tu biblioteca. Puedes activarlo más tarde cuando quieras que se ejecute automáticamente, o ejecutarlo manualmente cuando lo necesites.\n\n💡 **Comandos útiles:**\n• `mis workflows` - Ver todos tus workflows\n• `activar {workflow_name}` - Activar para ejecución automática\n• `ejecuta {workflow_name}` - Ejecutar ahora"
        
        elif is_activate_workflow:
            workflow_name = kyra_response.get("workflow_name", "tu workflow")
            return f"🟢 **Workflow activado y guardado!**\n\nTu workflow '{workflow_name}' está ahora activo y se ejecutará automáticamente según sus triggers configurados. También lo puedes ejecutar manualmente cuando quieras.\n\n💡 **Comandos útiles:**\n• `mis workflows` - Ver el estado de tus workflows\n• `ejecuta {workflow_name}` - Ejecutar manualmente\n• `desactivar {workflow_name}` - Desactivar si es necesario"
        
        elif is_execute_workflow:
            workflow_name = kyra_response.get("workflow_name", "tu workflow")
            execution_id = kyra_response.get("execution_id", "")
            execution_info = f"ID de ejecución: {execution_id}" if execution_id else ""
            return f"🚀 **Ejecutando workflow ahora!**\n\nTu workflow '{workflow_name}' se está ejecutando en este momento. {execution_info}\n\nPuedes monitorear el progreso y ver los resultados en tu dashboard de workflows.\n\n💡 **Tip:** Este workflow también está disponible para futuras ejecuciones con el comando `ejecuta {workflow_name}`"
        
        # Construir prompt base para Carl
        prompt = f"""Eres Carl, un traductor conversacional amigable.

Tu único trabajo es traducir respuestas técnicas de Kyra (el agente de automatización) a conversación natural.

REGLAS IMPORTANTES:
1. Habla como si fueras un amigo técnico que ayuda
2. Usa emojis moderadamente (no te pases)  
3. Sé conciso pero amigable
4. NO expliques detalles técnicos innecesarios
5. Si hay opciones para elegir, pregunta de forma natural
6. Si hay éxito, celebra brevemente y explica qué sigue

CONTEXTO:
- Usuario pidió: "{user_message}"
- Kyra respondió con: {self._extract_key_info(kyra_response)}

INSTRUCCIONES ESPECÍFICAS:"""

        if has_errors:
            prompt += """
- Kyra tuvo un error
- Traduce el error de forma amigable
- Sugiere que el usuario intente de nuevo o sea más específico"""
            
        elif has_clarification:
            prompt += """
- Kyra encontró varias opciones similares  
- Explica brevemente que encontraste opciones
- Pregunta cuál prefiere de forma natural
- NO menciones detalles técnicos como node_id"""
            
        elif has_oauth:
            prompt += """
- Kyra creó un workflow pero necesita permisos/autenticación
- Explica que necesitas conectar servicios
- Mantén tono positivo: "casi listo, solo necesito conectar X"""
            
        elif has_workflow:
            prompt += """
- Kyra creó un workflow exitoso
- Celebra el éxito brevemente
- Explica qué se creó en términos simples
- Ofrece opciones: revisar, modificar, ejecutar"""
            
        else:
            prompt += """
- Respuesta general de Kyra
- Traduce de forma natural y amigable
- Mantén la información importante"""

        prompt += """

FORMATO DE RESPUESTA:
- SOLO el mensaje conversacional
- Sin JSON, sin estructura técnica
- Como si fueras un amigo hablando por WhatsApp"""

        try:
            logger.info(f"🤖 CARL: Calling gpt-4o-mini for translation...")
            
            # Usar cliente directo para obtener texto plano (no JSON)
            messages = [{"role": "system", "content": prompt}]
            response = await self.carl_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.8
            )
            
            # Extraer contenido de la respuesta de OpenAI
            natural_message = response.choices[0].message.content
            
            logger.info(f"✅ CARL SUCCESS: Generated natural message")
            return natural_message.strip()
            
        except Exception as e:
            logger.error(f"❌ CARL FAILED: {e}")
            return "🤔 Encontré varias opciones. ¿Cuál te gusta más? [CARL ERROR FALLBACK]"
    
    def _has_clarification_step(self, kyra_response: Dict[str, Any]) -> bool:
        """Detecta si hay step de clarificación"""
        steps = kyra_response.get("steps", [])
        return any(
            step.get("action_name") == "request_clarification" 
            for step in steps
        )
    
    def _extract_key_info(self, kyra_response: Dict[str, Any]) -> str:
        """Extrae info clave de la respuesta de Kyra para el prompt"""
        info = {}
        
        if kyra_response.get("steps"):
            info["steps_count"] = len(kyra_response["steps"])
            
        if kyra_response.get("confidence"):
            info["confidence"] = kyra_response["confidence"]
            
        if kyra_response.get("oauth_requirements"):
            info["needs_oauth"] = True
            
        if kyra_response.get("errors"):
            info["has_errors"] = True
            
        # Extraer servicios similares si los hay
        for step in kyra_response.get("steps", []):
            if step.get("action_name") == "request_clarification":
                similar_services = step.get("params", {}).get("similar_services", [])
                if similar_services:
                    options = []
                    for group in similar_services:
                        for option in group.get("options", []):
                            options.append(option.get("name", ""))
                    info["service_options"] = options
                    break
        
        return str(info)
    
    def _fallback_translation(self, kyra_response: Dict[str, Any], user_message: str) -> str:
        """Fallback manual si Carl falla"""
        if self._has_clarification_step(kyra_response):
            return "¡Perfecto! 🎯 Encontré varias opciones excelentes para esto. ¿Cuál prefieres?"
            
        elif kyra_response.get("steps"):
            steps_count = len(kyra_response["steps"])
            return f"¡Listo! ✅ Creé un workflow de {steps_count} pasos para ti. ¿Quieres revisarlo?"
            
        elif kyra_response.get("errors"):
            return "🤔 Hmm, algo no salió como esperaba. ¿Puedes intentar ser un poco más específico?"
            
        else:
            return "¡Perfecto! Ya tengo todo listo. ¿Qué quieres hacer ahora?"
    
    def _fallback_clarification_message_from_response(self, response: dict) -> str:
        """
        Crear mensaje de clarification desde respuesta inesperada del LLM
        """
        service_groups = response.get("service_groups", [])
        if not service_groups:
            return "🤔 Encontré varias opciones. ¿Cuál prefieres?"
        
        first_group = service_groups[0]
        options = first_group.get("options", [])
        
        if len(options) >= 2:
            opt1, opt2 = options[0], options[1]
            return f"¡Perfecto! 🎯 Encontré dos servicios geniales:\n\n" \
                   f"✨ {opt1.get('name', 'Opción 1')} - {opt1.get('description', '')}\n" \
                   f"📧 {opt2.get('name', 'Opción 2')} - {opt2.get('description', '')}\n\n" \
                   f"¿Cuál prefieres usar?"
        
        return "🎯 Encontré varias opciones excelentes para esto. ¿Cuál te gusta más?"

# Factory function
def get_carl_translator() -> CarlTranslatorService:
    """Factory para obtener instancia de Carl"""
    return CarlTranslatorService()