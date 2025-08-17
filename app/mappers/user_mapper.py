# app/mappers/user_mapper.py
from app.db.models import User
from app.dtos.user_dto import UserDTO

def to_user_dto(u: User) -> UserDTO:
    return UserDTO.from_orm(u)
