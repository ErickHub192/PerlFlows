# app/dtos/login_dto.py
from pydantic import BaseModel


class LoginRequestDTO(BaseModel):
    username: str
    password: str


class LoginResponseDTO(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    refresh_token: str
