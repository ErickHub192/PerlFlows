# app/mappers/oauth_mapper.py
from typing import Optional
from app.dtos.oauth_dto import OAuthDTO

def map_oauth_response(
    service: str,
    redirect_url: Optional[str] = None,
    error: Optional[str] = None
) -> OAuthDTO:
    # Usamos model_validate para poblar desde un dict
    return OAuthDTO.model_validate({
        "service": service,
        "redirect_url": redirect_url,
        "error": error
    })
