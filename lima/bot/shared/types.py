"""
Tipos e estruturas compartilhadas para o sistema de busca por código.

Este módulo contém definições de tipos que são utilizadas em múltiplos
módulos para garantir consistência e reutilização.

IMPLEMENTADO: FASE 2 - Tipos compartilhados migrados de busca_codigo.py
"""

from dataclasses import dataclass
from typing import NamedTuple

# Estados da conversa para handlers
SELECIONANDO_TIPO_CODIGO, AGUARDANDO_CODIGO = range(2)


@dataclass
class ComandoInfo:
    """
    Estrutura para agrupar informações de um comando direto.

    Armazena metadados sobre comandos de busca por código específico,
    incluindo o nome do comando, tipo de código e nome legível do tipo.

    Attributes:
        nome_comando: Nome do comando (ex: 'operadora', 'detentora')
        tipo_codigo: Tipo técnico do código
            (ex: 'cod_operadora', 'cod_detentora')
        nome_tipo_codigo: Nome legível do tipo
            (ex: 'Código da Operadora')
    """

    nome_comando: str
    tipo_codigo: str
    nome_tipo_codigo: str


class InfoPaginacao(NamedTuple):
    """
    Informações de paginação para múltiplos resultados.

    Estrutura imutável que contém todos os dados necessários para
    implementar paginação de resultados de busca.

    Attributes:
        pagina_atual: Número da página atual (base 0)
        total_paginas: Total de páginas disponíveis
        inicio: Índice de início dos itens na página atual
        fim: Índice de fim dos itens na página atual
    """

    pagina_atual: int
    total_paginas: int
    inicio: int
    fim: int
