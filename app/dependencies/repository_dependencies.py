# app/dependencies/repository_dependencies.py

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.repositories.node_repository import NodeRepository
from app.repositories.action_repository import ActionRepository
from app.repositories.parameter_repository import ParameterRepository
from app.repositories.chat_session_repository import ChatSessionRepository
from app.repositories.credential_repository import CredentialRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.login_repository import LoginRepository

def get_node_repository(db: AsyncSession = Depends(get_db)) -> NodeRepository:
    """Factory for NodeRepository with FastAPI DI"""
    return NodeRepository(db)

def get_action_repository(db: AsyncSession = Depends(get_db)) -> ActionRepository:
    """Factory for ActionRepository with FastAPI DI"""
    return ActionRepository(db)

def get_parameter_repository(db: AsyncSession = Depends(get_db)) -> ParameterRepository:
    """Factory for ParameterRepository with FastAPI DI"""
    return ParameterRepository(db)

def get_chat_session_repository(db: AsyncSession = Depends(get_db)) -> ChatSessionRepository:
    """Factory for ChatSessionRepository with FastAPI DI"""
    return ChatSessionRepository(db)

def get_credential_repository(db: AsyncSession = Depends(get_db)) -> CredentialRepository:
    """Factory for CredentialRepository with FastAPI DI"""
    return CredentialRepository(db)

def get_refresh_token_repository(db: AsyncSession = Depends(get_db)) -> RefreshTokenRepository:
    """Factory for RefreshTokenRepository with FastAPI DI"""
    return RefreshTokenRepository(db)

def get_login_repository(db: AsyncSession = Depends(get_db)) -> LoginRepository:
    """Factory for LoginRepository with FastAPI DI"""
    return LoginRepository(db)