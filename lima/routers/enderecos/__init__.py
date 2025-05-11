"""
Módulo de rotas para gerenciamento de endereços.
Implementa a estratégia de sub-aplicações (mounts) do FastAPI
para separar as funcionalidades de busca e administração.
"""

from fastapi import FastAPI

from .admin import admin_app
from .busca import busca_app

# Criamos um router FastAPI vazio para montar as sub-aplicações
enderecos_app = FastAPI(
    title='API de Endereços',
    description='API para gerenciamento de endereços',
)

# Montamos as sub-aplicações em caminhos específicos
enderecos_app.mount('/admin', admin_app)
enderecos_app.mount('/busca', busca_app)


# Rota raiz para a aplicação principal de endereços
@enderecos_app.get('/', tags=['Endereços'])
async def enderecos_root():
    """Rota raiz da API de endereços."""
    return {
        'message': 'API de Endereços',
        'sub_apis': [
            {'nome': 'Administração', 'url': '/admin'},
            {'nome': 'Busca', 'url': '/busca'},
        ],
    }


# Exportar enderecos_app como
#  router para compatibilidade com o import no routers/__init__.py
router = enderecos_app
