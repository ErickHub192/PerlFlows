"""
Factory CORREGIDO para crear WorkflowEngine con DEPENDENCY INJECTION ADECUADA
✅ Elimina violaciones de DI - usa factory functions apropiadas
✅ Separación limpia de responsabilidades
"""
import logging
from typing import Optional
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .workflow_engine_simple import SimpleWorkflowEngine
from app.db.database import get_db
from app.services.cag_service import CAGService, get_cag_service
from app.services.auto_auth_trigger import AutoAuthTrigger, get_auto_auth_trigger


# 🆕 NEW: ChatWorkflowBridgeService factory function
async def get_bridge_service():
    """Factory function para ChatWorkflowBridgeService"""
    try:
        from app.services.chat_workflow_bridge_service import ChatWorkflowBridgeService
        from app.services.flow_service import get_flow_service
        from app.services.workflow_runner_service import get_workflow_runner
        from app.services.trigger_orchestrator_service import get_trigger_orchestrator_service
        from app.db.database import get_db
        
        # Create dependencies with proper DI
        db_gen = get_db()
        db_session = await anext(db_gen)
        
        try:
            # Create flow service dependencies
            from app.repositories.flow_repository import FlowRepository
            from app.services.flow_definition_service import get_flow_definition_service
            from app.services.trigger_orchestrator_service import TriggerOrchestratorService
            
            flow_repo = FlowRepository(db_session)
            definition_service = get_flow_definition_service()
            
            # Create TriggerOrchestratorService manually
            from app.services.trigger_orchestrator_service import create_trigger_orchestrator_manual
            trigger_orchestrator = await create_trigger_orchestrator_manual(db_session)
            
            # Create FlowService
            from app.services.flow_service import FlowService
            flow_service = FlowService(flow_repo, trigger_orchestrator, definition_service, db_session)
            
            # 🔧 FIX: Create WorkflowRunnerService manually to avoid Depends objects
            from app.services.workflow_runner_service import create_workflow_runner_manual
            
            workflow_runner = await create_workflow_runner_manual(db_session)
            
            # Create bridge service
            bridge_service = ChatWorkflowBridgeService(
                flow_service=flow_service,
                workflow_runner=workflow_runner,
                trigger_orchestrator=trigger_orchestrator,
                db=db_session
            )
            
            return bridge_service
            
        finally:
            await db_session.close()
            
    except Exception as e:
        logger.error(f"Error creating bridge service: {e}", exc_info=True)
        return None

# 🔥 NEW: ReflectionService factory function  
async def get_reflection_service(llm_service=None):
    """
    Factory function para ReflectionService
    🔥 Lazy import para evitar circular dependencies
    ✅ FIX: Acepta LLM service para preservar CAG context
    """
    try:
        from app.workflow_engine.reflection.reflection_service import ReflectionService
        from app.services.workflow_runner_service import WorkflowRunnerService
        from app.handlers.reflect import ReflectHandler
        from app.services.flow_execution_service import get_flow_execution_service
        from app.services.credential_service import get_credential_service
        from app.services.flow_validator_service import get_flow_validator_service
        
        # Create dependencies with proper DI
        from app.db.database import get_db
        db_gen = get_db()
        db_session = await anext(db_gen)
        
        try:
            # ✅ FIX: Create FlowExecutionService with repository dependency
            from app.repositories.flow_execution_repository import FlowExecutionRepository
            from app.services.flow_execution_service import FlowExecutionService
            flow_exec_repo = FlowExecutionRepository(db_session)
            flow_exec_svc = FlowExecutionService(flow_exec_repo)
            
            # Create credential service with its dependencies
            from app.repositories.credential_repository import CredentialRepository
            credential_repo = CredentialRepository(db_session)
            credential_service = get_credential_service(credential_repo)
            
            validator = get_flow_validator_service()  # No takes parameters
            
            # Create WorkflowRunnerService with required dependencies
            workflow_runner = WorkflowRunnerService(
                flow_exec_svc=flow_exec_svc,
                credential_service=credential_service,
                validator=validator
            )
            
            reflect_handler = ReflectHandler(creds={})
            
            # ✅ FIX: Create reflection service with shared LLM instance
            reflection_service = ReflectionService(llm_service=llm_service)
            
            if llm_service:
                logger.info("✅ ReflectionService created with SHARED LLM instance (preserves CAG context)")
            else:
                logger.info("ReflectionService created with fallback LLM service")
            return reflection_service
        finally:
            await db_session.close()
        
    except Exception as e:
        logger.warning(f"Could not create ReflectionService: {e}")
        return None  # Return None if reflection service can't be created


logger = logging.getLogger(__name__)


class SimpleWorkflowEngineFactory:
    """
    Factory CORREGIDO con dependency injection apropiada
    ✅ Usa factory functions en lugar de instanciación directa
    ✅ Separación limpia de responsabilidades
    """
    
    @staticmethod
    async def create_simple_engine(
        cag_service: CAGService,
        auto_auth_trigger: AutoAuthTrigger,
        with_reflection: bool = False,  # ❌ DISABLED: Reflection needs major refactor (see CLAUDE.md)
        llm_service=None
    ) -> SimpleWorkflowEngine:
        """
        Crea WorkflowEngine SIMPLE con dependencias inyectadas correctamente
        
        Args:
            cag_service: Servicio CAG ya configurado
            auto_auth_trigger: Auth trigger ya configurado
            with_reflection: Si incluir ReflectionService para mejora de workflows
            llm_service: LLM service compartido con CAG context
            
        Returns:
            SimpleWorkflowEngine configurado
        """
        try:
            logger.info("Creating SIMPLE WorkflowEngine with proper DI...")
            
            # ✅ FIX: Get shared LLM service if not provided
            if not llm_service:
                from app.ai.llm_clients.llm_service import get_llm_service
                llm_service = get_llm_service()
                logger.info("✅ Using singleton LLM service for WorkflowEngine")
            
            # ❌ REFLECTION DISABLED - NEEDS MAJOR REFACTOR
            # TODO: Current reflection implementation is wasteful and ineffective:
            # 1. Uses separate LLM without CAG context (loses critical node information)
            # 2. Only simulates execution but can't make real improvements
            # 3. Costs 2x tokens for minimal value
            # 4. Doesn't feedback insights to main LLM
            # 
            # REFACTOR NEEDED:
            # - Make reflection part of main LLM with enhanced context
            # - Add real tools (OAuth validation, endpoint testing, etc.)
            # - Implement error pattern detection and auto-fixing
            # - Create user guidance for missing credentials/setup
            reflection_service = None
            if with_reflection:
                logger.warning("⚠️ ReflectionService DISABLED - needs refactor for real value")
                # reflection_service = await get_reflection_service(llm_service=llm_service)
            else:
                logger.info("✅ ReflectionService disabled (default - saves tokens & improves performance)")
            
            # Create bridge service
            bridge_service = await get_bridge_service()
            if bridge_service:
                logger.info("ChatWorkflowBridgeService enabled for workflow management")
            else:
                logger.warning("ChatWorkflowBridgeService could not be created, proceeding without bridge")
            
            # Crear engine con dependencias ya resueltas incluyendo LLM service y bridge service
            engine = SimpleWorkflowEngine(cag_service, auto_auth_trigger, reflection_service, llm_service, bridge_service)
            
            # ✅ Store LLM service reference in engine for access by planner
            engine.llm_service = llm_service
            
            logger.info("SIMPLE WorkflowEngine created successfully with DI")
            return engine
            
        except Exception as e:
            logger.error(f"Error creating simple engine: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def create_minimal_engine(
        cag_service: CAGService,
        auto_auth_trigger: AutoAuthTrigger,
        with_reflection: bool = False
    ) -> SimpleWorkflowEngine:
        """
        Engine MÍNIMO para testing con dependencias inyectadas
        """
        try:
            logger.info("Creating MINIMAL WorkflowEngine...")
            
            engine = await SimpleWorkflowEngineFactory.create_simple_engine(
                cag_service, auto_auth_trigger, with_reflection
            )
            
            # Configuración más conservadora para testing
            # engine.auto_auth_trigger.max_auth_requirements = 2
            
            logger.info("MINIMAL WorkflowEngine created")
            return engine
            
        except Exception as e:
            logger.error(f"Error creating minimal engine: {e}", exc_info=True)
            raise


# ✅ CORREGIDO: Factory functions con DI apropiada
async def get_simple_workflow_engine(
    cag_service: CAGService = Depends(get_cag_service),
    auto_auth_trigger: AutoAuthTrigger = Depends(get_auto_auth_trigger)
) -> SimpleWorkflowEngine:
    """
    ✅ CORREGIDO: Factory function con dependency injection apropiada
    Para uso en FastAPI routers y servicios
    """
    logger.info("Creating SIMPLE WorkflowEngine with proper dependency injection...")
    
    return await SimpleWorkflowEngineFactory.create_simple_engine(
        cag_service, auto_auth_trigger
    )


async def get_minimal_workflow_engine(
    cag_service: CAGService = Depends(get_cag_service),
    auto_auth_trigger: AutoAuthTrigger = Depends(get_auto_auth_trigger)
) -> SimpleWorkflowEngine:
    """
    ✅ CORREGIDO: Factory function para testing con DI apropiada
    """
    logger.info("Creating MINIMAL WorkflowEngine for testing...")
    
    return await SimpleWorkflowEngineFactory.create_minimal_engine(
        cag_service, auto_auth_trigger
    )


# Legacy functions removed - use proper dependency injection with get_simple_workflow_engine()