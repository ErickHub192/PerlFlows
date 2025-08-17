#!/usr/bin/env python3
"""
Script para registrar el nodo AI_Agent_Creator.create_agent en la BD.
Registra el nodo, acción y parámetros para que Kyra pueda usarlo en planning.
"""

import asyncio
import sys
import os
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import async_session
from app.db.models import Node, Action, Parameter, NodeType, ActionType, ParamType, UsageMode


async def register_ai_agent_creator_node():
    """Registra el nodo AI_Agent_Creator con su acción y parámetros"""
    
    async with async_session() as session:
        try:
            # 1. Verificar si ya existe el nodo
            result = await session.execute(
                select(Node).where(Node.name == "AI_Agent_Creator")
            )
            existing_node = result.scalar_one_or_none()
            
            if existing_node:
                print("[OK] Nodo AI_Agent_Creator ya existe, actualizando...")
                node = existing_node
            else:
                print("[NEW] Creando nodo AI_Agent_Creator...")
                # 2. Crear el nodo AI_Agent_Creator
                node = Node(
                    node_id=uuid4(),
                    name="AI_Agent_Creator",
                    description="Creates custom AI agents with tools, memory, and triggers. Kyra designs the agent architecture and user provides LLM model + credentials.",
                    node_type=NodeType.ai,
                    usage_mode=UsageMode.step_and_tool,
                    connection_required=False,
                    supports_custom_auth=True
                )
                session.add(node)
                await session.flush()  # Para obtener el node_id
            
            # 3. Verificar si ya existe la acción
            result = await session.execute(
                select(Action).where(
                    Action.node_id == node.node_id,
                    Action.name == "create_agent"
                )
            )
            existing_action = result.scalar_one_or_none()
            
            if existing_action:
                print("[OK] Accion create_agent ya existe, actualizando...")
                action = existing_action
            else:
                print("[NEW] Creando accion create_agent...")
                # 4. Crear la acción create_agent
                action = Action(
                    action_id=uuid4(),
                    node_id=node.node_id,
                    name="create_agent",
                    description="Creates a new AI agent with specified tools, memory configuration, and triggers. The agent becomes available for execution once created.",
                    action_type=ActionType.Action
                )
                session.add(action)
                await session.flush()  # Para obtener el action_id
            
            # 5. Eliminar parámetros existentes para recrearlos
            await session.execute(
                text("DELETE FROM parameters WHERE action_id = :action_id"),
                {"action_id": action.action_id}
            )
            
            # 6. Crear parámetros detallados
            parameters = [
                # Lo que Kyra proporciona (requerido)
                Parameter(
                    param_id=uuid4(),
                    action_id=action.action_id,
                    name="agent_name",
                    description="Name for the AI agent (provided by Kyra planning)",
                    required=True,
                    param_type=ParamType.string
                ),
                Parameter(
                    param_id=uuid4(),
                    action_id=action.action_id,
                    name="agent_prompt",
                    description="System prompt for the AI agent (designed by Kyra)",
                    required=True,
                    param_type=ParamType.string
                ),
                Parameter(
                    param_id=uuid4(),
                    action_id=action.action_id,
                    name="tools",
                    description="List of tool names/nodes that the agent can use (selected by Kyra from CAG)",
                    required=True,
                    param_type=ParamType.json
                ),
                
                # Lo que usuario debe proporcionar (requerido)
                Parameter(
                    param_id=uuid4(),
                    action_id=action.action_id,
                    name="model",
                    description="LLM model to use (user selection from available models)",
                    required=True,
                    param_type=ParamType.string
                ),
                
                # Credentials (uno de los dos requerido)
                Parameter(
                    param_id=uuid4(),
                    action_id=action.action_id,
                    name="api_key",
                    description="New API key for LLM provider (alternative to credential_id)",
                    required=False,
                    param_type=ParamType.string
                ),
                Parameter(
                    param_id=uuid4(),
                    action_id=action.action_id,
                    name="credential_id",
                    description="Existing credential ID to use (alternative to api_key)",
                    required=False,
                    param_type=ParamType.string
                ),
                
                # Configuración de triggers (opcional)
                Parameter(
                    param_id=uuid4(),
                    action_id=action.action_id,
                    name="activation_type",
                    description="How the agent is activated: 'manual' (user triggered) or 'triggered' (automatic)",
                    required=False,
                    param_type=ParamType.string
                ),
                Parameter(
                    param_id=uuid4(),
                    action_id=action.action_id,
                    name="trigger_node",
                    description="Trigger node name (e.g., 'Gmail.email_received', 'Schedule.cron') - Kyra can suggest from CAG",
                    required=False,
                    param_type=ParamType.string
                ),
                Parameter(
                    param_id=uuid4(),
                    action_id=action.action_id,
                    name="trigger_params",
                    description="Parameters for the trigger node (e.g., cron schedule, email filters)",
                    required=False,
                    param_type=ParamType.json
                ),
                Parameter(
                    param_id=uuid4(),
                    action_id=action.action_id,
                    name="is_active",
                    description="Whether the agent should be active for automatic triggers (default: true)",
                    required=False,
                    param_type=ParamType.boolean
                ),
                
                # Configuración avanzada (opcional)
                Parameter(
                    param_id=uuid4(),
                    action_id=action.action_id,
                    name="memory_schema",
                    description="Memory configuration (short/long term, handlers) - Kyra can suggest optimal setup",
                    required=False,
                    param_type=ParamType.json
                ),
                Parameter(
                    param_id=uuid4(),
                    action_id=action.action_id,
                    name="temperature",
                    description="LLM temperature for randomness (0.0-1.0, default: 0.7)",
                    required=False,
                    param_type=ParamType.number
                ),
                Parameter(
                    param_id=uuid4(),
                    action_id=action.action_id,
                    name="max_iterations",
                    description="Maximum reasoning iterations for the agent (default: 5)",
                    required=False,
                    param_type=ParamType.number
                )
            ]
            
            # Agregar todos los parámetros
            for param in parameters:
                session.add(param)
            
            # 7. Commit todo
            await session.commit()
            print("[SUCCESS] Nodo AI_Agent_Creator registrado exitosamente!")
            
            # 8. Mostrar resumen
            print(f"\nRESUMEN:")
            print(f"   - Nodo: {node.name} (ID: {node.node_id})")
            print(f"   - Accion: {action.name} (ID: {action.action_id})")
            print(f"   - Parametros: {len(parameters)} registrados")
            print(f"\nUSO PARA KYRA:")
            print("   - Kyra puede sugerir este nodo cuando el usuario quiere crear agentes")
            print("   - Kyra disena: agent_name, agent_prompt, tools, trigger_node")
            print("   - Usuario proporciona: model, credentials")
            print("   - Supports triggers from CAG: Schedule.cron, Gmail.email_received, etc.")
            
        except Exception as e:
            await session.rollback()
            print(f"[ERROR] Error registrando nodo: {e}")
            raise


async def main():
    """Función principal"""
    print("Registrando nodo AI_Agent_Creator en CAG...")
    await register_ai_agent_creator_node()
    print("Completado!")


if __name__ == "__main__":
    asyncio.run(main())