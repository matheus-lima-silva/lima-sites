"""
Módulo de rotas para gerenciamento de endereços.
Organiza as operações em módulos menores para melhor manutenção.
"""

from fastapi import APIRouter

from .auditoria import router as auditoria_router
from .auxiliares import router as auxiliares_router
from .basic import router as basic_router
from .busca import router as busca_router
from .estatisticas import router as estatisticas_router
from .listagem import router as listagem_router

# Router principal que inclui todos os outros
router = APIRouter(prefix='/enderecos', tags=['Endereços'])

# Incluir todos os sub-routers
router.include_router(basic_router)
router.include_router(busca_router)
router.include_router(estatisticas_router)
router.include_router(auxiliares_router)
router.include_router(auditoria_router)
router.include_router(listagem_router)
