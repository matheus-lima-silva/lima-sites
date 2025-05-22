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
from .scheduler import iniciar_tarefas_agendadas, parar_tarefas_agendadas
from .bot.main import (
    iniciar_bot as inicializar_handlers_telegram,
    obter_aplicacao,  # Importar obter_aplicacao
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação"""
    # Startup: validar a conexão com o banco de dados
    try:
        # Criar uma conexão de teste ao iniciar
        async with engine.begin() as conn:
            await conn.execute(text('SELECT 1'))
        print('✅ Conexão com PostgreSQL estabelecida com sucesso!')

        # Iniciar o scheduler de tarefas agendadas
        iniciar_tarefas_agendadas()
        print('✅ Scheduler de tarefas agendadas iniciado com sucesso!')

        # Inicializar handlers do Telegram
        await inicializar_handlers_telegram()  # Adicionar await
        print('✅ Handlers do Telegram inicializados com sucesso!')
    except Exception as e:
        print(f'❌ Erro ao inicializar a aplicação: {e}')
        # Em produção, seria melhor repassar este erro para um sistema de log
        raise

    yield  # A aplicação executa aqui

    # Shutdown: desligar componentes
    # Parar o bot do Telegram
    telegram_app = obter_aplicacao()
    if telegram_app:
        if telegram_app.updater and telegram_app.updater.running:
            await telegram_app.updater.stop()  # Parar o updater se estiver rodando (para polling)
        await telegram_app.stop()
        await telegram_app.shutdown()
        print('✅ Bot do Telegram parado com sucesso!')
    else:
        print('⚠️ Aplicação do Telegram não encontrada para parar.')

    # Parar o scheduler de tarefas agendadas
    parar_tarefas_agendadas()
    print('✅ Scheduler de tarefas agendadas parado com sucesso!')

    # Fechar o pool de conexões
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
