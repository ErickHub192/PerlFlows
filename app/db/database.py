import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
from typing import AsyncGenerator
# Asume que settings.DATABASE_URL usa el esquema postgresql://
# Para el engine asíncrono, reemplazamos por asyncpg:
ASYNC_DATABASE_URL = (
    settings.DATABASE_URL.replace(
        "postgresql://", "postgresql+asyncpg://"
    )
)

# Crea el engine asíncrono
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    
)

# Session factory asíncrona
async_session = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Crea la sesión asíncrona con auto-commit
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()  # ✅ Auto-commit al final del request
        except Exception:
            await session.rollback()  # ✅ Rollback en caso de error
            raise

# Base para todos los modelos ORM
Base = declarative_base()
