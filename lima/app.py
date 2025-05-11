from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .database import engine
from .routers import (
    alteracoes_router,
    anotacoes_router,
    auth_router,
    buscas_router,
    sugestoes_router,
    usuarios_admin_router,
    usuarios_router,
)
from .routers.enderecos import enderecos_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação"""
    # Startup: validar a conexão com o banco de dados
    try:
        # Criar uma conexão de teste ao iniciar
        async with engine.begin() as conn:
            await conn.execute(text('SELECT 1'))
        print('✅ Conexão com PostgreSQL estabelecida com sucesso!')
    except Exception as e:
        print(f'❌ Erro ao conectar ao PostgreSQL: {e}')
        # Em produção, seria melhor repassar este erro para um sistema de log
        raise

    yield  # A aplicação executa aqui

    # Shutdown: fecha o pool de conexões
    await engine.dispose()
    print('✅ Pool de conexões PostgreSQL fechado com sucesso!')


app = FastAPI(title='Lima - API de Endereços via WhatsApp', lifespan=lifespan)

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
)

# Incluir os routers regulares
app.include_router(auth_router)
app.include_router(usuarios_router)
app.include_router(usuarios_admin_router)
app.include_router(buscas_router)
app.include_router(sugestoes_router)
app.include_router(alteracoes_router)
app.include_router(anotacoes_router)

# Montar a sub-aplicação de endereços
app.mount('/enderecos', enderecos_app)


# Rota raiz
@app.get('/')
async def root():
    return {'message': 'Bem-vindo à API de Endereços Lima via WhatsApp'}
