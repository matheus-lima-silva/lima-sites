"""
Módulo de formatadores para o bot Telegram.

Este módulo contém todas as funções de formatação de mensagens,
incluindo escape de caracteres especiais, formatação de endereços,
anotações e outros elementos para exibição no Telegram.
"""

from .anotacao import (
    construir_partes_anotacoes_secao,
    filtrar_anotacoes_por_privilegio,
    filtrar_anotacoes_por_proprietario,
    formatar_anotacao,
    formatar_anotacoes_agrupadas,
    formatar_anotacoes_para_exibicao,
)
from .base import escape_markdown
from .endereco import (
    formatar_endereco,
    formatar_endereco_detalhado,
    formatar_lista_resultados,
)
from .sugestao import formatar_sugestao

__all__ = [
    'escape_markdown',
    'formatar_endereco',
    'formatar_endereco_detalhado',
    'formatar_lista_resultados',
    'formatar_sugestao',
    'formatar_anotacao',
    'filtrar_anotacoes_por_proprietario',
    'filtrar_anotacoes_por_privilegio',
    'formatar_anotacoes_agrupadas',
    'formatar_anotacoes_para_exibicao',
    'construir_partes_anotacoes_secao',
]
