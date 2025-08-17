# app/dtos/user_dto.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# --- Entrada (registro) ---
class UserCreateDTO(BaseModel):
    username: str
    email: EmailStr
    password: str      # texto plano; luego haces hash en el service
    full_name: Optional[str]

# --- Salida / Respuesta ---
class UserDTO(BaseModel):
    id: int
    username: str
    email: EmailStr
    full_name: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
