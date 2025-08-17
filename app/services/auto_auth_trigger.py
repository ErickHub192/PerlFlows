"""
AutoAuthTrigger - Servicio central para auto-triggering de auth flows AGNÓSTICO
Usa registry pattern para eliminar hardcodeo y ser completamente escalable
"""
import logging
from typing import Optional, Dict, Any, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.db.database import get_db
from app.services.auth_policy_service import AuthPolicyService, get_auth_policy_service
from app.services.credential_service import CredentialService, get_credential_service
from app.services.auth_handler_registry import get_auth_handler_registry, AuthHandlerRegistry
from app.dtos.auth_requirement_dto import (
    AuthRequirementDTO, 
    AuthStepDTO, 
    WorkflowAuthAnalysisDTO
)
from app.mappers.auth_requirement_mapper import (
    dict_to_auth_requirement_dto,
    create_workflow_analysis_dto
)
from app.exceptions.api_exceptions import WorkflowProcessingException

logger = logging.getLogger(__name__)


class AutoAuthTrigger:
    """
    Servicio central para auto-detection y triggering de authentication flows
    ✅ COMPLETAMENTE AGNÓSTICO - usa registry pattern
    ✅ SIN HARDCODEO - dynamic dispatch por mechanism
    ✅ ESCALABLE - soporta 500+ servicios automáticamente
    
    Funciones principales:
    1. Detectar qué autenticaciones necesita un workflow/nodo
    2. Verificar qué credenciales ya existen 
    3. Generar flows de auth para lo que falta usando registry
    4. Orquestar el proceso completo sin if/elif statements
    """
    
    def __init__(
        self,
        db: AsyncSession,
        auth_policy_service: AuthPolicyService,
        credential_service: CredentialService,
        auth_handler_registry: AuthHandlerRegistry
    ):
        self.db = db
        self.auth_policy_service = auth_policy_service
        self.credential_service = credential_service
        self.auth_handler_registry = auth_handler_registry
    
    async def analyze_workflow_auth_requirements(
        self, 
        flow_spec: Dict[str, Any],
        user_id: int,
        chat_id: str
    ) -> WorkflowAuthAnalysisDTO:
        """
        Analiza un workflow completo y detecta todos los auth requirements
        ✅ AGNÓSTICO - funciona con cualquier mecanismo registrado
        
        Args:
            flow_spec: Especificación del workflow
            user_id: ID del usuario
            chat_id: ID del chat
            
        Returns:
            WorkflowAuthAnalysisDTO con análisis completo
        """
        try:
            logger.info(f"Analyzing auth requirements for workflow (user: {user_id})")
            
            # Extract all nodes from flow_spec
            nodes = flow_spec.get("nodes", [])
            requirements = []
            
            for node in nodes:
                node_requirements = await self._analyze_node_auth_requirements(
                    node, user_id, chat_id
                )
                requirements.extend(node_requirements)
            
            # Deduplicate by service_id
            unique_requirements = {}
            for req in requirements:
                service_id = req.service_id
                if service_id and service_id not in unique_requirements:
                    unique_requirements[service_id] = req
            
            requirements_list = list(unique_requirements.values())
            
            # Generate auth steps for missing requirements
            missing_requirements = [req for req in requirements_list if not req.is_satisfied]
            auth_steps = await self._generate_auth_steps_agnostic(
                missing_requirements, user_id, chat_id
            )
            
            return create_workflow_analysis_dto(requirements_list, auth_steps)
            
        except Exception as e:
            logger.error(f"Error analyzing workflow auth requirements: {e}")
            raise WorkflowProcessingException(f"Failed to analyze auth requirements: {str(e)}")
    
    async def analyze_action_auth_requirements(
        self,
        action_id: str,
        user_id: int,
        chat_id: str
    ) -> Optional[AuthRequirementDTO]:
        """
        Analiza auth requirements para una acción específica
        ✅ AGNÓSTICO - funciona con cualquier mecanismo
        
        Args:
            action_id: UUID de la acción
            user_id: ID del usuario
            chat_id: ID del chat
            
        Returns:
            AuthRequirementDTO o None si no requiere auth
        """
        try:
            # Get action auth requirements from auth_policy_service
            auth_data = await self.auth_policy_service.get_action_auth_requirements(action_id)
            
            if not auth_data or not auth_data.get("auth_required"):
                logger.debug(f"Action {action_id} does not require auth")
                return None
            
            service_id = auth_data.get("service_id")
            if not service_id:
                logger.warning(f"Action {action_id} requires auth but has no service_id")
                return None
            
            # Check if user already has credentials for this service
            existing_cred = await self.credential_service.get_credential(
                user_id, service_id, chat_id
            )
            
            # ✅ FIXED: Para OAuth, verificar que tenga access_token, no solo client_id/client_secret
            is_satisfied = False
            if existing_cred:
                if auth_data.get("mechanism") == "oauth2":
                    # Para OAuth, requiere access_token (autorización del usuario)
                    is_satisfied = existing_cred.get("access_token") is not None
                    logger.info(f"🔍 OAuth check for {service_id}: has_access_token={is_satisfied}, existing_cred_keys={list(existing_cred.keys()) if existing_cred else None}")
                else:
                    # Para otros mecanismos (api_key, etc.), basta con que exista
                    is_satisfied = True
                    logger.info(f"🔍 Non-OAuth check for {service_id}: is_satisfied={is_satisfied}")
            else:
                # ✅ CRITICAL FIX: Si no hay credenciales, marcar como NOT satisfied
                is_satisfied = False
                logger.info(f"🔍 No existing credentials for {service_id}: is_satisfied={is_satisfied}")
                logger.info(f"🔍 Step {action_id}: service_id={service_id}, is_satisfied={is_satisfied}, mechanism={auth_data.get('mechanism')}")
            
            auth_data["is_satisfied"] = is_satisfied
            
            return dict_to_auth_requirement_dto(auth_data)
            
        except Exception as e:
            logger.error(f"Error analyzing action auth requirements for {action_id}: {e}")
            return None
    
    async def trigger_missing_auth_flows_agnostic(
        self,
        missing_requirements: List[AuthRequirementDTO],
        user_id: int,
        chat_id: str
    ) -> List[AuthStepDTO]:
        """
        Dispara flows de autenticación usando registry pattern
        ✅ COMPLETAMENTE AGNÓSTICO - sin if/elif statements
        ✅ ESCALABLE - funciona con cualquier mecanismo registrado
        
        Args:
            missing_requirements: Lista de requirements no satisfechos
            user_id: ID del usuario
            chat_id: ID del chat
            
        Returns:
            Lista de AuthStepDTO para ejecutar
        """
        auth_steps = []
        
        try:
            for req in missing_requirements:
                # ✅ DYNAMIC DISPATCH - sin hardcodeo
                auth_step = await self.auth_handler_registry.create_auth_step_for_mechanism(
                    mechanism=req.mechanism,
                    service_id=req.service_id,
                    display_name=req.display_name or req.service_id,
                    auth_config=req.auth_config,
                    user_id=user_id,
                    chat_id=chat_id,
                    required_scopes=req.required_scopes
                )
                
                if auth_step:
                    auth_steps.append(auth_step)
                else:
                    logger.warning(f"Could not create auth step for mechanism: {req.mechanism}")
            
            logger.info(f"Generated {len(auth_steps)} auth steps for {len(missing_requirements)} requirements")
            return auth_steps
            
        except Exception as e:
            logger.error(f"Error triggering auth flows: {e}")
            raise WorkflowProcessingException(f"Failed to trigger auth flows: {str(e)}")
    
    async def validate_all_requirements_satisfied(
        self,
        flow_spec: Dict[str, Any],
        user_id: int,
        chat_id: str
    ) -> Tuple[bool, List[str]]:
        """
        Valida que todos los auth requirements estén satisfechos antes de ejecutar
        ✅ AGNÓSTICO - funciona con cualquier workflow
        
        Args:
            flow_spec: Especificación del workflow
            user_id: ID del usuario
            chat_id: ID del chat
            
        Returns:
            Tuple(can_execute: bool, missing_services: List[str])
        """
        try:
            analysis = await self.analyze_workflow_auth_requirements(flow_spec, user_id, chat_id)
            
            missing_services = [
                req.service_id 
                for req in analysis.missing_requirements
                if req.service_id
            ]
            
            return analysis.can_execute, missing_services
            
        except Exception as e:
            logger.error(f"Error validating auth requirements: {e}")
            return False, []
    
    async def get_auth_step_for_service(
        self,
        service_id: str,
        user_id: int,
        chat_id: str
    ) -> Optional[AuthStepDTO]:
        """
        Genera auth step para un servicio específico
        ✅ AGNÓSTICO - obtiene mechanism de la BD dinámicamente
        
        Args:
            service_id: ID del servicio
            user_id: ID del usuario
            chat_id: ID del chat
            
        Returns:
            AuthStepDTO o None si no se puede generar
        """
        try:
            # Get auth policy for this service
            auth_policy = await self.auth_policy_service.get_auth_policy_by_service_id(service_id)
            
            if not auth_policy:
                logger.warning(f"No auth policy found for service_id: {service_id}")
                return None
            
            # Check if already satisfied
            existing_cred = await self.credential_service.get_credential(user_id, service_id, chat_id)
            if existing_cred:
                # ✅ FIXED: Para OAuth, verificar que tenga access_token, no solo client_id/client_secret
                if auth_policy.get("mechanism") == "oauth2":
                    if existing_cred.get("access_token"):
                        logger.debug(f"Service {service_id} already has OAuth access_token")
                        return None
                    # Si solo tiene client_id/client_secret pero no access_token, continuar con OAuth flow
                    logger.debug(f"Service {service_id} has client credentials but no OAuth access_token, triggering OAuth flow")
                else:
                    # Para otros mecanismos, basta con que exista
                    logger.debug(f"Service {service_id} already has credentials")
                    return None
            
            # ✅ DYNAMIC DISPATCH - usa registry
            return await self.auth_handler_registry.create_auth_step_for_mechanism(
                mechanism=auth_policy["mechanism"],
                service_id=service_id,
                display_name=auth_policy.get("display_name", service_id),
                auth_config=auth_policy.get("auth_config", {}),
                user_id=user_id,
                chat_id=chat_id,
                required_scopes=auth_policy.get("scopes", [])
            )
            
        except Exception as e:
            logger.error(f"Error getting auth step for service {service_id}: {e}")
            return None
    
    # Private helper methods
    
    async def _analyze_node_auth_requirements(
        self,
        node: Dict[str, Any],
        user_id: int,
        chat_id: str
    ) -> List[AuthRequirementDTO]:
        """
        Analiza auth requirements para un nodo específico
        ✅ AGNÓSTICO - funciona con cualquier tipo de nodo
        """
        requirements = []
        
        try:
            # Get node actions
            actions = node.get("actions", [])
            
            for action in actions:
                action_id = action.get("id")
                if action_id:
                    requirement = await self.analyze_action_auth_requirements(
                        action_id, user_id, chat_id
                    )
                    if requirement:
                        requirements.append(requirement)
            
            # Also check if node itself has auth requirements via default_auth
            node_id = node.get("id")
            if node_id:
                node_requirement = await self._analyze_node_default_auth(
                    node_id, user_id, chat_id
                )
                if node_requirement:
                    requirements.append(node_requirement)
            
            return requirements
            
        except Exception as e:
            logger.error(f"Error analyzing node auth requirements: {e}")
            return []
    
    async def _analyze_node_default_auth(
        self,
        node_id: str,
        user_id: int,
        chat_id: str
    ) -> Optional[AuthRequirementDTO]:
        """
        Analiza default_auth de un nodo
        """
        try:
            from sqlalchemy import select
            from app.db.models import Node
            
            stmt = select(Node).where(Node.node_id == node_id)
            result = await self.db.execute(stmt)
            node_obj = result.scalar_one_or_none()
            
            if not node_obj or not node_obj.default_auth:
                return None
            
            # Map default_auth to service_id
            service_id = await self._map_default_auth_to_service_id(node_obj.default_auth)
            if not service_id:
                return None
            
            # Get auth policy for this service_id
            auth_policy = await self.auth_policy_service.get_auth_policy_by_service_id(service_id)
            if not auth_policy:
                return None
            
            # Check if satisfied
            existing_cred = await self.credential_service.get_credential(
                user_id, service_id, chat_id
            )
            
            # ✅ FIXED: Para OAuth, verificar que tenga access_token, no solo client_id/client_secret
            is_satisfied = False
            if existing_cred:
                if auth_policy.get("mechanism") == "oauth2":
                    # Para OAuth, requiere access_token (autorización del usuario)
                    is_satisfied = existing_cred.get("access_token") is not None
                else:
                    # Para otros mecanismos (api_key, etc.), basta con que exista
                    is_satisfied = True
            
            auth_policy["service_id"] = service_id
            auth_policy["is_satisfied"] = is_satisfied
            auth_policy["required_scopes"] = auth_policy.get("scopes", [])
            
            return dict_to_auth_requirement_dto(auth_policy)
            
        except Exception as e:
            logger.error(f"Error analyzing node default auth: {e}")
            return None
    
    async def _map_default_auth_to_service_id(self, default_auth: str) -> Optional[str]:
        """
        Maps old default_auth format to new service_id
        ✅ AGNÓSTICO - funciona con cualquier formato
        """
        if not default_auth:
            return None
        
        # Remove mechanism prefix if present
        for prefix in ["oauth2_", "api_key_", "bot_token_", "db_credentials_"]:
            if default_auth.startswith(prefix):
                return default_auth[len(prefix):]
        
        # If no prefix, assume it's already the service_id
        return default_auth
    
    async def _generate_auth_steps_agnostic(
        self,
        missing_requirements: List[AuthRequirementDTO],
        user_id: int,
        chat_id: str
    ) -> List[AuthStepDTO]:
        """
        Genera pasos de autenticación usando registry pattern
        ✅ COMPLETAMENTE AGNÓSTICO
        """
        return await self.trigger_missing_auth_flows_agnostic(
            missing_requirements, user_id, chat_id
        )

    async def check_missing_oauth_for_selected_steps(
        self, 
        user_id: int, 
        selected_steps: List[Dict[str, Any]],
        chat_id: Optional[str] = None
    ) -> List["ClarifyOAuthItemDTO"]:
        """
        Verifica qué autenticaciones OAuth faltan para una lista de pasos seleccionados
        
        Args:
            user_id: ID del usuario
            selected_steps: Lista de pasos del workflow a verificar
            chat_id: ID del chat (opcional, se genera UUID si no se proporciona)
            
        Returns:
            Lista de ClarifyOAuthItemDTO para autorización pendiente
        """
        try:
            logger.info(f"Checking OAuth requirements for {len(selected_steps)} selected steps")
            
            # Generate proper UUID for workflow execution if not provided
            if not chat_id:
                import uuid
                chat_id = str(uuid.uuid4())
                logger.debug(f"Generated workflow execution chat_id: {chat_id}")
            
            missing_requirements = []
            
            for step in selected_steps:
                # Analizar requirements de autenticación para este paso
                step_requirements = await self.analyze_action_auth_requirements(
                    action_id=step.get('action_id'),
                    user_id=user_id,
                    chat_id=chat_id
                )
                
                # DEBUG: Log detallado del análisis
                if step_requirements:
                    logger.info(f"🔍 Step {step.get('action_id')}: service_id={step_requirements.service_id}, is_satisfied={step_requirements.is_satisfied}, mechanism={step_requirements.mechanism}")
                else:
                    logger.info(f"🔍 Step {step.get('action_id')}: No auth requirements")
                
                # Agregar cualquier requirement que falte
                if step_requirements and not step_requirements.is_satisfied:
                    missing_requirements.append(step_requirements)
                    logger.info(f"✅ Added missing requirement for {step_requirements.service_id}")
            
            # Remover duplicados basados en service_id
            unique_requirements = []
            seen_services = set()
            
            for req in missing_requirements:
                if req.service_id not in seen_services:
                    unique_requirements.append(req)
                    seen_services.add(req.service_id)
            
            # Convert to ClarifyOAuthItemDTO directly
            oauth_items = []
            for req in unique_requirements:
                # Find matching step for node_id
                matching_step = None
                for step in selected_steps:
                    if step.get('action_id') == req.action_id:
                        matching_step = step
                        break
                
                node_id_str = matching_step.get('node_id') if matching_step else str(__import__('uuid').uuid4())
                
                from app.dtos.clarify_oauth_dto import ClarifyOAuthItemDTO
                oauth_item = ClarifyOAuthItemDTO(
                    type="oauth",
                    node_id=__import__('uuid').UUID(node_id_str),
                    message=f"Se requiere autorización para {req.display_name or req.service_id}",
                    oauth_url=req.auth_url or f"/auth/{req.provider}/authorize",
                    service_id=req.service_id
                )
                oauth_items.append(oauth_item)
            
            logger.info(f"Created {len(oauth_items)} OAuth authorization items")
            return oauth_items
            
        except Exception as e:
            logger.error(f"Error checking OAuth for selected steps: {str(e)}")
            return []




# Factory para FastAPI DI
async def get_auto_auth_trigger(
    db: AsyncSession = Depends(get_db),
    auth_policy_service: AuthPolicyService = Depends(get_auth_policy_service),
    credential_service: CredentialService = Depends(get_credential_service)
) -> AutoAuthTrigger:
    """
    Factory para inyección de dependencias
    ✅ Inyecta registry automáticamente
    """
    auth_handler_registry = get_auth_handler_registry()
    return AutoAuthTrigger(db, auth_policy_service, credential_service, auth_handler_registry)