# app/dtos/oauth_dto.py
from pydantic import BaseModel, ConfigDict
from typing import Optional

class OAuthDTO(BaseModel):
    service: str
    redirect_url: Optional[str] = None
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
