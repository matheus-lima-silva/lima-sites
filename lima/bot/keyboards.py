"""
Teclados interativos para o Telegram.
Este módulo contém funções para criar teclados inline e de resposta.
"""

from typing import List, Optional

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)

from .config import ITENS_POR_PAGINA


def criar_teclado_filtros() -> InlineKeyboardMarkup:
    """
    Cria teclado com botões de filtro para buscas.

    Returns:
        Teclado inline com botões de filtro.
    """
    keyboard = [
        [
            InlineKeyboardButton(
                '🏙️ Filtrar por Cidade', callback_data='filtro_cidade'
            ),
            InlineKeyboardButton(
                '📮 Filtrar por CEP', callback_data='filtro_cep'
            ),
        ],
        [
            InlineKeyboardButton(
                '🏢 Filtrar por UF', callback_data='filtro_uf'
            ),
            InlineKeyboardButton(
                '📱 Filtrar por Operadora', callback_data='filtro_operadora'
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def criar_teclado_tipos_endereco() -> InlineKeyboardMarkup:
    """
    Cria teclado com os tipos de endereço para filtro.

    Returns:
        Teclado inline com tipos de endereço.
    """
    keyboard = [
        [
            InlineKeyboardButton(
                'Greenfield', callback_data='tipo_greenfield'
            ),
            InlineKeyboardButton('Rooftop', callback_data='tipo_rooftop'),
        ],
        [
            InlineKeyboardButton('Shopping', callback_data='tipo_shopping'),
            InlineKeyboardButton('Indoor', callback_data='tipo_indoor'),
        ],
        [
            InlineKeyboardButton('COW', callback_data='tipo_cow'),
            InlineKeyboardButton('Fastsite', callback_data='tipo_fastsite'),
        ],
        [
            InlineKeyboardButton('Outdoor', callback_data='tipo_outdoor'),
            InlineKeyboardButton(
                'Small Cell', callback_data='tipo_small_cell'
            ),
        ],
        [InlineKeyboardButton('Voltar', callback_data='filtro_voltar')],
    ]
    return InlineKeyboardMarkup(keyboard)


def criar_teclado_paginacao(
    pagina_atual: int,
    total_resultados: int,
    prefixo: str = 'pagina',
    itens_por_pagina: Optional[int] = None,
) -> InlineKeyboardMarkup:
    """
    Cria teclado para paginação de resultados.

    Args:
        pagina_atual: Número da página atual (começando em 0).
        total_resultados: Total de itens.
        prefixo: Prefixo para o callback_data dos botões.
        itens_por_pagina: Número de itens por página.

    Returns:
        Teclado inline com botões de paginação.
    """
    if itens_por_pagina is None:
        itens_por_pagina = ITENS_POR_PAGINA

    total_paginas = (
        total_resultados + itens_por_pagina - 1
    ) // itens_por_pagina

    # Se só tem uma página, não precisa de paginação
    if total_paginas <= 1:
        return None

    botoes = []

    # Anterior
    if pagina_atual > 0:
        botoes.append(
            InlineKeyboardButton(
                '◀️ Anterior', callback_data=f'{prefixo}_{pagina_atual - 1}'
            )
        )

    # Indicador de página
    botoes.append(
        InlineKeyboardButton(
            f'{pagina_atual + 1}/{total_paginas}',
            callback_data=f'{prefixo}_info',
        )
    )

    # Próximo
    if pagina_atual < total_paginas - 1:
        botoes.append(
            InlineKeyboardButton(
                'Próximo ▶️', callback_data=f'{prefixo}_{pagina_atual + 1}'
            )
        )

    return InlineKeyboardMarkup([botoes])


def criar_teclado_confirma_cancelar(
    prefixo: str = 'confirma',
) -> InlineKeyboardMarkup:
    """
    Cria teclado com botões para confirmar ou cancelar uma ação.

    Args:
        prefixo: Prefixo para o callback_data dos botões.

    Returns:
        Teclado inline com botões de confirmação e cancelamento.
    """
    keyboard = [
        [
            InlineKeyboardButton(
                '✅ Confirmar', callback_data=f'{prefixo}_sim'
            ),
            InlineKeyboardButton(
                '❌ Cancelar', callback_data=f'{prefixo}_nao'
            ),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def criar_teclado_sugestoes() -> InlineKeyboardMarkup:
    """
    Cria teclado com os tipos de sugestão.

    Returns:
        Teclado inline com tipos de sugestão.
    """
    keyboard = [
        [
            InlineKeyboardButton(
                '➕ Adicionar', callback_data='sugestao_adicao'
            )
        ],
        [
            InlineKeyboardButton(
                '✏️ Modificar', callback_data='sugestao_modificacao'
            )
        ],
        [InlineKeyboardButton('❌ Remover', callback_data='sugestao_remocao')],
        [InlineKeyboardButton('🔙 Voltar', callback_data='sugestao_voltar')],
    ]
    return InlineKeyboardMarkup(keyboard)


def criar_teclado_compartilhar_localizacao() -> ReplyKeyboardMarkup:
    """
    Cria teclado de resposta para compartilhar a localização.

    Returns:
        Teclado de resposta com botão para compartilhar localização.
    """
    keyboard = [
        [{'text': '📍 Compartilhar Localização', 'request_location': True}]
    ]
    return ReplyKeyboardMarkup(
        keyboard, one_time_keyboard=True, resize_keyboard=True
    )


def criar_teclado_resultados_combinado(
    pagina_atual: int,
    total_resultados: int,
    prefixo_pagina: str = 'pagina',
    mostrar_filtros_botao: bool = True,  # Novo parâmetro
) -> InlineKeyboardMarkup:
    """
    Cria um teclado combinado com paginação e outros botões (ex: filtros).

    Args:
        pagina_atual: Número da página atual (começando em 0).
        total_resultados: Total de itens.
        prefixo_pagina: Prefixo para o callback_data dos botões de paginação.
        mostrar_filtros_botao: Se True, mostra o botão de filtros.

    Returns:
        Teclado inline combinado.
    """
    keyboard_rows: List[List[InlineKeyboardButton]] = []

    # 1. Botões de Paginação (se houver mais de uma página)
    teclado_paginacao = criar_teclado_paginacao(
        pagina_atual, total_resultados, prefixo_pagina
    )
    if teclado_paginacao:
        keyboard_rows.extend(teclado_paginacao.inline_keyboard)

    # 2. Botão de Filtros (agora condicional)
    if mostrar_filtros_botao and total_resultados > 1:  # Condição adicionada
        botoes_acao = [
            InlineKeyboardButton(
                '🔍 Filtrar Resultados', callback_data='mostrar_filtros'
            )
        ]
        keyboard_rows.append(botoes_acao)

    # 3. Botão de Sugestões (sempre presente, se houver resultados)
    if total_resultados > 0:
        botoes_sugestao = [
            InlineKeyboardButton(
                '💡 Sugerir Alteração', callback_data='mostrar_sugestoes'
            )
        ]
        keyboard_rows.append(botoes_sugestao)

    if not keyboard_rows:  # Se nenhuma linha foi adicionada
        return None

    return InlineKeyboardMarkup(keyboard_rows)
