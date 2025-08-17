from uuid import UUID
from typing import List, Optional
from sqlalchemy import update, select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.db.models import Flow, ChatSession
from app.db.database import get_db
from fastapi import Depends, HTTPException, status
class FlowRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_owner(self, owner_id: int) -> List[Flow]:
        q = select(Flow).where(Flow.owner_id == owner_id)
        res = await self.db.execute(q)
        return res.scalars().all()

    async def list_by_owner_with_chat(self, owner_id: int) -> List[Flow]:
        """Lista flows con información del chat asociado"""
        q = (
            select(Flow)
            .options(joinedload(Flow.chat_session))
            .where(Flow.owner_id == owner_id)
            .order_by(Flow.created_at.desc())
        )
        res = await self.db.execute(q)
        return res.scalars().unique().all()

    async def list_all(self) -> List[Flow]:
        """Lista todos los flows para limpieza administrativa"""
        q = select(Flow)
        res = await self.db.execute(q)
        return res.scalars().all()

    async def delete_flow(self, flow_id: UUID) -> bool:
        """Elimina un flow por ID y retorna True si se eliminó exitosamente"""
        q = delete(Flow).where(Flow.flow_id == flow_id)
        result = await self.db.execute(q)
        await self.db.flush()
        return result.rowcount > 0  # True si se eliminó al menos una fila

    async def update_flow_status(self, flow_id: UUID, is_active: bool) -> None:
        """Actualiza solo el estado activo de un flow"""
        q = (
            update(Flow)
            .where(Flow.flow_id == flow_id)
            .values(is_active=is_active, updated_at=func.now())
        )
        await self.db.execute(q)
        await self.db.flush()

    async def update_flow(self, flow_id: UUID, name: str, spec: dict, description: str = None) -> Flow:
        """Actualiza un flow completo"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"🔄 REPO UPDATE: update_flow for flow_id {flow_id}, name: {name}")
        logger.info(f"🔄 REPO UPDATE STATE: db.is_active: {self.db.is_active}, in_transaction: {self.db.in_transaction()}")
        
        # Preparar valores para actualizar
        update_values = {
            "name": name,
            "spec": spec,
            "updated_at": func.now()
        }
        
        # 🔧 FIX: Flow model doesn't have description field, store it in spec metadata instead
        if description:
            if "metadata" not in spec:
                spec["metadata"] = {}
            spec["metadata"]["description"] = description
            update_values["spec"] = spec
        
        logger.info(f"🔄 REPO UPDATE PRE-UPDATE: About to update flow")
        q = (
            update(Flow)
            .where(Flow.flow_id == flow_id)
            .values(**update_values)
            .returning(Flow)
        )
        result = await self.db.execute(q)
        logger.info(f"🔄 REPO UPDATE POST-UPDATE: Flow updated successfully")
        
        # ✅ Repository no maneja transacciones - solo flush
        logger.info(f"🔄 REPO UPDATE PRE-FLUSH: About to flush session")
        logger.info(f"🔄 REPO UPDATE PRE-FLUSH STATE: db.in_transaction: {self.db.in_transaction()}")
        await self.db.flush()
        logger.info(f"🔄 REPO UPDATE POST-FLUSH: Session flushed successfully")
        logger.info(f"🔄 REPO UPDATE POST-FLUSH STATE: db.in_transaction: {self.db.in_transaction()}")
        
        updated_flow = result.scalar_one()
        logger.info(f"🔄 REPO UPDATE SUCCESS: Returning updated flow with ID: {updated_flow.flow_id}")
        return updated_flow

    async def get_by_chat_id(self, owner_id: int, chat_id: UUID) -> Optional[Flow]:
        """
        Recupera el flow MÁS RECIENTE por chat_id y owner_id
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"🔍 REPO LOOKUP: get_by_chat_id for owner {owner_id}, chat_id: {chat_id}")
        
        try:
            # 🔧 FIX: ORDER BY created_at DESC para obtener el MÁS RECIENTE
            query = select(Flow).where(
                Flow.owner_id == owner_id,
                Flow.chat_id == chat_id
            ).order_by(Flow.created_at.desc())
            
            result = await self.db.execute(query)
            
            # 🔧 FIX: Use first() instead of scalar_one_or_none() to handle multiple rows gracefully
            # This gets the most recent workflow and ignores duplicates
            flow_row = result.first()
            flow = flow_row[0] if flow_row else None
            
            if flow:
                logger.info(f"🔍 REPO FOUND: Found LATEST flow {flow.flow_id} for chat_id {chat_id} (created: {flow.created_at})")
            else:
                logger.info(f"🔍 REPO NOT FOUND: No flow found for chat_id {chat_id}")
                
            return flow
            
        except Exception as e:
            logger.error(f"🔍 REPO LOOKUP ERROR: {e}")
            # 🔧 ADDITIONAL FIX: Fallback with limit(1) to ensure single result
            try:
                logger.info(f"🔍 REPO FALLBACK: Attempting fallback query for chat_id {chat_id}")
                fallback_query = select(Flow).where(
                    Flow.owner_id == owner_id,
                    Flow.chat_id == chat_id
                ).order_by(Flow.created_at.desc()).limit(1)
                fallback_result = await self.db.execute(fallback_query)
                fallback_row = fallback_result.first()
                fallback_flow = fallback_row[0] if fallback_row else None
                if fallback_flow:
                    logger.info(f"🔍 REPO FALLBACK SUCCESS: Found flow {fallback_flow.flow_id}")
                return fallback_flow
            except Exception as fallback_error:
                logger.error(f"🔍 REPO FALLBACK ERROR: {fallback_error}")
                return None

    async def set_active(self, flow_id: UUID, is_active: bool) -> Flow:
        q = (
            update(Flow)
            .where(Flow.flow_id == flow_id)
            .values(is_active=is_active, updated_at=func.now())
            .returning(Flow)
        )
        res = await self.db.execute(q)
        # ✅ Repository no maneja transacciones - solo flush
        await self.db.flush()
        return res.scalar_one()
    
    async def get_by_id(self, flow_id: UUID, owner_id: UUID | None = None) -> Flow:
        q = select(Flow).where(Flow.flow_id == flow_id)
        if owner_id is not None:
            q = q.where(Flow.owner_id == owner_id)
        res = await self.db.execute(q)
        flow = res.scalar_one_or_none()
        if not flow:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flujo no encontrado")
        return flow

    async def update_trigger_id(self, flow_id: UUID, trigger_id: str | None) -> None:
        q = (
            update(Flow)
            .where(Flow.flow_id == flow_id)
            .values(trigger_id=trigger_id, updated_at=func.now())
        )
        await self.db.execute(q)
        # ✅ Repository no maneja transacciones - solo flush
        await self.db.flush()

    async def create_flow(self, name: str, owner_id: int, spec: dict, description: str = None, chat_id: UUID = None) -> Flow:
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"🔄 REPO START: create_flow for user {owner_id}, name: {name}")
        logger.info(f"🔄 REPO STATE: db.is_active: {self.db.is_active}, in_transaction: {self.db.in_transaction()}")
        
        # 🔧 FIX: Flow model doesn't have description field, store it in spec metadata instead
        if description:
            if "metadata" not in spec:
                spec["metadata"] = {}
            spec["metadata"]["description"] = description
        
        flow = Flow(
            name=name, 
            owner_id=owner_id, 
            spec=spec, 
            is_active=False,
            chat_id=chat_id
        )
        
        logger.info(f"🔄 REPO PRE-ADD: About to add flow to session")
        self.db.add(flow)
        logger.info(f"🔄 REPO POST-ADD: Flow added to session")
        
        # ✅ Repository no maneja transacciones - solo flush para obtener ID
        logger.info(f"🔄 REPO PRE-FLUSH: About to flush session")
        logger.info(f"🔄 REPO PRE-FLUSH STATE: db.in_transaction: {self.db.in_transaction()}")
        await self.db.flush()
        logger.info(f"🔄 REPO POST-FLUSH: Session flushed successfully")
        logger.info(f"🔄 REPO POST-FLUSH STATE: db.in_transaction: {self.db.in_transaction()}")
        
        logger.info(f"🔄 REPO PRE-REFRESH: About to refresh flow")
        await self.db.refresh(flow)
        logger.info(f"🔄 REPO POST-REFRESH: Flow refreshed with ID: {flow.flow_id}")
        
        logger.info(f"🔄 REPO SUCCESS: Returning flow with ID: {flow.flow_id}")
        return flow
    
async def get_flow_repository(
    db: AsyncSession = Depends(get_db),
) -> FlowRepository:
    return FlowRepository(db)    
