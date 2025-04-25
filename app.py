from http import HTTPStatus

from fastapi import FastAPI

from schemas import Message
from lima.routers import auth, usuarios, buscas, enderecos, alteracoes, sugestoes

app = FastAPI(
    title="Lima API",
    description="API para gerenciamento de dados com integração ao WhatsApp",
    version="0.1.0"
)

# Incluindo os roteadores
app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(buscas.router)
app.include_router(enderecos.router)
app.include_router(alteracoes.router)
app.include_router(sugestoes.router)


@app.get('/', status_code=HTTPStatus.OK, response_model=Message)
def read_root():
    return {'message': 'Olá Mundo!'}
