"""
Aplicação FastAPI para busca de endereços.
"""

from fastapi import FastAPI

from lima.routers.enderecos.busca.auxiliares import router as auxiliares_router
from lima.routers.enderecos.busca.busca import router as busca_router
from lima.routers.enderecos.busca.estatisticas import (
    router as estatisticas_router,
)
from lima.routers.enderecos.busca.listagem import router as listagem_router

# Cria a aplicação FastAPI para busca de endereços
busca_app = FastAPI(
    title='API de Busca de Endereços',
    description='API para consulta e visualização de endereços',
    docs_url='/docs',
    openapi_url='/openapi.json',
)

# Incluir os routers na aplicação de busca
busca_app.include_router(busca_router)
busca_app.include_router(listagem_router)
busca_app.include_router(estatisticas_router)
busca_app.include_router(auxiliares_router)


# Rota raiz da aplicação de busca
@busca_app.get('/', tags=['Busca'])
async def busca_root():
    """
    Rota raiz da API de busca.
    """
    return {'message': 'API de Busca de Endereços', 'status': 'operacional'}
