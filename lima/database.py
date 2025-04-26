from typing import AsyncGenerator
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import event

from .settings import Settings

settings = Settings()
DATABASE_URL = settings.DATABASE_URL

# Com PostgreSQL, podemos usar totalmente o modo assíncrono
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,  # Ativa logs SQL em modo DEBUG
    pool_size=5,          # Configuração recomendada para PostgreSQL
    max_overflow=10,      # Permite criar até 10 conexões adicionais quando o pool está cheio
    pool_timeout=30,      # Timeout para obter uma conexão do pool (em segundos)
    pool_recycle=1800,    # Recicla conexões após 30 minutos (evita conexões quebradas)
    future=True,
)

async_session = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


# Configuração para garantir que datetimes sejam sempre tratados com timezone
@event.listens_for(engine.sync_engine, "connect")
def set_timezone(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("SET timezone='UTC'")
    cursor.close()


# Função para garantir que datetimes sejam sempre gerados com timezone
def utcnow():
    """Retorna o datetime atual com timezone UTC."""
    return datetime.now(timezone.utc)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency para FastAPI: retorna uma sessão assíncrona."""
    session = async_session()
    try:
        yield session
    finally:
        await session.close()
