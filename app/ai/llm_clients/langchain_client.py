# app/ai/llm_clients/langchain_client.py

import logging
import json
from typing import Any, Dict, List

from langchain_openai import ChatOpenAI
from langchain_community.cache import  AsyncRedisCache 
from langchain.schema import SystemMessage, AIMessage, HumanMessage

# Redis asyncio client
import redis.asyncio as redis 
from redis.asyncio import Redis
from app.core.config import settings
from app.ai.llm_clients.protocol import LLMClientProtocol
from app.ai.llm_factory import LLMClientFactory
from app.exceptions.api_exceptions import WorkflowProcessingException

# -----------------------------------------------------------------
# 1) Initialize a single global RedisCache using the async Redis client
_lc_redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    health_check_interval=30,
    decode_responses=True,
)
AsyncRedisCache(_lc_redis_client, ttl=settings.CACHE_TTL_SECONDS)
# -----------------------------------------------------------------


@LLMClientFactory.register
class LangChainClient(LLMClientProtocol):
    """
    Cliente basado en LangChain-Community + RedisCache.
    Usa ChatOpenAI con caché en Redis para chat_completion,
    y AsyncOpenAI para embeddings en embed().
    """

    @staticmethod
    def can_handle_model(model: str) -> bool:
        return model.startswith("gpt-") or model.startswith("gpt_")

    def __init__(self, api_key: str, model: str):
        self.logger = logging.getLogger(__name__)
        try:
            # ChatOpenAI from langchain_community will automatically use the RedisCache above
            self.llm = ChatOpenAI(
                model_name=model,
                temperature=0.0,
                openai_api_key=api_key,
            )
        except Exception as e:
            self.logger.error("Error creando LangChainClient: %s", e, exc_info=True)
            raise WorkflowProcessingException(f"Error inicializando LangChainClient: {e}")

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        **kwargs: Any
    ) -> Any:
        # Map OpenAI-style messages to LangChain messages
        lc_msgs: List[Any] = []
        for m in messages:
            role = m["role"]
            content = m["content"]
            if role == "system":
                lc_msgs.append(SystemMessage(content=content))
            elif role in ("user", "human"):
                lc_msgs.append(HumanMessage(content=content))
            else:
                lc_msgs.append(AIMessage(content=content))

        try:
            # Use agenerate (async) to get LLM response (cached via RedisCache)
            result = await self.llm.agenerate(messages=[lc_msgs], temperature=temperature, **kwargs)
            # agenerate returns .generations: List[List[Generation]]
            result_text = result.generations[0][0].text
        except Exception as e:
            self.logger.error("LangChainClient chat_completion error: %s", e, exc_info=True)
            raise WorkflowProcessingException(f"Error en LangChainClient: {e}")

        # Wrap in OpenAI-style .choices[0].message.content
        class _Choice:
            pass

        choice = _Choice()
        choice.message = type("M", (), {"content": result_text})
        return type("R", (), {"choices": [choice]})

    async def embed(self, texts: List[str], model: str) -> List[List[float]]:
        """
        Generate embeddings using OpenAI Async API.
        """
        from openai import AsyncOpenAI

        try:
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            resp = await client.embeddings.create(model=model, input=texts)
            return [item.embedding for item in resp.data]
        except Exception as e:
            self.logger.error("Error generando embeddings: %s", e, exc_info=True)
            raise WorkflowProcessingException(f"Error generando embeddings: {e}")
