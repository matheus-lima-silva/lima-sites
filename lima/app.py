from http import HTTPStatus

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import (
    alteracoes,
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


@app.get('/', status_code=HTTPStatus.OK)
def read_root():
    return {'message': 'API Lima rodando!'}
