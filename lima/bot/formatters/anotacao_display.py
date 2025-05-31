"""
Formatadores para exibição de anotações no Telegram.

Este módulo contém funções especializadas para formatação de anotações
para exibição no Telegram, incluindo agrupamento por proprietário,
limitação de tamanho e escape de caracteres especiais.
"""

# Importa as funções implementadas do módulo anotacao
from .anotacao import (
    construir_partes_anotacoes_secao,
    filtrar_anotacoes_por_proprietario,
    formatar_anotacao,
    formatar_anotacoes_agrupadas,
)

__all__ = [
    'formatar_anotacao',
    'filtrar_anotacoes_por_proprietario',
    'formatar_anotacoes_agrupadas',
    'construir_partes_anotacoes_secao',
]
