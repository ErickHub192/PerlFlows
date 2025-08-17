"""DTOs relacionados con el despliegue de agentes."""

from typing import Optional

from pydantic import BaseModel, Field, model_validator

class AIAgentDeployRequestDTO(BaseModel):
    """Request payload for deploying an AI agent to a channel."""

    channel: str = Field(..., description="Canal de destino para el despliegue")
    bot_token: Optional[str] = Field(
        None,
        description="Token del bot para Telegram (requerido si channel es 'telegram')",
    )

    @model_validator(mode="after")
    def check_bot_token_for_telegram(self):
        """Valida que `bot_token` esté presente cuando el canal es Telegram."""
        channel = self.channel
        bot_token = self.bot_token
        if channel == "telegram" and not bot_token:
            raise ValueError(
                "bot_token es obligatorio cuando channel es 'telegram'"
            )
        return self

