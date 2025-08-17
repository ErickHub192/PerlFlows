from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends
from app.services.auth_policy_service import AuthPolicyService, get_auth_policy_service
from app.authenticators.registry import get_registered_class
from app.repositories.oauth_state_repository import OAuthStateRepository
from app.db.models import OAuthState
from app.db.database import get_db
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)

class OAuthService:
    def __init__(self, db: AsyncSession, auth_policy_service: AuthPolicyService):
        self.db = db
        self.auth_policy_service = auth_policy_service
        self.state_repo = OAuthStateRepository(db)
        # Fix: Add logger attribute that the code expects
        from app.exceptions.logging_utils import get_kyra_logger
        self.logger = get_kyra_logger(__name__)

    async def initiate_oauth_flow(self, service_id: str, chat_id: str, user_id: int) -> str:
        """
        Inicia flujo OAuth y retorna URL de autorización
        """
        # Get auth policy for this service_id
        auth_policy = await self.auth_policy_service.get_auth_policy_by_service_id(service_id)
        
        if not auth_policy:
            raise HTTPException(
                status_code=404,
                detail=f"No auth policy found for service_id: {service_id}"
            )
        
        if auth_policy["mechanism"] != "oauth2":
            raise HTTPException(
                status_code=400,
                detail=f"Service {service_id} does not use OAuth2 mechanism"
            )
        
        # Get authenticator class dynamically
        provider = auth_policy["provider"]
        authenticator_class = get_registered_class("oauth2", provider)
        
        if not authenticator_class:
            raise HTTPException(
                status_code=400,
                detail=f"No OAuth authenticator found for provider: {provider}"
            )
        
        # Create authenticator instance and get authorization URL
        authenticator = authenticator_class(
            user_id=user_id, 
            db=self.db, 
            auth_policy=auth_policy,
            chat_id=chat_id
        )
        auth_url = await authenticator.authorization_url()
        await self.db.commit()  # Commit the OAuth state save
        
        return auth_url

    async def handle_oauth_callback(self, code: str, state: str, service_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Maneja callback OAuth y completa el flujo
        Retorna información para respuesta HTML
        """
        # Extract user_id, service_id, and chat_id from oauth_states using state parameter
        oauth_data = await self._extract_oauth_data_from_state(state)
        
        if not oauth_data:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired OAuth state"
            )
        
        user_id, provider, extracted_service_id, extracted_chat_id = oauth_data
        
        # Use extracted service_id from state if not provided in query
        if not service_id:
            service_id = extracted_service_id
        
        # Get auth policy for this service_id
        auth_policy = await self.auth_policy_service.get_auth_policy_by_service_id(service_id)
        
        if not auth_policy:
            raise HTTPException(
                status_code=404,
                detail=f"No auth policy found for service_id: {service_id}"
            )
        
        # Get authenticator class dynamically
        provider = auth_policy["provider"]
        authenticator_class = get_registered_class("oauth2", provider)
        
        if not authenticator_class:
            raise HTTPException(
                status_code=400,
                detail=f"No OAuth authenticator found for provider: {provider}"
            )
        
        # Process token exchange
        authenticator = authenticator_class(
            user_id=user_id, 
            db=self.db, 
            auth_policy=auth_policy,
            chat_id=extracted_chat_id
        )
        
        # Pass None as state since we already validated it
        await authenticator.fetch_token(code, None)
        
        # ✅ FRONTEND MESSAGE INJECTION: No backend continuation needed
        if extracted_chat_id:
            logger.info(f"🔄 OAuth completed for user {user_id}, chat {extracted_chat_id}, service {service_id}")
            logger.info("✅ Frontend will inject continuation message automatically")
            
            # 🎯 FIX: Save OAuth completion to conversation memory
            try:
                logger.info(f"🎯 OAUTH: About to import ConversationMemoryService...")
                from app.services.conversation_memory_service import ConversationMemoryService
                logger.info(f"🎯 OAUTH: ConversationMemoryService imported successfully")
                
                logger.info(f"🎯 OAUTH: Creating ConversationMemoryService instance...")
                memory_service = ConversationMemoryService()
                logger.info(f"🎯 OAUTH: ConversationMemoryService instance created: {memory_service}")
                
                logger.info(f"🎯 OAUTH: Calling save_oauth_completion...")
                await memory_service.save_oauth_completion(
                    self.db, extracted_chat_id, user_id, [service_id]
                )
                logger.info(f"🎯 OAUTH MEMORY: Saved {service_id} completion to chat {extracted_chat_id}")
            except Exception as e:
                logger.error(f"🎯 OAUTH MEMORY ERROR: Failed to save OAuth completion: {e}")
                logger.error(f"🎯 OAUTH MEMORY ERROR DETAILS: {str(e)}", exc_info=True)
                raise
        
        # 🎯 AUTO OAUTH CONTINUATION: Check if there are still pending OAuth requirements
        continuation_success = False
        if extracted_chat_id:
            try:
                self.logger.logger.info(f"🎯 OAUTH CHECK: Verifying if more OAuth requirements are pending for chat {extracted_chat_id}")
                
                # ✅ FIX: Check if there are still missing OAuth requirements before calling LLM
                from app.services.auto_auth_trigger import AutoAuthTrigger
                from app.services.conversation_memory_service import ConversationMemoryService
                
                # Get the current workflow steps from memory to check remaining OAuth
                memory_service = ConversationMemoryService()
                memory_context = await memory_service.load_memory_context(self.db, extracted_chat_id)
                
                if memory_context and memory_context.get('workflow_steps'):
                    workflow_steps = memory_context['workflow_steps']
                    
                    # Convert workflow steps to selected_steps format for AutoAuthTrigger
                    selected_steps = []
                    for step in workflow_steps:
                        if step.get('action_id') and step.get('node_id'):
                            selected_steps.append({
                                'action_id': step.get('action_id'),
                                'node_id': step.get('node_id')
                            })
                    
                    # Check for remaining missing OAuth requirements
                    from app.services.auth_handler_registry import get_auth_handler_registry
                    from app.services.credential_service import CredentialService
                    from app.repositories.credential_repository import get_credential_repository
                    
                    auth_handler_registry = get_auth_handler_registry()
                    credential_repo = get_credential_repository(self.db)
                    credential_service = CredentialService(credential_repo)
                    auto_auth_trigger = AutoAuthTrigger(
                        db=self.db, 
                        auth_policy_service=self.auth_policy_service, 
                        credential_service=credential_service, 
                        auth_handler_registry=auth_handler_registry
                    )
                    missing_oauth_items = await auto_auth_trigger.check_missing_oauth_for_selected_steps(
                        user_id=user_id,
                        selected_steps=selected_steps,
                        chat_id=extracted_chat_id
                    )
                    
                    self.logger.logger.info(f"🎯 OAUTH CHECK: Found {len(missing_oauth_items)} missing OAuth items after {service_id} completion")
                    
                    if missing_oauth_items:
                        # Still have pending OAuth requirements - DON'T call LLM yet
                        self.logger.logger.info(f"🔄 OAUTH PENDING: Still have {len(missing_oauth_items)} OAuth requirements pending:")
                        for item in missing_oauth_items:
                            self.logger.logger.info(f"  - {item.service_id}: {item.message}")
                        self.logger.logger.info(f"🔄 OAUTH PENDING: NOT calling LLM yet - waiting for remaining OAuth to complete")
                        continuation_success = False
                    else:
                        # ALL OAuth requirements satisfied - NOW call LLM with full discovery
                        self.logger.logger.info(f"🎉 OAUTH COMPLETE: ALL OAuth requirements satisfied! Triggering LLM with full discovery context")
                        
                        # Import and trigger continuation via chat service
                        from app.services.chat_service_clean import ChatService
                        from app.ai.llm_clients.llm_service import get_llm_service
                        from app.services.chat_session_service import get_chat_session_service
                        
                        # Create service instances directly instead of using FastAPI DI
                        llm_service = get_llm_service()  # No await - it's synchronous
                        chat_session_service = await get_chat_session_service(self.db)
                        chat_service = ChatService(llm_service, chat_session_service)
                        
                        # Create system message to continue workflow automatically
                        continuation_message = f"All OAuth completed. Continue workflow with full discovery context."
                        
                        # Convert chat_id to UUID if it's a string
                        from uuid import UUID
                        if isinstance(extracted_chat_id, str):
                            chat_uuid = UUID(extracted_chat_id)
                        else:
                            chat_uuid = extracted_chat_id
                        
                        # Get list of all completed OAuth services from memory
                        oauth_completed_services = memory_context.get('oauth_completed', [])
                        if service_id not in oauth_completed_services:
                            oauth_completed_services.append(service_id)
                        
                        # Auto-send continuation message to trigger LLM call with ALL OAuth completed
                        result = await chat_service.process_chat(
                            session_id=chat_uuid,
                            user_message=continuation_message,
                            conversation=[],  # Empty conversation for auto-continuation
                            user_id=user_id,
                            db_session=self.db,
                            oauth_completed=oauth_completed_services,  # ALL completed OAuth services
                            system_message=f"OAUTH_COMPLETION: All OAuth requirements satisfied. OAuth completed for services: {', '.join(oauth_completed_services)}. Workflow can now continue with full discovery and credential access.",
                            continue_workflow=True
                        )
                        
                        continuation_success = True
                        self.logger.logger.info(f"🎯 OAUTH AUTO-TRIGGER SUCCESS: Full workflow continuation triggered for chat {extracted_chat_id} with {len(oauth_completed_services)} OAuth services")
                else:
                    self.logger.logger.warning(f"🔄 OAUTH CHECK: No workflow steps found in memory for chat {extracted_chat_id}")
                    continuation_success = False
                
            except Exception as e:
                self.logger.logger.error(f"🎯 OAUTH AUTO-TRIGGER ERROR: Failed to trigger continuation: {e}")
                continuation_success = False

        return {
            "user_id": user_id,
            "service_id": service_id,
            "provider": provider,
            "chat_id": extracted_chat_id,
            "continuation_triggered": continuation_success
        }

    async def _extract_oauth_data_from_state(self, state: str) -> Optional[tuple]:
        """
        Extrae user_id, provider, service_id, y chat_id del OAuth state
        """
        oauth_data = await self.state_repo.get_oauth_state_by_state(state)
        logger.info(f"🔍 OAuth callback debug - state: {state}, oauth_data: {oauth_data}")
        
        if oauth_data:
            if len(oauth_data) >= 4:
                user_id, provider, extracted_service_id, extracted_chat_id = oauth_data[:4]
                logger.info(f"✅ OAuth data found - user_id: {user_id}, provider: {provider}, service_id: {extracted_service_id}, chat_id: {extracted_chat_id}")
                # Clean up the used state
                await self.state_repo.delete_oauth_state_by_state(state)
                await self.db.commit()
                return user_id, provider, extracted_service_id, extracted_chat_id
            else:
                # Fallback for old records without chat_id
                user_id, provider, extracted_service_id = oauth_data[:3]
                logger.info(f"✅ OAuth data found (legacy) - user_id: {user_id}, provider: {provider}, service_id: {extracted_service_id}")
                await self.state_repo.delete_oauth_state_by_state(state)
                await self.db.commit()
                return user_id, provider, extracted_service_id, None
        else:
            logger.info(f"❌ No OAuth data found for state: {state}")
            return None


# Factory para FastAPI DI
def get_oauth_service(
    db: AsyncSession = Depends(get_db),
    auth_policy_service: AuthPolicyService = Depends(get_auth_policy_service)
) -> OAuthService:
    """
    Factory para inyección de dependencias
    """
    return OAuthService(db, auth_policy_service)