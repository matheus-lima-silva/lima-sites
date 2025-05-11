"""
Aplicação FastAPI para administração de endereços.
"""

from fastapi import FastAPI

from .auditoria import router as auditoria_router
from .basic import router as basic_router

# Cria a aplicação FastAPI para administração de endereços
admin_app = FastAPI(
    title='API de Administração de Endereços',
    description='API para criação, atualização e exclusão de endereços',
    docs_url='/docs',
    openapi_url='/openapi.json',
)

# Incluir os routers na aplicação admin
admin_app.include_router(basic_router)
admin_app.include_router(auditoria_router)


# Rota raiz da aplicação admin
@admin_app.get('/', tags=['Administração'])
async def admin_root():
    """
    Rota raiz da API de administração.
    Requer nível de acesso intermediário ou superior.
    """
    return {
        'message': 'API de Administração de Endereços',
        'status': 'operacional',
    }
