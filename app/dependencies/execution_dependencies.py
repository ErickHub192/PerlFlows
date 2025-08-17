# app/dependencies/execution_dependencies.py

from fastapi import Depends
from app.workflow_engine.execution.execution_bridge import ExecutionBridge
from app.dependencies.repository_dependencies import (
    get_node_repository, 
    get_action_repository, 
    get_parameter_repository
)
from app.repositories.node_repository import NodeRepository
from app.repositories.action_repository import ActionRepository
from app.repositories.parameter_repository import ParameterRepository

def get_execution_bridge(
    node_repo: NodeRepository = Depends(get_node_repository),
    action_repo: ActionRepository = Depends(get_action_repository),
    param_repo: ParameterRepository = Depends(get_parameter_repository)
) -> ExecutionBridge:
    """Factory for ExecutionBridge with FastAPI DI"""
    return ExecutionBridge(node_repo, action_repo, param_repo)