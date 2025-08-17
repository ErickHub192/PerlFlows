import logging

from fastapi import HTTPException

from app.core.config import settings
from app.dtos.ai_agent_deploy_request_dto import AIAgentDeployRequestDTO
from app.db.models import AIAgent
from app.repositories.telegram_credential_repository import TelegramCredentialRepository

logger = logging.getLogger(__name__)


async def deploy_localhost(agent: AIAgent, _: TelegramCredentialRepository, __: AIAgentDeployRequestDTO) -> dict:
    """Return chat page URL for the agent."""
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    chat_url = f"{base}/embed/{agent.agent_id}"
    return {"url": chat_url}


async def deploy_telegram(agent: AIAgent, repo: TelegramCredentialRepository, req: AIAgentDeployRequestDTO) -> dict:
    """Configure Telegram webhook and return its URL."""
    bot_token = req.bot_token
    if not bot_token:
        raise HTTPException(status_code=400, detail="bot_token requerido para Telegram")

    await repo.upsert(agent.agent_id, bot_token)
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    webhook_url = f"{base}/api/ai_agents/tg/{agent.agent_id}/{agent.webhook_secret}"
    return {"url": webhook_url}


CHANNEL_DEPLOYERS = {
    "web": deploy_localhost,
    "telegram": deploy_telegram,
}
