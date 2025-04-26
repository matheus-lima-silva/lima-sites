from http import HTTPStatus

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .database import engine
from .routers import (
    alteracoes,
    anotacoes,
    auth,
    buscas,
    enderecos,
    sugestoes,
    usuarios,
)

# Imports relativos dentro do pacote lima

app = FastAPI(title="Lima - API de Endereços via WhatsApp")

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro dos routers
app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(enderecos.router)
app.include_router(buscas.router)
app.include_router(sugestoes.router)
app.include_router(alteracoes.router)
app.include_router(anotacoes.router)


@app.get('/', status_code=HTTPStatus.OK)
def read_root():
    return {'message': 'API Lima rodando!'}


# Eventos de gerenciamento de ciclo de vida da aplicação
@app.on_event("startup")
async def startup():
    """Executa operações na inicialização do aplicativo"""
    # Validar a conexão com o banco de dados na inicialização
    # Isso garante que a aplicação só inicia se a conexão com o PostgreSQL estiver funcional
    try:
        # Criar uma conexão de teste ao iniciar
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ Conexão com PostgreSQL estabelecida com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao conectar ao PostgreSQL: {e}")
        # Em produção, seria melhor repassar este erro para um sistema de log
        raise


@app.on_event("shutdown")
async def shutdown():
    """Executa operações ao desligar o aplicativo"""
    # Fecha o pool de conexões ao encerrar a aplicação
    await engine.dispose()
    print("✅ Pool de conexões PostgreSQL fechado com sucesso!")
