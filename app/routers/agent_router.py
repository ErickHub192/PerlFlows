from datetime import datetime, timedelta, timezone
from uuid import UUID
import logging

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.config import settings
from app.db.models import AIAgent
from app.repositories.telegram_credential_repository import (
    TelegramCredentialRepository,
    get_telegram_repo,
)
from app.db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/agents", tags=["agents"])
logger = logging.getLogger(__name__)


def generate_embed_token(agent_id: UUID) -> str:
    payload = {
        "agent_id": str(agent_id),
        "scope": "chat_embed",
        "service_url": settings.PUBLIC_BASE_URL,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


@router.post("/{agent_id}/embed_token")
async def embed_token(agent_id: UUID) -> dict:
    token = generate_embed_token(agent_id)
    return {"token": token}


class DeployRequest(Request):
    channel: str
    bot_token: str | None


@router.post("/{agent_id}/deploy")
async def deploy_agent(
    agent_id: UUID,
    req: dict,
    repo: TelegramCredentialRepository = Depends(get_telegram_repo),
) -> dict:
    if req.get("channel") != "telegram" or "bot_token" not in req:
        raise HTTPException(status_code=400, detail="Unsupported channel")

    bot_token = req["bot_token"]
    async with httpx.AsyncClient() as client:
        r = await client.get(f"https://api.telegram.org/bot{bot_token}/getMe")
    if r.status_code != 200 or not r.json().get("ok"):
        raise HTTPException(status_code=400, detail="Invalid bot token")

    await repo.upsert(agent_id, bot_token)
    if settings.PUBLIC_BASE_URL.startswith("http://localhost"):
        logger.warning(
            "Telegram requires a public HTTPS URL for webhooks. PUBLIC_BASE_URL=%s",
            settings.PUBLIC_BASE_URL,
        )
    return {"status": "telegram_ok"}


@router.post("/tg/{agent_id}/{secret}")
async def telegram_webhook(
    agent_id: UUID,
    secret: str,
    update: dict,
    repo: TelegramCredentialRepository = Depends(get_telegram_repo),
    db: AsyncSession = Depends(get_db),
):
    agent = await db.get(AIAgent, agent_id)
    if not agent or agent.webhook_secret != secret:
        raise HTTPException(status_code=403, detail="invalid secret")

    cred = await repo.get(agent_id)
    if not cred:
        raise HTTPException(status_code=404, detail="bot not deployed")

    message = update.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text")
    if not chat_id or not text:
        return {"ok": True}

    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{cred.bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
        )
    return {"ok": True}
