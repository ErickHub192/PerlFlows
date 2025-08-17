# app/services/cost_calculation_service.py
"""
Unified cost calculation service to eliminate duplication across LLM services
"""
import logging
from typing import Dict, Any, Optional
from uuid import UUID

from app.repositories.llm_model_repository import LLMModelRepository
from fastapi import Depends

logger = logging.getLogger(__name__)

class CostCalculationService:
    """
    Centralized service for all LLM cost calculations and token usage extraction
    """
    
    def __init__(self, model_repo: LLMModelRepository):
        self.model_repo = model_repo
        self._model_cache: Dict[str, Dict[str, Any]] = {}
    
    async def get_model_info(self, model_key: str) -> Optional[Dict[str, Any]]:
        """
        Get model information with caching
        """
        if model_key in self._model_cache:
            return self._model_cache[model_key]
        
        try:
            model = await self.model_repo.get_by_model_key(model_key)
            if not model:
                return None
            
            model_info = {
                'model_key': model.model_key,
                'display_name': model.display_name,
                'provider_key': model.provider_key,
                'input_cost_per_1k': float(model.input_cost_per_1k or 0),
                'output_cost_per_1k': float(model.output_cost_per_1k or 0),
                'context_length': model.context_length,
                'capabilities': model.capabilities or []
            }
            
            # Cache the result
            self._model_cache[model_key] = model_info
            return model_info
            
        except Exception as e:
            logger.error(f"Error getting model info for {model_key}: {e}")
            return None
    
    async def calculate_cost(
        self, 
        model_key: str, 
        input_tokens: int, 
        output_tokens: int
    ) -> float:
        """
        Calculate cost for token usage using cached model info
        """
        model_info = await self.get_model_info(model_key)
        if not model_info:
            logger.warning(f"No model info found for {model_key}, cost will be 0")
            return 0.0
        
        input_cost = (input_tokens / 1000) * model_info['input_cost_per_1k']
        output_cost = (output_tokens / 1000) * model_info['output_cost_per_1k']
        total_cost = input_cost + output_cost
        
        logger.debug(
            f"Cost calculation for {model_key}: "
            f"input={input_tokens}*{model_info['input_cost_per_1k']}/1k={input_cost:.6f}, "
            f"output={output_tokens}*{model_info['output_cost_per_1k']}/1k={output_cost:.6f}, "
            f"total={total_cost:.6f}"
        )
        
        return total_cost
    
    def extract_token_usage(self, llm_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardized token usage extraction from various LLM response formats
        """
        usage_info = {
            'input_tokens': 0,
            'output_tokens': 0,
            'total_tokens': 0
        }
        
        try:
            # OpenAI format
            if 'usage' in llm_response:
                usage = llm_response['usage']
                usage_info.update({
                    'input_tokens': usage.get('prompt_tokens', 0),
                    'output_tokens': usage.get('completion_tokens', 0),
                    'total_tokens': usage.get('total_tokens', 0)
                })
            
            # Anthropic format
            elif 'usage' in llm_response and 'input_tokens' in llm_response['usage']:
                usage = llm_response['usage']
                usage_info.update({
                    'input_tokens': usage.get('input_tokens', 0),
                    'output_tokens': usage.get('output_tokens', 0)
                })
                usage_info['total_tokens'] = usage_info['input_tokens'] + usage_info['output_tokens']
            
            # Generic format fallback
            elif any(key in llm_response for key in ['input_tokens', 'prompt_tokens']):
                usage_info.update({
                    'input_tokens': llm_response.get('input_tokens', llm_response.get('prompt_tokens', 0)),
                    'output_tokens': llm_response.get('output_tokens', llm_response.get('completion_tokens', 0))
                })
                usage_info['total_tokens'] = usage_info['input_tokens'] + usage_info['output_tokens']
            
            # Ensure total_tokens is calculated if not provided
            if usage_info['total_tokens'] == 0 and (usage_info['input_tokens'] or usage_info['output_tokens']):
                usage_info['total_tokens'] = usage_info['input_tokens'] + usage_info['output_tokens']
                
        except Exception as e:
            logger.warning(f"Error extracting token usage: {e}")
        
        return usage_info
    
    async def calculate_usage_with_cost(
        self,
        model_key: str,
        llm_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract token usage and calculate cost in one operation
        """
        usage_info = self.extract_token_usage(llm_response)
        
        if usage_info['input_tokens'] or usage_info['output_tokens']:
            cost = await self.calculate_cost(
                model_key,
                usage_info['input_tokens'],
                usage_info['output_tokens']
            )
            usage_info['cost'] = cost
        else:
            usage_info['cost'] = 0.0
        
        return usage_info
    
    def clear_cache(self):
        """Clear model info cache"""
        self._model_cache.clear()
        logger.info("Model info cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'cached_models': len(self._model_cache),
            'model_keys': list(self._model_cache.keys())
        }


def get_cost_calculation_service(
    model_repo: LLMModelRepository = Depends()  # Necesita factory del repo
) -> CostCalculationService:
    """Dependency injection for CostCalculationService"""
    return CostCalculationService(model_repo)