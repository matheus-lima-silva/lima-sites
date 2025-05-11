from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .settings import Settings

settings = Settings()
DATABASE_URL = settings.DATABASE_URL

# Com PostgreSQL, podemos usar totalmente o modo assíncrono
engine = create_async_engine(
    DATABASE_URL,
    # Ativa logs SQL em modo DEBUG
    echo=settings.DEBUG,
    # Configuração recomendada para PostgreSQL
    pool_size=5,
    # Permite criar até 10 conexões adicionais quando o pool está cheio
    max_overflow=10,
    # Tempo máximo de espera para obter uma conexão do pool
    pool_timeout=30,
    # Recicla conexões após 30 minutos (evita conexões quebradas)
    pool_recycle=1800,
    future=True,
)

async_session = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


# Configuração para garantir que datetimes sejam sempre tratados com timezone
@event.listens_for(engine.sync_engine, 'connect')
def set_timezone(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("SET timezone='UTC'")
    cursor.close()


# Função para garantir que datetimes sejam sempre gerados com timezone
def utcnow():
    """Retorna o datetime atual sem timezone,
    para compatibilidade com PostgreSQL."""
    # Obtém o datetime com timezone UTC e depois remove o timezone
    # para compatibilidade com colunas do tipo TIMESTAMP WITHOUT TIME ZONE
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency para FastAPI: retorna uma sessão assíncrona."""
    session = async_session()
    try:
        yield session
    finally:
        await session.close()
