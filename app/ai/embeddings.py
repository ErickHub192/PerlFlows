# app/ai/embeddings.py
"""
Embedding service for agent memory system
Provides unified interface for text embeddings with multiple provider support
"""
import asyncio
import logging
from typing import List, Optional, Dict, Any
from enum import Enum
import hashlib
import json

from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingProvider(Enum):
    """Supported embedding providers"""
    OPENAI = "openai"
    # Future: ANTHROPIC = "anthropic", HUGGINGFACE = "huggingface"

class EmbeddingCache:
    """Simple in-memory cache for embeddings"""
    
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, List[float]] = {}
        self.max_size = max_size
    
    def _get_key(self, text: str, model: str) -> str:
        """Generate cache key from text and model"""
        content = f"{model}:{text}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, text: str, model: str) -> Optional[List[float]]:
        """Get embedding from cache"""
        key = self._get_key(text, model)
        return self.cache.get(key)
    
    def set(self, text: str, model: str, embedding: List[float]) -> None:
        """Store embedding in cache with size management"""
        if len(self.cache) >= self.max_size:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        key = self._get_key(text, model)
        self.cache[key] = embedding
    
    def clear(self) -> None:
        """Clear all cached embeddings"""
        self.cache.clear()
    
    def size(self) -> int:
        """Get current cache size"""
        return len(self.cache)

class EmbeddingService:
    """
    Unified embedding service for agent memory system
    """
    
    def __init__(
        self,
        provider: EmbeddingProvider = EmbeddingProvider.OPENAI,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        cache_enabled: bool = True,
        cache_size: int = 1000
    ):
        self.provider = provider
        self.cache_enabled = cache_enabled
        self.cache = EmbeddingCache(cache_size) if cache_enabled else None
        
        # Provider-specific initialization
        if provider == EmbeddingProvider.OPENAI:
            self.api_key = api_key or settings.LLM_API_KEY
            self.model = model or "text-embedding-3-small"
            self.client = AsyncOpenAI(api_key=self.api_key)
            self.dimensions = 1536  # text-embedding-3-small dimensions
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")
    
    async def get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for a single text
        Main function expected by memory system
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return [0.0] * self.dimensions
        
        # Check cache first
        if self.cache_enabled and self.cache:
            cached = self.cache.get(text, self.model)
            if cached is not None:
                logger.debug(f"Cache hit for embedding: {text[:50]}...")
                return cached
        
        try:
            embedding = await self._get_embedding_from_provider(text)
            
            # Store in cache
            if self.cache_enabled and self.cache:
                self.cache.set(text, self.model, embedding)
            
            logger.debug(f"Generated embedding for text: {text[:50]}... (dim: {len(embedding)})")
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * self.dimensions
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for multiple texts
        More efficient for batch operations
        """
        if not texts:
            return []
        
        # Check cache for all texts
        cached_results = {}
        uncached_texts = []
        
        if self.cache_enabled and self.cache:
            for i, text in enumerate(texts):
                cached = self.cache.get(text, self.model)
                if cached is not None:
                    cached_results[i] = cached
                else:
                    uncached_texts.append((i, text))
        else:
            uncached_texts = list(enumerate(texts))
        
        # Get embeddings for uncached texts
        if uncached_texts:
            try:
                batch_texts = [text for _, text in uncached_texts]
                batch_embeddings = await self._get_embeddings_from_provider(batch_texts)
                
                # Store in cache and results
                for (original_index, text), embedding in zip(uncached_texts, batch_embeddings):
                    cached_results[original_index] = embedding
                    if self.cache_enabled and self.cache:
                        self.cache.set(text, self.model, embedding)
                        
            except Exception as e:
                logger.error(f"Error generating batch embeddings: {e}")
                # Fill missing embeddings with zero vectors
                for original_index, _ in uncached_texts:
                    cached_results[original_index] = [0.0] * self.dimensions
        
        # Return results in original order
        return [cached_results[i] for i in range(len(texts))]
    
    async def _get_embedding_from_provider(self, text: str) -> List[float]:
        """Get embedding from the configured provider"""
        if self.provider == EmbeddingProvider.OPENAI:
            return await self._get_openai_embedding(text)
        else:
            raise ValueError(f"Provider {self.provider} not implemented")
    
    async def _get_embeddings_from_provider(self, texts: List[str]) -> List[List[float]]:
        """Get batch embeddings from the configured provider"""
        if self.provider == EmbeddingProvider.OPENAI:
            return await self._get_openai_embeddings(texts)
        else:
            raise ValueError(f"Provider {self.provider} not implemented")
    
    async def _get_openai_embedding(self, text: str) -> List[float]:
        """Get embedding from OpenAI"""
        response = await self.client.embeddings.create(
            model=self.model,
            input=text,
            encoding_format="float"
        )
        return response.data[0].embedding
    
    async def _get_openai_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get batch embeddings from OpenAI"""
        response = await self.client.embeddings.create(
            model=self.model,
            input=texts,
            encoding_format="float"
        )
        return [data.embedding for data in response.data]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.cache_enabled or not self.cache:
            return {"cache_enabled": False}
        
        return {
            "cache_enabled": True,
            "cache_size": self.cache.size(),
            "max_cache_size": self.cache.max_size,
            "cache_hit_ratio": "Not tracked"  # Could be enhanced
        }
    
    def clear_cache(self) -> None:
        """Clear embedding cache"""
        if self.cache:
            self.cache.clear()
            logger.info("Embedding cache cleared")

# Global embedding service instance
_embedding_service: Optional[EmbeddingService] = None

def get_embedding_service() -> EmbeddingService:
    """
    Get global embedding service instance
    Lazy initialization with configuration from settings
    """
    global _embedding_service
    
    if _embedding_service is None:
        provider = EmbeddingProvider.OPENAI  # Default to OpenAI
        cache_enabled = getattr(settings, 'EMBEDDING_CACHE_ENABLED', True)
        cache_size = getattr(settings, 'EMBEDDING_CACHE_SIZE', 1000)
        
        _embedding_service = EmbeddingService(
            provider=provider,
            cache_enabled=cache_enabled,
            cache_size=cache_size
        )
        
        logger.info(f"Initialized embedding service: {provider.value}")
    
    return _embedding_service

async def get_embedding(text: str) -> List[float]:
    """
    Convenience function for getting single embedding
    This is the main function expected by the memory system
    """
    service = get_embedding_service()
    return await service.get_embedding(text)

async def get_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Convenience function for getting batch embeddings
    """
    service = get_embedding_service()
    return await service.get_embeddings(texts)

def set_embedding_provider(
    provider: EmbeddingProvider,
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> None:
    """
    Set embedding provider configuration
    Recreates the global service instance
    """
    global _embedding_service
    
    _embedding_service = EmbeddingService(
        provider=provider,
        api_key=api_key,
        model=model
    )
    
    logger.info(f"Embedding provider set to: {provider.value}")

def clear_embedding_cache() -> None:
    """Clear the global embedding cache"""
    service = get_embedding_service()
    service.clear_cache()

def get_embedding_cache_stats() -> Dict[str, Any]:
    """Get embedding cache statistics"""
    service = get_embedding_service()
    return service.get_cache_stats()