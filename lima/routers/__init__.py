# Este pacote conterá todos os routers da aplicação

from .alteracoes import router as alteracoes_router
from .auth import router as auth_router
from .buscas import router as buscas_router
from .enderecos import router as enderecos_router
from .sugestoes import router as sugestoes_router
from .usuarios import router as usuarios_router

__all__ = [
    "auth_router",
    "usuarios_router",
    "enderecos_router",
    "buscas_router",
    "sugestoes_router",
    "alteracoes_router",
]
