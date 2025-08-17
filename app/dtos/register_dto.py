# app/dtos/register_dto.py
from pydantic import BaseModel, EmailStr
from typing import Optional

class RegisterRequestDTO(BaseModel):
    username:  str
    password:  str
    email:     EmailStr
    full_name: Optional[str] = None

class RegisterResponseDTO(BaseModel):
    access_token: str
    token_type:   str
    user_id:      str
