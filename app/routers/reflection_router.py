"""
Reflection API Router - Endpoints para capacidades de reflexión y mejora de workflows
Expone ReflectionService para uso del frontend y APIs externas
"""
import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.workflow_engine.reflection.reflection_service import ReflectionService
from app.workflow_engine.core.simple_engine_factory import get_reflection_service
from app.dtos.workflow_creation_result_dto import WorkflowCreationResultDTO
from app.workflow_engine.core.interfaces import WorkflowCreationResult, WorkflowType
from app.core.auth import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reflection", tags=["Workflow Reflection"])


class ReflectionAnalysisRequest(BaseModel):
    """Request para análisis de reflexión de workflow"""
    workflow_result: Dict[str, Any]
    user_message: str
    max_iterations: Optional[int] = 2
    simulate_first: bool = True


class ReflectionAnalysisResponse(BaseModel):
    """Response del análisis de reflexión"""
    status: str
    original_workflow: Dict[str, Any]
    improved_workflow: Optional[Dict[str, Any]] = None
    iterations_completed: int
    improvements_made: List[str]
    simulation_summary: Dict[str, Any]
    reflection_insights: List[str]


class WorkflowSimulationRequest(BaseModel):
    """Request para simulación de workflow"""
    workflow_result: Dict[str, Any]
    user_message: str


class WorkflowSimulationResponse(BaseModel):
    """Response de simulación de workflow"""
    simulation_status: str
    steps_executed: int
    execution_results: List[Dict[str, Any]]
    potential_issues: List[str]
    success_probability: float
    recommendations: List[str]


@router.post("/analyze-workflow", response_model=ReflectionAnalysisResponse)
async def analyze_workflow_with_reflection(
    request: ReflectionAnalysisRequest,
    user_id: int = Depends(get_current_user_id),
    reflection_service: ReflectionService = Depends(get_reflection_service)
):
    """
    Analiza y mejora un workflow usando ReflectionService
    Plan → Simulate → Reflect → Improve workflow
    """
    try:
        if not reflection_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Reflection service is not available"
            )

        logger.info(f"Starting workflow reflection analysis for user {user_id}")

        # Convert dict to WorkflowCreationResult for reflection service
        workflow_result = _dict_to_workflow_result(request.workflow_result)

        # Execute reflection with smart iteration
        enhanced_result = await reflection_service.execute_workflow_with_smart_iteration(
            workflow_result=workflow_result,
            user_message=request.user_message,
            user_id=user_id,
            simulate_first=request.simulate_first,
            max_iterations=request.max_iterations
        )

        # Format response
        return ReflectionAnalysisResponse(
            status=enhanced_result.get("status", "unknown"),
            original_workflow=request.workflow_result,
            improved_workflow=enhanced_result.get("improved_workflow"),
            iterations_completed=enhanced_result.get("iterations_completed", 0),
            improvements_made=enhanced_result.get("improvements_made", []),
            simulation_summary=enhanced_result.get("simulation_summary", {}),
            reflection_insights=enhanced_result.get("reflection_insights", [])
        )

    except Exception as e:
        logger.error(f"Error in workflow reflection analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze workflow with reflection: {str(e)}"
        )


@router.post("/simulate-workflow", response_model=WorkflowSimulationResponse)
async def simulate_workflow_execution(
    request: WorkflowSimulationRequest,
    user_id: int = Depends(get_current_user_id),
    reflection_service: ReflectionService = Depends(get_reflection_service)
):
    """
    Simula la ejecución de un workflow sin ejecutarlo realmente
    Usa dry-run capabilities del ReflectionService
    """
    try:
        if not reflection_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Reflection service is not available"
            )

        logger.info(f"Starting workflow simulation for user {user_id}")

        # Convert dict to WorkflowCreationResult
        workflow_result = _dict_to_workflow_result(request.workflow_result)

        # Execute simulation only (no real execution)
        simulation_result = await reflection_service._simulate_workflow_execution(
            workflow_result, user_id
        )

        # Analyze simulation results
        analysis = await reflection_service._reflect_on_execution(
            simulation_result, request.user_message
        )

        return WorkflowSimulationResponse(
            simulation_status=simulation_result.get("overall_status", "unknown"),
            steps_executed=len(simulation_result.get("steps", [])),
            execution_results=simulation_result.get("steps", []),
            potential_issues=analysis.get("potential_issues", []),
            success_probability=analysis.get("success_probability", 0.5),
            recommendations=analysis.get("recommendations", [])
        )

    except Exception as e:
        logger.error(f"Error in workflow simulation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to simulate workflow: {str(e)}"
        )


@router.get("/capabilities")
async def get_reflection_capabilities(
    reflection_service: ReflectionService = Depends(get_reflection_service)
):
    """
    Obtiene las capacidades disponibles del ReflectionService
    """
    try:
        if not reflection_service:
            return {
                "reflection_available": False,
                "message": "Reflection service is not available"
            }

        return {
            "reflection_available": True,
            "capabilities": {
                "workflow_analysis": True,
                "workflow_simulation": True,
                "iterative_improvement": True,
                "plan_act_reflect_iterate": True,
                "smart_iteration": True,
                "dry_run_execution": True
            },
            "features": {
                "max_iterations_supported": 5,
                "simulation_with_fake_data": True,
                "reflection_interval": 3,
                "supports_llm_reflection": True
            }
        }

    except Exception as e:
        logger.error(f"Error getting reflection capabilities: {e}")
        return {
            "reflection_available": False,
            "error": str(e)
        }


@router.post("/reflect-on-execution")
async def reflect_on_workflow_execution(
    execution_result: Dict[str, Any],
    user_message: str,
    user_id: int = Depends(get_current_user_id),
    reflection_service: ReflectionService = Depends(get_reflection_service)
):
    """
    Reflexiona sobre los resultados de ejecución de un workflow
    Genera insights y recomendaciones de mejora
    """
    try:
        if not reflection_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Reflection service is not available"
            )

        logger.info(f"Reflecting on workflow execution for user {user_id}")

        # Perform reflection analysis
        reflection_analysis = await reflection_service._reflect_on_execution(
            execution_result, user_message
        )

        return {
            "reflection_status": "completed",
            "insights": reflection_analysis.get("insights", []),
            "potential_issues": reflection_analysis.get("potential_issues", []),
            "recommendations": reflection_analysis.get("recommendations", []),
            "success_probability": reflection_analysis.get("success_probability", 0.5),
            "improvement_suggestions": reflection_analysis.get("improvement_suggestions", [])
        }

    except Exception as e:
        logger.error(f"Error reflecting on execution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reflect on execution: {str(e)}"
        )


def _dict_to_workflow_result(workflow_dict: Dict[str, Any]) -> WorkflowCreationResult:
    """
    Helper function to convert dictionary to WorkflowCreationResult
    """
    try:
        # Extract workflow type
        workflow_type_str = workflow_dict.get("workflow_type", "classic")
        workflow_type = WorkflowType.AGENT if workflow_type_str == "agent" else WorkflowType.CLASSIC

        # Create WorkflowCreationResult
        return WorkflowCreationResult(
            status="success",
            workflow_type=workflow_type,
            steps=workflow_dict.get("steps", []),
            confidence=workflow_dict.get("confidence", 0.7),
            oauth_requirements=[],
            discovered_resources=[],
            metadata=workflow_dict.get("metadata", {})
        )

    except Exception as e:
        logger.error(f"Error converting dict to WorkflowCreationResult: {e}")
        raise ValueError(f"Invalid workflow format: {str(e)}")