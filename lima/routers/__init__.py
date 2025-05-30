# Este pacote conterá todos os routers da aplicação

from .alteracoes import router as alteracoes_router
from .anotacoes import router as anotacoes_router
from .auth import router as auth_router
from .bot_conversations import router as bot_conversations_router
from .buscas import router as buscas_router
from .enderecos import router as enderecos_router
from .sugestoes import router as sugestoes_router
from .usuarios import router as usuarios_router
from .usuarios_admin import router as usuarios_admin_router

__all__ = [
    'auth_router',
    'usuarios_router',
    'usuarios_admin_router',
    'enderecos_router',
    'buscas_router',
    'sugestoes_router',
    'alteracoes_router',
    'anotacoes_router',
    'bot_conversations_router',
]
