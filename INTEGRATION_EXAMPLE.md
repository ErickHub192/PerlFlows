# 🎯 TOKEN TRACKING - GUÍA DE INTEGRACIÓN

## ✅ Sistema Listo Para Usar

El sistema de token tracking está **completamente configurado** y **listo para usar**. Solo necesitas agregar **2 líneas de código** en tus servicios existentes.

## 🚀 Integración en ChatService

### Antes (código actual):
```python
# app/services/chat_service_clean.py
async def handle_message(self, chat_id, user_message, user_id, context=None, db_session=None):
    # Tu código existente...
    
    # Llamada LLM sin tracking
    result = await self.llm.run(
        system_prompt=prompt,
        short_term=short_term,
        long_term=long_term,
        user_prompt=user_message
    )
    
    return ChatResponseModel(reply=result["final_output"])
```

### Después (con auto-tracking):
```python
# app/services/chat_service_clean.py
from app.ai.llm_clients.llm_service import token_tracking_context  # ← Agregar import

async def handle_message(self, chat_id, user_message, user_id, context=None, db_session=None):
    # ← Agregar context manager
    async with token_tracking_context(
        user_id=user_id,
        operation_type="chat", 
        workflow_id=str(chat_id)
    ):
        # Todo tu código existente aquí - SIN CAMBIOS
        result = await self.llm.run(
            system_prompt=prompt,
            short_term=short_term,
            long_term=long_term,
            user_prompt=user_message
        )
        
        # 📊 ← Tokens automáticamente tracked!
        
        return ChatResponseModel(reply=result["final_output"])
```

## 🚀 Integración en WorkflowRunner

### Para WorkflowRunnerService:
```python
# app/services/workflow_runner_service.py
from app.ai.llm_clients.llm_service import token_tracking_context

async def run_workflow(self, flow_id, steps, user_id, inputs, simulate=False):
    # ← Agregar context para todo el workflow
    async with token_tracking_context(
        user_id=user_id,
        operation_type="workflow",
        workflow_id=str(flow_id),
        execution_id=str(execution_id)
    ):
        # Todo tu código de workflow existente
        # Cualquier call LLM interno será tracked automáticamente
        return await self._execute_workflow_steps(steps)
```

## 🚀 Integración en AI Agents

### Para AIAgentService:
```python
# app/services/ai_agent_service.py  
from app.ai.llm_clients.llm_service import token_tracking_context

async def execute_agent(self, agent_id, prompt, user_id):
    async with token_tracking_context(
        user_id=user_id,
        operation_type="ai_agent",
        workflow_id=str(agent_id)
    ):
        # Tu lógica de AI agent
        # Todos los LLM calls serán tracked
        return await self._run_agent_logic(prompt)
```

## 📊 Verificar Límites (Opcional)

### Si quieres verificar límites antes de ejecutar:
```python
from app.core.token_system import get_token_manager

async def handle_message(self, chat_id, user_message, user_id):
    # Verificar límites primero (opcional)
    token_manager = get_token_manager()
    status = await token_manager.can_use_tokens(user_id, estimated_tokens=2000)
    
    if not status.can_use:
        return ChatResponseModel(
            reply=f"❌ Límite de tokens alcanzado. Remaining: {status.remaining_tokens}",
            finalize=True
        )
    
    # Proceder con tracking automático
    async with token_tracking_context(user_id=user_id, operation_type="chat"):
        # Tu código LLM...
```

## 🎯 Lo Que Se Registra Automáticamente

Cada vez que se ejecuta código dentro del `token_tracking_context()`:

✅ **Input tokens** (prompt enviado)  
✅ **Output tokens** (respuesta recibida)  
✅ **Modelo usado** (gpt-4.1, gpt-4o, etc.)  
✅ **Costo calculado** (based on current pricing)  
✅ **User ID, Workflow ID, Execution ID**  
✅ **Timestamp y metadata**  

## 📈 Analytics Disponibles

El sistema automáticamente genera:

- **Uso por usuario/mes** 
- **Tokens por workflow**
- **Costos por operación**
- **Alertas de límites** (80%, 90%, 100%)
- **Top workflows que más consumen**
- **Tendencias de uso diario**

## 🚨 Alertas Automáticas

El sistema envía alertas automáticamente cuando:

- Usuario usa 80% de sus tokens → Email/notificación  
- Usuario usa 90% de sus tokens → Warning  
- Usuario alcanza 100% → Bloqueo suave  

## 🔧 Configuración

### Development (automático):
- Batch size: 5 tokens per batch
- Alertas: Solo in-app notifications

### Production (automático):  
- Batch size: 20 tokens per batch
- Alertas: Email + webhooks + in-app

## ✅ Ready to Use!

1. **Sistema inicializado** ✅ en startup
2. **Tablas creadas** ✅ con migración  
3. **Interceptor activo** ✅ en LLMService
4. **Solo agregar context manager** ✅ en tus servicios

**2 líneas de código = Token tracking completo** 🎉