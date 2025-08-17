import logging
from uuid import UUID
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.repositories.telegram_credential_repository import (
    TelegramCredentialRepository,
    get_telegram_repo,
)
from app.routers.agent_router import telegram_webhook

router = APIRouter(prefix="/telegram", tags=["telegram"])
logger = logging.getLogger(__name__)


@router.post("/{agent_id}/{secret}")
async def public_telegram_webhook(
    agent_id: UUID,
    secret: str,
    update: Dict,
    repo: TelegramCredentialRepository = Depends(get_telegram_repo),
    db: AsyncSession = Depends(get_db),
):
    """Endpoint público para manejar webhooks de Telegram."""
    logger.info("Received Telegram webhook for agent %s", agent_id)
    try:
        return await telegram_webhook(agent_id, secret, update, repo, db)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error processing Telegram webhook: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to process webhook") from exc
