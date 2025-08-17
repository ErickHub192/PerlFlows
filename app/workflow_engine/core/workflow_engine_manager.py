"""
WorkflowEngineManager - Singleton Pattern para Workflow Engines
Mantiene instancias únicas por chat_id para preservar identidad de Kyra
"""
import logging
from typing import Dict, Optional
from uuid import uuid4

from .workflow_engine_simple import SimpleWorkflowEngine
from .simple_engine_factory import SimpleWorkflowEngineFactory

logger = logging.getLogger(__name__)


class WorkflowEngineManager:
    """
    Gestiona instancias singleton de WorkflowEngine por chat_id.
    
    Esto asegura que:
    1. El mismo chat_id siempre obtenga la MISMA instancia
    2. El LLM planner mantenga su identidad y contexto (Kyra)
    3. La historia de conversación se preserve entre requests
    4. No se pierda el contexto después de OAuth
    """
    
    _instances: Dict[str, SimpleWorkflowEngine] = {}
    _lock = None  # Para thread safety si es necesario
    
    @classmethod
    async def get_or_create(
        cls, 
        chat_id: str, 
        cag_service=None, 
        auto_auth_trigger=None,
        skip_cag_construction=False
    ) -> SimpleWorkflowEngine:
        """
        Obtiene la instancia existente para este chat_id o crea una nueva.
        
        Args:
            chat_id: Identificador único del chat/sesión
            cag_service: Servicio CAG (solo para nuevas instancias)
            auto_auth_trigger: Auth trigger (solo para nuevas instancias)
            skip_cag_construction: Si True, evita construir CAG (post-OAuth optimization)
            
        Returns:
            SimpleWorkflowEngine: La misma instancia para este chat_id
        """
        if chat_id not in cls._instances:
            logger.info(f"🏭 CREATING NEW WorkflowEngine instance for chat_id: {chat_id}")
            
            # Crear nueva instancia usando la factory
            # ✅ FIX: Verificar que las dependencias no sean objetos Depends sin resolver
            is_valid_cag = cag_service and not hasattr(cag_service, 'dependency')
            is_valid_auth = auto_auth_trigger and not hasattr(auto_auth_trigger, 'dependency')
            
            if is_valid_cag and is_valid_auth:
                # Crear con dependencias proporcionadas + reflection
                logger.info("🔧 USING RESOLVED DEPENDENCIES from FastAPI DI")
                engine = await SimpleWorkflowEngineFactory.create_simple_engine(
                    cag_service=cag_service,
                    auto_auth_trigger=auto_auth_trigger,
                    with_reflection=True  # ✅ MANTENER REFLECTION
                )
            else:
                # Dependencies no resueltas o faltantes - crear manualmente
                logger.info(f"🔧 MANUAL DEPENDENCY CREATION: cag_valid={is_valid_cag}, auth_valid={is_valid_auth}")
                if skip_cag_construction:
                    logger.info("⚡ OPTIMIZATION: Skipping CAG construction (post-OAuth)")
                    # Post-OAuth: Crear dependencies manually (FastAPI DI no está disponible aquí)
                    from app.services.auto_auth_trigger import AutoAuthTrigger
                    from app.services.auth_policy_service import AuthPolicyService  
                    from app.services.credential_service import CredentialService
                    from app.services.auth_handler_registry import get_auth_handler_registry
                    from app.db.database import async_session
                    
                    # Crear todas las dependencias manualmente (no hay FastAPI context)
                    async with async_session() as db_session:
                        # AuthPolicyService necesita AuthPolicyRepository
                        from app.repositories.auth_policy_repository import AuthPolicyRepository
                        auth_policy_repo = AuthPolicyRepository(db_session)
                        auth_policy_service = AuthPolicyService(db_session, auth_policy_repo)
                        
                        # CredentialService necesita CredentialRepository
                        from app.repositories.credential_repository import CredentialRepository
                        credential_repo = CredentialRepository(db_session)
                        credential_service = CredentialService(credential_repo)
                        
                        auth_handler_registry = get_auth_handler_registry()
                        
                        # Crear AutoAuthTrigger con todas las dependencias requeridas
                        auto_auth_trigger = AutoAuthTrigger(
                            db=db_session,
                            auth_policy_service=auth_policy_service,
                            credential_service=credential_service,
                            auth_handler_registry=auth_handler_registry
                        )
                    
                    # CAG vacío para post-OAuth optimization
                    mock_cag = None  
                    
                    # Crear engine simplificado con bridge service
                    from .workflow_engine_simple import SimpleWorkflowEngine
                    from .simple_engine_factory import get_bridge_service
                    
                    # Get bridge service for workflow management
                    bridge_service = await get_bridge_service()
                    
                    engine = SimpleWorkflowEngine(mock_cag, auto_auth_trigger, None, None, bridge_service)
                else:
                    # Pre-OAuth: Crear con dependencias completas
                    from app.services.cag_service import CAGService
                    from app.services.auto_auth_trigger import get_auto_auth_trigger
                    from app.repositories.node_repository import NodeRepository
                    from app.repositories.action_repository import ActionRepository
                    from app.repositories.parameter_repository import ParameterRepository
                    from app.ai.llm_clients.llm_service import get_llm_client
                    from app.db.database import async_session
                    
                    # Crear dependencias completas
                    async with async_session() as db_session:
                        node_repo = NodeRepository(db_session)
                        action_repo = ActionRepository(db_session)
                        param_repo = ParameterRepository(db_session)
                        llm_client = get_llm_client()
                        
                        # 🔥 OPCIÓN 2: RedisNodeCacheService sin llm_client
                        from app.services.cag_service import RedisNodeCacheService
                        cag_service = RedisNodeCacheService(node_repo, action_repo, param_repo, "kyra:nodes:all")
                        
                        # Crear AutoAuthTrigger manualmente con todas las dependencias
                        from app.services.auth_policy_service import AuthPolicyService
                        from app.services.credential_service import CredentialService
                        from app.services.auto_auth_trigger import AutoAuthTrigger
                        from app.repositories.auth_policy_repository import AuthPolicyRepository
                        from app.repositories.credential_repository import CredentialRepository
                        from app.services.auth_handler_registry import get_auth_handler_registry
                        
                        auth_policy_repo = AuthPolicyRepository(db_session)
                        auth_policy_service = AuthPolicyService(db_session, auth_policy_repo)
                        credential_repo = CredentialRepository(db_session)
                        credential_service = CredentialService(credential_repo)
                        auth_handler_registry = get_auth_handler_registry()
                        
                        auto_auth_trigger = AutoAuthTrigger(
                            db=db_session,
                            auth_policy_service=auth_policy_service,
                            credential_service=credential_service,
                            auth_handler_registry=auth_handler_registry
                        )
                        
                        # Crear engine con reflection habilitado
                        engine = await SimpleWorkflowEngineFactory.create_simple_engine(
                            cag_service=cag_service,
                            auto_auth_trigger=auto_auth_trigger,
                            with_reflection=True  # ✅ MANTENER REFLECTION
                        )
            
            # Asociar el engine con el chat_id
            engine.chat_id = chat_id
            cls._instances[chat_id] = engine
            
            logger.info(f"✅ CREATED WorkflowEngine for chat_id: {chat_id}")
            logger.info(f"📊 MANAGER STATS: {len(cls._instances)} active engines")
            
        else:
            logger.info(f"♻️ REUSING existing WorkflowEngine for chat_id: {chat_id}")
            # ✅ FIX: Asegurar que el chat_id esté establecido en engines reutilizados
            engine = cls._instances[chat_id]
            if not hasattr(engine, 'chat_id') or engine.chat_id != chat_id:
                engine.chat_id = chat_id
                logger.info(f"✅ RESTORED chat_id to reused engine: {chat_id}")
            
        return cls._instances[chat_id]
    
    @classmethod
    def get_existing(cls, chat_id: str) -> Optional[SimpleWorkflowEngine]:
        """
        Obtiene una instancia existente sin crear una nueva.
        
        Args:
            chat_id: Identificador del chat
            
        Returns:
            SimpleWorkflowEngine o None si no existe
        """
        logger.info(f"🔍 SEARCHING for existing WorkflowEngine with chat_id: {chat_id}")
        logger.info(f"🔍 AVAILABLE chat_ids in manager: {list(cls._instances.keys())}")
        logger.info(f"🔍 TOTAL engines managed: {len(cls._instances)}")
        
        engine = cls._instances.get(chat_id)
        if engine:
            logger.info(f"✅ FOUND existing WorkflowEngine for chat_id: {chat_id}")
        else:
            logger.warning(f"❌ NO existing WorkflowEngine found for chat_id: {chat_id}")
        
        return engine
    
    @classmethod
    def remove(cls, chat_id: str) -> bool:
        """
        Limpia la instancia cuando termina el workflow.
        
        Args:
            chat_id: Identificador del chat
            
        Returns:
            bool: True si se removió, False si no existía
        """
        if chat_id in cls._instances:
            logger.info(f"🗑️ REMOVING WorkflowEngine for chat_id: {chat_id}")
            del cls._instances[chat_id]
            logger.info(f"📊 MANAGER STATS: {len(cls._instances)} active engines")
            return True
        return False
    
    @classmethod
    def cleanup_expired(cls, max_age_hours: int = 24) -> int:
        """
        Limpia instancias que han estado inactivas por mucho tiempo.
        
        Args:
            max_age_hours: Horas máximas de inactividad
            
        Returns:
            int: Número de instancias removidas
        """
        # TODO: Implementar limpieza basada en timestamp
        # Por ahora, método placeholder
        removed_count = 0
        logger.info(f"🧹 CLEANUP: Would check {len(cls._instances)} engines for expiration")
        return removed_count
    
    @classmethod
    def get_stats(cls) -> Dict[str, any]:
        """
        Obtiene estadísticas del manager.
        
        Returns:
            Dict con estadísticas
        """
        return {
            "active_engines": len(cls._instances),
            "chat_ids": list(cls._instances.keys()),
            "memory_usage": "TODO: implement"
        }
    
    @classmethod
    def reset_all(cls):
        """
        PELIGROSO: Limpia todas las instancias. Solo para testing.
        """
        logger.warning("⚠️ RESET ALL: Clearing all WorkflowEngine instances")
        cls._instances.clear()


# Función helper para obtener instancia
async def get_workflow_engine_for_chat(chat_id: str) -> SimpleWorkflowEngine:
    """
    Helper function para obtener WorkflowEngine para un chat específico.
    
    Args:
        chat_id: ID del chat
        
    Returns:
        SimpleWorkflowEngine para ese chat
    """
    return await WorkflowEngineManager.get_or_create(chat_id)


# Función helper para nuevos chats
async def create_new_workflow_engine() -> tuple[str, SimpleWorkflowEngine]:
    """
    Helper function para crear un nuevo WorkflowEngine con chat_id generado.
    
    Returns:
        Tuple de (chat_id, engine)
    """
    new_chat_id = str(uuid4())
    engine = await WorkflowEngineManager.get_or_create(new_chat_id)
    return new_chat_id, engine