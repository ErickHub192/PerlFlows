# app/examples/token_tracking_usage.py

"""
🎯 EJEMPLOS DE USO DEL SISTEMA DE TOKEN TRACKING AUTOMÁTICO

El sistema intercepta AUTOMÁTICAMENTE todos los tokens del LLM sin modificar código existente.
Solo necesitas establecer el contexto antes de usar el LLM.
"""

import asyncio
from uuid import uuid4
from typing import Dict, Any

# Imports del sistema de tokens
from app.core.token_system import initialize_token_system, get_token_manager
from app.ai.llm_clients.llm_service import (
    get_llm_service, 
    token_tracking_context,
    set_token_context,
    clear_token_context
)

async def example_1_context_manager():
    """
    ✅ MÉTODO RECOMENDADO: Context manager automático
    """
    print("🎯 Ejemplo 1: Context Manager (RECOMENDADO)")
    
    user_id = 123
    workflow_id = str(uuid4())
    
    # Todo lo que esté dentro del context será tracked automáticamente
    async with token_tracking_context(
        user_id=user_id,
        operation_type="workflow",
        workflow_id=workflow_id
    ):
        # Cualquier llamada LLM aquí será interceptada automáticamente
        llm_service = get_llm_service()
        
        result = await llm_service.run(
            system_prompt="You are a helpful assistant",
            short_term=[],
            long_term=[],
            user_prompt="Explain what is machine learning in 50 words",
            temperature=0.7
        )
        
        # Los tokens se registran automáticamente en background
        print(f"✅ LLM call completed. Result: {result.get('final_output', 'No output')[:100]}...")
        print("📊 Tokens were automatically tracked!")

async def example_2_manual_context():
    """
    ✅ MÉTODO MANUAL: Set/clear manual del contexto
    """
    print("\n🎯 Ejemplo 2: Manual Context")
    
    user_id = 456
    chat_id = str(uuid4())
    
    try:
        # Establecer contexto manualmente
        set_token_context(
            user_id=user_id,
            operation_type="chat",
            workflow_id=chat_id
        )
        
        # Todas las llamadas LLM serán tracked
        llm_service = get_llm_service()
        
        result = await llm_service.run(
            system_prompt="You are a coding assistant",
            short_term=[],
            long_term=[],
            user_prompt="Write a Python function to calculate fibonacci",
            temperature=0.0
        )
        
        print(f"✅ LLM call completed. Auto-tracked!")
        
    finally:
        # IMPORTANTE: Limpiar contexto
        clear_token_context()

async def example_3_chat_service_integration():
    """
    🔧 INTEGRACIÓN CON CHAT SERVICE
    Muestra cómo integrar en servicios existentes
    """
    print("\n🎯 Ejemplo 3: Integración con ChatService")
    
    user_id = 789
    chat_id = uuid4()
    
    # Simular ChatService.handle_message()
    async def mock_chat_service_handle_message(chat_id, user_message, user_id):
        # En tu ChatService real, agregarías estas líneas:
        async with token_tracking_context(
            user_id=user_id,
            operation_type="chat",
            workflow_id=str(chat_id)
        ):
            # Todo el procesamiento LLM existente aquí
            llm_service = get_llm_service()
            
            result = await llm_service.run(
                system_prompt="You are a helpful chatbot",
                short_term=[],
                long_term=[],
                user_prompt=user_message,
                temperature=0.5
            )
            
            return {"reply": result.get("final_output", "No response")}
    
    # Usar el mock
    response = await mock_chat_service_handle_message(
        chat_id=chat_id,
        user_message="What is the weather like?",
        user_id=user_id
    )
    
    print(f"✅ Chat response: {response['reply'][:100]}...")
    print("📊 Tokens automatically tracked in ChatService!")

async def example_4_workflow_service_integration():
    """
    🔧 INTEGRACIÓN CON WORKFLOW SERVICE
    """
    print("\n🎯 Ejemplo 4: Integración con WorkflowService")
    
    user_id = 101
    workflow_id = str(uuid4())
    execution_id = str(uuid4())
    
    # Simular WorkflowRunner.execute_step()
    async def mock_workflow_execute_step(step_data: Dict[str, Any]):
        # En tu WorkflowRunner real, agregarías estas líneas:
        async with token_tracking_context(
            user_id=user_id,
            operation_type="workflow",
            workflow_id=workflow_id,
            execution_id=execution_id
        ):
            # Procesamiento del step que usa LLM
            if step_data.get("requires_llm"):
                llm_service = get_llm_service()
                
                result = await llm_service.run(
                    system_prompt="Process this workflow step",
                    short_term=[],
                    long_term=[],
                    user_prompt=f"Execute step: {step_data['action']}",
                    temperature=0.0
                )
                
                return {"status": "completed", "result": result.get("final_output")}
            
            return {"status": "completed", "result": "Step executed without LLM"}
    
    # Simular ejecución de múltiples steps
    steps = [
        {"action": "send_email", "requires_llm": True},
        {"action": "update_database", "requires_llm": False},
        {"action": "generate_report", "requires_llm": True}
    ]
    
    for i, step in enumerate(steps):
        result = await mock_workflow_execute_step(step)
        print(f"✅ Step {i+1} completed: {step['action']}")
        if step.get("requires_llm"):
            print("📊 LLM tokens automatically tracked!")

async def example_5_check_usage_and_limits():
    """
    📊 VERIFICAR USO Y LÍMITES
    """
    print("\n🎯 Ejemplo 5: Verificar Uso y Límites")
    
    token_manager = get_token_manager()
    user_id = 123
    
    # Verificar si el usuario puede usar tokens
    status = await token_manager.can_use_tokens(user_id, estimated_tokens=1000)
    
    print(f"Can use tokens: {status.can_use}")
    print(f"Remaining tokens: {status.remaining_tokens}")
    print(f"Usage percentage: {status.usage_percentage:.1f}%")
    print(f"Plan type: {status.plan_type}")
    
    if not status.can_use:
        print(f"❌ Limit exceeded: {status.reason}")
    else:
        print("✅ User can proceed with LLM operation")

async def main():
    """
    Ejecutar todos los ejemplos
    """
    print("🚀 INICIANDO EJEMPLOS DE TOKEN TRACKING\n")
    
    # NOTA: En tu app real, esto se hace en el startup
    # initialize_token_system(db_session)
    
    try:
        await example_1_context_manager()
        await example_2_manual_context()
        await example_3_chat_service_integration()
        await example_4_workflow_service_integration()
        await example_5_check_usage_and_limits()
        
        print("\n🎉 TODOS LOS EJEMPLOS COMPLETADOS")
        print("\n📊 RESUMEN:")
        print("- Los tokens se capturan AUTOMÁTICAMENTE en todas las llamadas LLM")
        print("- Solo necesitas establecer el contexto con user_id")
        print("- El sistema maneja límites, alertas y analytics automáticamente")
        print("- Zero configuración adicional en tu código existente")
        
    except Exception as e:
        print(f"❌ Error en ejemplos: {e}")

if __name__ == "__main__":
    asyncio.run(main())