import asyncio
from datetime import datetime, timedelta

import httpx
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from freezegun import freeze_time
from httpx import AsyncClient
from sqlalchemy import StaticPool, create_engine, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from lima.app import app as fastapi_app
from lima.database import get_async_session
from lima.models import NivelAcesso, Usuario, table_registry
from lima.security import create_whatsapp_token

# Configuração do banco de dados de testes
TEST_DATABASE_URL = 'sqlite+aiosqlite:///:memory:'
TEST_DATABASE_SYNC_URL = 'sqlite:///:memory:'


@pytest.fixture(scope='session')
def event_loop():
    """Cria um event loop para os testes assíncronos"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def async_engine():
    """Cria um engine assíncrono para o banco de dados de teste"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(table_registry.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(table_registry.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def async_session_factory(async_engine):
    """Cria uma fábrica de sessão assíncrona para o banco de dados de teste"""
    AsyncSessionLocal = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return AsyncSessionLocal


@pytest_asyncio.fixture
async def async_session(async_session_factory):
    """Cria uma sessão assíncrona para o banco de dados de teste"""
    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def sync_engine():
    """Cria um engine síncrono para o banco de dados de teste"""
    engine = create_engine(
        TEST_DATABASE_SYNC_URL,
        echo=False,
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )

    table_registry.metadata.create_all(engine)

    yield engine

    table_registry.metadata.drop_all(engine)


@pytest.fixture
def sync_session(sync_engine):
    """Cria uma sessão síncrona para o banco de dados de teste"""
    Session = sessionmaker(bind=sync_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest_asyncio.fixture
async def app(async_session):
    """Cria uma instância do aplicativo FastAPI para testes"""
    # Salva a instância original do app
    app_original = fastapi_app

    # Define o override de dependência para usar a mesma sessão de teste
    original_overrides = app_original.dependency_overrides.copy()
    app_original.dependency_overrides[get_async_session] = (
        lambda: async_session
    )

    yield app_original

    # Restaura as dependências originais ao finalizar
    app_original.dependency_overrides = original_overrides


@pytest.fixture
def client(app):
    """Cria um cliente de teste para o aplicativo FastAPI"""
    with TestClient(app) as client:
        yield client


@pytest_asyncio.fixture
async def async_client(app):
    """Cria um cliente assíncrono para o aplicativo FastAPI"""
    async with AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url='http://test'
    ) as client:
        yield client


@pytest.fixture
def frozen_datetime():
    """Fixture para retornar um datetime fixo"""
    return datetime(2025, 4, 28, 12, 0)


@pytest.fixture
def frozen_time():
    """Fixture para congelar o tempo em um momento específico"""
    with freeze_time('2025-04-28 12:00:00') as frozen:
        yield frozen


@pytest.fixture
def time_travel():
    """Fixture para viajar no tempo durante os testes"""
    dt = datetime(2025, 4, 28, 12, 0)

    def travel(delta_seconds=0, delta_minutes=0, delta_hours=0, delta_days=0):
        nonlocal dt
        dt += timedelta(
            seconds=delta_seconds,
            minutes=delta_minutes,
            hours=delta_hours,
            days=delta_days,
        )
        return dt

    return travel


@pytest_asyncio.fixture
async def usuario_basico(async_session):
    """Fixture para criar um usuário com nível básico."""
    usuario = Usuario(
        telefone='+5521900000001',
        nome='Usuário Básico',
        nivel_acesso=NivelAcesso.basico,
    )
    async_session.add(usuario)
    await async_session.commit()
    return usuario


@pytest_asyncio.fixture
async def usuario_intermediario(async_session):
    """Fixture para criar um usuário com nível intermediário."""
    usuario = Usuario(
        telefone='+5521900000002',
        nome='Usuário Intermediário',
        nivel_acesso=NivelAcesso.intermediario,
    )
    async_session.add(usuario)
    await async_session.commit()
    return usuario


@pytest_asyncio.fixture
async def usuario_super(async_session):
    """Fixture para criar um super usuário."""
    usuario = Usuario(
        telefone='+5521900000003',
        nome='Super Usuário',
        nivel_acesso=NivelAcesso.super_usuario,
    )
    async_session.add(usuario)
    await async_session.commit()
    return usuario


@pytest_asyncio.fixture
async def token_basico(usuario_basico):
    """Fixture para gerar um token para usuário com nível básico."""
    usuario = await usuario_basico
    return create_whatsapp_token(usuario.telefone)


@pytest_asyncio.fixture
async def token_intermediario(usuario_intermediario):
    """Fixture para gerar um token para usuário com nível intermediário."""
    usuario = await usuario_intermediario
    return create_whatsapp_token(usuario.telefone)


@pytest_asyncio.fixture
async def token_super(usuario_super):
    """Fixture para gerar um token para super usuário."""
    usuario = await usuario_super
    return create_whatsapp_token(usuario.telefone)


@pytest_asyncio.fixture
async def auth_header_basico(token_basico):
    """Fixture para gerar cabeçalho de autenticação para usuário básico."""
    return {'Authorization': f'Bearer {token_basico}'}


@pytest_asyncio.fixture
async def auth_header_intermediario(token_intermediario):
    """Fixture para gerar cabeçalho de autenticação para usuário
      intermediário."""
    return {'Authorization': f'Bearer {token_intermediario}'}


@pytest_asyncio.fixture
async def auth_header_super(token_super):
    """Fixture para gerar cabeçalho de autenticação para super usuário."""
    return {'Authorization': f'Bearer {token_super}'}


@pytest_asyncio.fixture
async def usuarios_exemplo(async_session):
    """Fixture para criar um conjunto de usuários de exemplo para testes."""
    usuarios = [
        Usuario(
            telefone='+5521800000001',
            nome='Usuário Teste 1',
            nivel_acesso=NivelAcesso.basico,
        ),
        Usuario(
            telefone='+5521800000002',
            nome='Usuário Teste 2',
            nivel_acesso=NivelAcesso.intermediario,
        ),
        Usuario(
            telefone='+5521800000003',
            nome='Usuário Teste 3',
            nivel_acesso=NivelAcesso.super_usuario,
        ),
    ]

    for usuario in usuarios:
        async_session.add(usuario)

    await async_session.commit()

    return usuarios


@pytest_asyncio.fixture
async def criar_usuario_com_token(async_session):
    """Fixture para criar um usuário e seu token de autenticação."""

    async def _criar_usuario_com_token(
        telefone='+5521999000000',
        nome='Usuário Teste',
        nivel=NivelAcesso.basico,
    ):
        usuario = Usuario(telefone=telefone, nome=nome, nivel_acesso=nivel)
        async_session.add(usuario)
        await async_session.commit()

        # Verificar se o usuário foi criado
        query = select(Usuario).where(Usuario.telefone == telefone)
        result = await async_session.execute(query)
        usuario_db = result.scalar_one_or_none()

        token = create_whatsapp_token(telefone)
        headers = {'Authorization': f'Bearer {token}'}

        return usuario_db, token, headers

    return _criar_usuario_com_token
