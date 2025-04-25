from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .settings import Settings

settings = Settings()
DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False, future=True)

async_session = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency para FastAPI: retorna uma sessão assíncrona."""
    session = async_session()
    try:
        yield session
    finally:
        await session.close()
