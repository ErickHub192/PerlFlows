# app/services/intelligent_llm_service.py

import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.ai.llm_clients.llm_service import LLMService
from app.ai.llm_factory import LLMClientFactory
from app.core.config import settings
from app.repositories.llm_model_repository import LLMModelRepository
from app.repositories.llm_provider_repository import LLMProviderRepository
from app.repositories.llm_usage_repository import LLMUsageRepository
from app.dtos.llm_usage_dto import LLMUsageInputDTO
from app.exceptions.api_exceptions import WorkflowProcessingException
class IntelligentLLMService:
    """
    Enhanced LLM Service for USER-SELECTED models and agents.
    
    This is separate from Kyra's internal LLMService:
    - Kyra internal operations: Use LLMService with settings.DEFAULT_LLM_MODEL
    - User agents/Bill/custom: Use IntelligentLLMService with user-selected models
    
    Features: intelligent model selection, cost tracking, usage analytics
    """
    
    def __init__(
        self,
        model_repo: LLMModelRepository,
        provider_repo: LLMProviderRepository,
        usage_repo: LLMUsageRepository
    ):
        self.model_repo = model_repo
        self.provider_repo = provider_repo
        self.usage_repo = usage_repo
        self.logger = logging.getLogger(__name__)
        
        # Cache for models and providers
        self._model_cache = {}
        self._provider_cache = {}
    
    async def run_with_model_selection(
        self,
        system_prompt: str,
        short_term: List[Dict[str, Any]],
        long_term: List[Dict[str, Any]],
        user_prompt: str,
        user_id: int,
        model_key: Optional[str] = None,
        temperature: float = 0.0,
        mode: str | None = None,
        auto_select_model: bool = True
    ) -> Dict[str, Any]:
        """
        Run LLM with intelligent model selection and usage tracking
        """
        start_time = time.perf_counter()
        
        try:
            # 1. Select the best model for this request
            selected_model = await self._select_model(
                model_key=model_key,
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                auto_select=auto_select_model
            )
            
            if not selected_model:
                raise WorkflowProcessingException("No suitable model found for this request")
            
            # 2. Get provider information
            provider = await self._get_provider(selected_model.provider_key)
            if not provider:
                raise WorkflowProcessingException(f"Provider {selected_model.provider_key} not found")
            
            # 3. Create LLM service with selected model
            llm_service = await self._create_llm_service(selected_model, provider)
            
            # 4. Calculate estimated cost
            estimated_input_tokens = self._estimate_tokens(system_prompt + user_prompt)
            estimated_cost = (estimated_input_tokens / 1000) * selected_model.cost_per_1k_input_tokens
            
            self.logger.info(
                f"Using model {selected_model.model_key} from {provider.name} "
                f"(estimated cost: ${estimated_cost:.4f})"
            )
            
            # 5. Run the LLM
            response = await llm_service.run(
                system_prompt=system_prompt,
                short_term=short_term,
                long_term=long_term,
                user_prompt=user_prompt,
                temperature=temperature,
                mode=mode
            )
            
            # 6. Calculate actual metrics
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            actual_input_tokens = self._estimate_tokens(system_prompt + user_prompt)
            actual_output_tokens = self._estimate_tokens(str(response))
            actual_cost = self._calculate_actual_cost(
                selected_model, actual_input_tokens, actual_output_tokens
            )
            
            # 7. Log usage for analytics
            await self._log_usage(
                user_id=user_id,
                model=selected_model,
                provider=provider,
                input_tokens=actual_input_tokens,
                output_tokens=actual_output_tokens,
                cost=actual_cost,
                duration_ms=duration_ms,
                success=True
            )
            
            # 8. Add metadata to response
            response["_llm_metadata"] = {
                "model_key": selected_model.model_key,
                "model_name": selected_model.name,
                "provider_key": provider.provider_key,
                "provider_name": provider.name,
                "input_tokens": actual_input_tokens,
                "output_tokens": actual_output_tokens,
                "total_tokens": actual_input_tokens + actual_output_tokens,
                "cost": actual_cost,
                "duration_ms": duration_ms,
                "context_length": selected_model.context_length,
                "is_recommended": selected_model.is_recommended
            }
            
            return response
            
        except Exception as e:
            # Log failed usage
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            if 'selected_model' in locals() and 'provider' in locals():
                await self._log_usage(
                    user_id=user_id,
                    model=selected_model,
                    provider=provider,
                    input_tokens=0,
                    output_tokens=0,
                    cost=0.0,
                    duration_ms=duration_ms,
                    success=False,
                    error_message=str(e)
                )
            
            self.logger.error(f"Error in intelligent LLM service: {e}", exc_info=True)
            raise
    
    async def _select_model(
        self,
        model_key: Optional[str] = None,
        user_prompt: str = "",
        system_prompt: str = "",
        auto_select: bool = True
    ):
        """Select the best model for the request"""
        
        # If specific model requested, use it
        if model_key:
            model = await self.model_repo.get_by_model_key(model_key)
            if model and model.is_active:
                return model
            else:
                self.logger.warning(f"Requested model {model_key} not found or inactive")
        
        # Auto-select best model
        if auto_select:
            return await self._auto_select_model(user_prompt, system_prompt)
        
        # Fallback to default model
        default_models = await self.model_repo.get_recommended_models()
        if default_models:
            return default_models[0]
        
        # Last resort - any active model
        all_models = await self.model_repo.get_all_active()
        return all_models[0] if all_models else None
    
    async def _auto_select_model(self, user_prompt: str, system_prompt: str):
        """Intelligent model selection based on request characteristics"""
        
        # Estimate total tokens needed
        estimated_tokens = self._estimate_tokens(system_prompt + user_prompt)
        
        # Get available models
        models = await self.model_repo.get_all_active()
        
        # Filter by context length
        suitable_models = [
            m for m in models 
            if m.context_length >= estimated_tokens * 2  # 2x buffer for response
        ]
        
        if not suitable_models:
            suitable_models = models  # Fallback to all models
        
        # Simple scoring system
        def score_model(model):
            score = 0
            
            # Prefer recommended models
            if model.is_recommended:
                score += 10
            
            # Prefer models with good performance scores
            if hasattr(model, 'performance_score') and model.performance_score:
                score += model.performance_score
            
            # Consider cost (lower is better, but not the only factor)
            cost_penalty = model.cost_per_1k_input_tokens * 2  # Adjust weight
            score -= cost_penalty
            
            # Prefer models with larger context windows for complex tasks
            if estimated_tokens > 4000:  # Complex task
                if model.context_length >= 32000:
                    score += 5
            
            return score
        
        # Select model with highest score
        suitable_models.sort(key=score_model, reverse=True)
        return suitable_models[0] if suitable_models else None
    
    async def _get_provider(self, provider_key: str):
        """Get provider with caching"""
        if provider_key not in self._provider_cache:
            provider = await self.provider_repo.get_by_provider_key(provider_key)
            self._provider_cache[provider_key] = provider
        return self._provider_cache[provider_key]
    
    async def _create_llm_service(self, model, provider):
        """Create LLM service instance for the selected model"""
        
        # Get API key from provider configuration or fallback to settings
        api_key = None
        if provider.configuration:
            api_key = provider.configuration.get('api_key')
        
        if not api_key:
            # Fallback to settings based on provider
            if provider.provider_key == 'openai':
                api_key = settings.OPENAI_API_KEY
            elif provider.provider_key == 'anthropic':
                api_key = settings.ANTHROPIC_API_KEY
            else:
                api_key = settings.LLM_API_KEY
        
        if not api_key:
            raise WorkflowProcessingException(f"No API key found for provider {provider.provider_key}")
        
        # Create LLM service
        return LLMService(api_key=api_key, model=model.model_key)
    
    def _estimate_tokens(self, text: str) -> int:
        """Simple token estimation (can be improved with tiktoken)"""
        # Rough estimation: 1 token ≈ 4 characters for English
        return max(1, len(text) // 4)
    
    def _calculate_actual_cost(self, model, input_tokens: int, output_tokens: int) -> float:
        """Calculate actual cost based on token usage"""
        input_cost = (input_tokens / 1000) * model.cost_per_1k_input_tokens
        output_cost = (output_tokens / 1000) * model.cost_per_1k_output_tokens
        return input_cost + output_cost
    
    async def _log_usage(
        self,
        user_id: int,
        model,
        provider,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        duration_ms: int,
        success: bool,
        error_message: Optional[str] = None
    ):
        """Log usage for analytics"""
        try:
            usage_dto = LLMUsageInputDTO(
                user_id=user_id,
                provider_id=provider.id,
                model_id=model.id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_cost=cost,
                response_time_ms=duration_ms,
                success=success,
                error_message=error_message,
                timestamp=datetime.utcnow()
            )
            
            await self.usage_repo.log_usage(usage_dto)
            
        except Exception as e:
            # Don't fail the main request if logging fails
            self.logger.error(f"Failed to log usage: {e}", exc_info=True)


# Factory function for dependency injection
async def get_intelligent_llm_service(
    model_repo: LLMModelRepository,
    provider_repo: LLMProviderRepository,
    usage_repo: LLMUsageRepository
) -> IntelligentLLMService:
    """Factory function to create IntelligentLLMService"""
    return IntelligentLLMService(model_repo, provider_repo, usage_repo)