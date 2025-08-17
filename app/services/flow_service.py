# app/services/flow_service.py

from typing import List
from uuid import UUID
from fastapi import HTTPException, status, Depends

from app.repositories.flow_repository import FlowRepository, get_flow_repository
from app.services.trigger_orchestrator_service import TriggerOrchestratorService, get_trigger_orchestrator_service
from app.services.flow_definition_service import FlowDefinitionService, get_flow_definition_service
from app.dtos.flow_dtos import FlowSummaryDTO, FlowDetailDTO
from app.db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession


class FlowService:
    """
    ✅ LIMPIADO: Servicio que implementa la gestión de flujos sin interface innecesaria
    """

    def __init__(
        self, 
        repo: FlowRepository, 
        orchestrator: TriggerOrchestratorService,
        definition_service: FlowDefinitionService,
        db: AsyncSession
    ):
        self.repo = repo
        self.orchestrator = orchestrator
        self.definition_service = definition_service
        self.db = db

    def _build_flow_summary_dto(self, flow) -> FlowSummaryDTO:
        """Helper para construir FlowSummaryDTO con información del chat"""
        dto_data = {
            "flow_id": flow.flow_id,
            "name": flow.name,
            "is_active": flow.is_active,
            "created_at": flow.created_at,
            "updated_at": flow.updated_at,
            "chat_id": flow.chat_id,
            "chat_title": None
        }
        
        # Si hay chat_session relacionado, incluir el título
        if hasattr(flow, 'chat_session') and flow.chat_session:
            dto_data["chat_title"] = flow.chat_session.title
            
        return FlowSummaryDTO(**dto_data)

    async def list_flows(self, owner_id: int) -> List[FlowSummaryDTO]:
        flows = await self.repo.list_by_owner_with_chat(owner_id)
        return [self._build_flow_summary_dto(f) for f in flows]

    async def get_flow(self, flow_id: UUID, owner_id: int) -> FlowSummaryDTO:
        # 1) Obtener el flujo por su ID
        flow = await self.repo.get_by_id(flow_id)
        if not flow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flow no encontrado"
            )
        return FlowSummaryDTO.from_orm(flow)

    async def get_flow_detail(
        self, 
        flow_id: UUID, 
        owner_id: UUID, 
        include_spec: bool = False
    ) -> FlowDetailDTO:
        """
        ✅ NUEVO: Método que maneja la lógica de composición de datos
        que antes estaba en el router.
        """
        # 1) Obtener summary del flujo
        summary = await self.get_flow(flow_id, owner_id)
        
        # 2) Crear FlowDetailDTO desde summary
        result = FlowDetailDTO(**summary.model_dump())
        
        # 3) Agregar spec si se solicita
        if include_spec:
            result.spec = await self.definition_service.get_flow_spec(flow_id)
            
        return result

    async def set_flow_active(
        self,
        flow_id: UUID,
        is_active: bool,
        user_id: int
    ) -> FlowSummaryDTO:
        # 1) Obtener el flujo y verificar que existe
        flow = await self.repo.get_by_id(flow_id)
        if not flow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flow no encontrado"
            )

        # 2) Verificar que el user_id coincide con el owner_id del flujo
        if flow.owner_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para modificar este flujo"
            )

        # 3) Actualizar la bandera de activo/inactivo
        updated_flow = await self.repo.set_active(flow_id, is_active)
        if not updated_flow:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo actualizar el estado del flujo"
            )

        # 4) Programar o desprogramar en el scheduler según is_active
        if is_active:
            try:
                await self.orchestrator.schedule_flow(
                    flow_id,
                    updated_flow.spec,
                    user_id
                )
            except Exception:
                # Si falla scheduling, revertimos la bandera a False
                await self.repo.set_active(flow_id, False)
                raise
        else:
            await self.orchestrator.unschedule_flow(
                flow_id,
                updated_flow.spec,
                user_id
            )

        # 5) Devolver DTO actualizado
        return FlowSummaryDTO.from_orm(updated_flow)

    async def create_flow(
        self, 
        name: str, 
        spec: dict, 
        owner_id: int, 
        description: str = None,
        chat_id: UUID = None
    ) -> FlowSummaryDTO:
        """
        Crea y guarda un nuevo flujo en la base de datos
        ✅ Service maneja transacciones (movido desde repository)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"🔄 FLOWSERVICE START: create_flow for user {owner_id}, name: {name}")
            logger.info(f"🔄 FLOWSERVICE STATE: db.is_active: {self.db.is_active}, in_transaction: {self.db.in_transaction()}")
            
            # No manejar transacciones aquí - dejar que el router/dependency injection las maneje
            # Crear el flujo en el repositorio
            logger.info(f"🔄 FLOWSERVICE PRE-REPO: About to call repo.create_flow")
            flow = await self.repo.create_flow(
                name=name,
                spec=spec,
                owner_id=owner_id,
                description=description,
                chat_id=chat_id
            )
            logger.info(f"🔄 FLOWSERVICE POST-REPO: repo.create_flow returned flow with ID: {flow.flow_id}")
            logger.info(f"🔄 FLOWSERVICE STATE AFTER REPO: db.in_transaction: {self.db.in_transaction()}")
            
            # Retornar DTO
            result_dto = FlowSummaryDTO.from_orm(flow)
            logger.info(f"🔄 FLOWSERVICE SUCCESS: Created DTO with flow_id: {result_dto.flow_id}")
            return result_dto
            
        except Exception as e:
            logger.error(f"🔄 FLOWSERVICE ERROR: {e}")
            logger.error(f"🔄 FLOWSERVICE ERROR STATE: db.is_active: {self.db.is_active}, in_transaction: {self.db.in_transaction()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creando flujo: {str(e)}"
            )

    async def update_flow(
        self, 
        flow_id: UUID,
        name: str, 
        spec: dict, 
        description: str = None
    ) -> FlowSummaryDTO:
        """
        Actualiza un flujo existente en la base de datos
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"🔄 FLOWSERVICE UPDATE: update_flow for flow_id {flow_id}")
            logger.info(f"🔄 FLOWSERVICE UPDATE STATE: db.is_active: {self.db.is_active}, in_transaction: {self.db.in_transaction()}")
            
            # Obtener el flow existente
            existing_flow = await self.repo.get_by_id(flow_id)
            if not existing_flow:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Flow no encontrado para actualizar"
                )
            
            # Actualizar el flow en el repositorio
            logger.info(f"🔄 FLOWSERVICE UPDATE PRE-REPO: About to call repo.update_flow")
            updated_flow = await self.repo.update_flow(
                flow_id=flow_id,
                name=name,
                spec=spec,
                description=description
            )
            logger.info(f"🔄 FLOWSERVICE UPDATE POST-REPO: repo.update_flow returned flow with ID: {updated_flow.flow_id}")
            logger.info(f"🔄 FLOWSERVICE UPDATE STATE AFTER REPO: db.in_transaction: {self.db.in_transaction()}")
            
            # Retornar DTO
            result_dto = FlowSummaryDTO.from_orm(updated_flow)
            logger.info(f"🔄 FLOWSERVICE UPDATE SUCCESS: Updated DTO with flow_id: {result_dto.flow_id}")
            return result_dto
            
        except Exception as e:
            logger.error(f"🔄 FLOWSERVICE UPDATE ERROR: {e}")
            logger.error(f"🔄 FLOWSERVICE UPDATE ERROR STATE: db.is_active: {self.db.is_active}, in_transaction: {self.db.in_transaction()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error actualizando flujo: {str(e)}"
            )
    
    async def get_user_flows(self, owner_id: int, limit: int = None) -> List[FlowSummaryDTO]:
        """
        Alias para list_flows para compatibilidad con comandos de chat
        """
        flows = await self.list_flows(owner_id)
        if limit:
            flows = flows[:limit]
        return flows
    
    async def get_flow_by_name(self, owner_id: int, name: str) -> FlowSummaryDTO:
        """
        Busca un flujo por nombre para un usuario específico
        """
        flows = await self.repo.list_by_owner(owner_id)
        
        for flow in flows:
            if flow.name.lower() == name.lower():
                return FlowSummaryDTO.from_orm(flow)
        
        return None
    
    async def get_flow_by_chat_id(self, owner_id: int, chat_id: UUID) -> FlowSummaryDTO:
        """
        Busca un flujo por chat_id para un usuario específico
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"🔍 FLOWSERVICE LOOKUP: get_flow_by_chat_id for user {owner_id}, chat_id: {chat_id}")
            
            # Buscar workflow por chat_id en la tabla flows
            flow = await self.repo.get_by_chat_id(owner_id, chat_id)
            
            if flow:
                logger.info(f"🔍 FLOWSERVICE FOUND: Found flow {flow.flow_id} for chat_id {chat_id}")
                return FlowSummaryDTO.from_orm(flow)
            else:
                logger.info(f"🔍 FLOWSERVICE NOT FOUND: No flow found for chat_id {chat_id}")
                return None
                
        except Exception as e:
            logger.error(f"🔍 FLOWSERVICE LOOKUP ERROR: {e}")
            return None
    
    async def execute_flow(self, flow_id: UUID, user_id: int) -> dict:
        """
        Ejecuta un flujo manualmente
        """
        # Verificar que el flujo existe y pertenece al usuario
        flow = await self.repo.get_by_id(flow_id)
        if not flow or flow.owner_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flow no encontrado"
            )
        
        # Ejecutar flujo a través del orchestrator
        try:
            execution_result = await self.orchestrator.execute_flow_manually(
                flow_id=flow_id,
                spec=flow.spec,
                user_id=user_id
            )
            return execution_result
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error ejecutando flujo: {str(e)}"
            )
    
    async def toggle_flow_active(self, flow_id: UUID, is_active: bool, user_id: int = None) -> FlowSummaryDTO:
        """
        Alias para set_flow_active para compatibilidad con comandos de chat
        """
        # Si no se proporciona user_id, obtenerlo del flujo
        if user_id is None:
            flow = await self.repo.get_by_id(flow_id)
            if flow:
                user_id = flow.owner_id
        
        return await self.set_flow_active(flow_id, is_active, user_id)
    
    async def delete_flow(self, flow_id: UUID, user_id: int) -> bool:
        """
        Elimina un flujo
        """
        # Verificar que el flujo existe y pertenece al usuario
        flow = await self.repo.get_by_id(flow_id)
        if not flow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flow no encontrado"
            )
        
        if flow.owner_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para eliminar este flujo"
            )
        
        # Primero desactivar si está activo
        if flow.is_active:
            await self.orchestrator.unschedule_flow(
                flow_id,
                flow.spec,
                user_id
            )
        
        # Eliminar flujo del repositorio
        try:
            deleted = await self.repo.delete_flow(flow_id)
            return deleted
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error eliminando flujo: {str(e)}"
            )

    async def delete_flow_and_chat(self, flow_id: UUID, user_id: int) -> dict:
        """
        Elimina un flujo y su chat asociado (si existe)
        """
        # Verificar que el flujo existe y pertenece al usuario
        flow = await self.repo.get_by_id(flow_id)
        if not flow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flow no encontrado"
            )
        
        if flow.owner_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para eliminar este flujo"
            )
        
        result = {"deleted_chat_id": None}
        
        try:
            # No manejar transacciones aquí - dejar que el router/dependency injection las maneje
            # Primero desactivar si está activo
            if flow.is_active:
                await self.orchestrator.unschedule_flow(
                    flow_id,
                    flow.spec,
                    user_id
                )
            
            # Guardar chat_id antes de eliminar el flow
            chat_id = flow.chat_id
            
            # Eliminar flujo del repositorio
            deleted = await self.repo.delete_flow(flow_id)
            if not deleted:
                raise Exception("No se pudo eliminar el flujo")
            
            # Si hay un chat asociado, eliminarlo también
            if chat_id:
                await self._delete_chat_session(chat_id, user_id)
                result["deleted_chat_id"] = str(chat_id)
            
            return result
                
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error eliminando flujo y chat: {str(e)}"
            )

    async def _delete_chat_session(self, chat_id: UUID, user_id: int):
        """
        Elimina una sesión de chat y sus mensajes asociados
        """
        try:
            from sqlalchemy import text
            
            # Verificar que el chat pertenece al usuario
            verify_query = text("""
                SELECT user_id FROM chat_sessions 
                WHERE session_id = :chat_id AND user_id = :user_id
            """)
            result = await self.db.execute(verify_query, {"chat_id": chat_id, "user_id": user_id})
            
            if not result.fetchone():
                return  # Chat no existe o no pertenece al usuario
            
            # Eliminar mensajes del chat
            delete_messages_query = text("""
                DELETE FROM chat_messages WHERE session_id = :chat_id
            """)
            await self.db.execute(delete_messages_query, {"chat_id": chat_id})
            
            # Eliminar la sesión de chat
            delete_session_query = text("""
                DELETE FROM chat_sessions WHERE session_id = :chat_id AND user_id = :user_id
            """)
            await self.db.execute(delete_session_query, {"chat_id": chat_id, "user_id": user_id})
            
        except Exception as e:
            # Log el error pero no fallar la eliminación del workflow
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not delete chat session {chat_id}: {e}")
            # No re-raise - permitir que el workflow se elimine aunque el chat ya no exista

async def get_flow_service(
    repo: FlowRepository = Depends(get_flow_repository),
    orchestrator: TriggerOrchestratorService = Depends(get_trigger_orchestrator_service),
    definition_service: FlowDefinitionService = Depends(get_flow_definition_service),
    db: AsyncSession = Depends(get_db),
) -> FlowService:
    """
    ✅ LIMPIADO: Factory sin interfaces innecesarias
    """
    return FlowService(repo, orchestrator, definition_service, db)

async def create_flow_service_manual(db_session: AsyncSession) -> FlowService:
    """
    🔧 MANUAL CREATION: Crear FlowService sin Depends para uso fuera de FastAPI
    """
    import logging
    logger = logging.getLogger(__name__)
    
    from app.repositories.flow_repository import FlowRepository
    from app.services.trigger_orchestrator_service import create_trigger_orchestrator_manual
    from app.services.flow_definition_service import FlowDefinitionService
    
    # Crear instancias manualmente
    from app.repositories.flow_definition_repository import FlowDefinitionRepository
    repo = FlowRepository(db_session)
    orchestrator = await create_trigger_orchestrator_manual(db_session)
    logger.info(f"🔧 MANUAL FLOW: Created orchestrator type: {type(orchestrator)}")
    logger.info(f"🔧 MANUAL FLOW: orchestrator.cred_repo type: {type(orchestrator.cred_repo)}")
    def_repo = FlowDefinitionRepository(db_session)
    definition_service = FlowDefinitionService(def_repo)
    
    flow_service = FlowService(repo, orchestrator, definition_service, db_session)
    logger.info(f"🔧 MANUAL FLOW: Created flow_service.orchestrator type: {type(flow_service.orchestrator)}")
    logger.info(f"🔧 MANUAL FLOW: flow_service.orchestrator.cred_repo type: {type(flow_service.orchestrator.cred_repo)}")
    return flow_service
