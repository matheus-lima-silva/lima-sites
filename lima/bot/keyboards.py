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
        [
            InlineKeyboardButton(
                '🏗️ Filtrar por Tipo', callback_data='filtro_tipo'
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


def criar_teclado_tipos_codigo() -> InlineKeyboardMarkup:
    """
    Cria o teclado para seleção do tipo de código.

    Returns:
        Teclado inline com tipos de código disponíveis.
    """
    keyboard = [
        [
            InlineKeyboardButton(
                '📱 Código da Operadora', callback_data='tipo_cod_operadora'
            )
        ],
        [
            InlineKeyboardButton(
                '🏢 Código da Detentora', callback_data='tipo_cod_detentora'
            )
        ],
        [
            InlineKeyboardButton(
                '🆔 ID do Sistema', callback_data='tipo_id_sistema'
            )
        ],
        [
            InlineKeyboardButton(
                '↩️ Voltar ao Menu', callback_data='voltar_menu_principal'
            )
        ],
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


def criar_teclado_selecionar_tipo_sugestao_geral() -> InlineKeyboardMarkup:
    """
    Cria teclado para selecionar o tipo de sugestão (fluxo geral).
    Usado quando o comando /sugerir é chamado.
    """
    keyboard = [
        [
            InlineKeyboardButton(
                '➕ Adicionar Novo Endereço',
                callback_data='sugest_tipo_adicao',
            )
        ],
        [
            InlineKeyboardButton(
                '✏️ Modificar Endereço Existente',
                callback_data='sugest_tipo_modificar_pedir_id',
            )
        ],
        [
            InlineKeyboardButton(
                '❌ Remover Endereço Existente',
                callback_data='sugest_tipo_remover_pedir_id',
            )
        ],
        [
            InlineKeyboardButton(
                '🚫 Cancelar Sugestão',
                callback_data='sugest_cancelar_geral',
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def criar_teclado_selecionar_tipo_sugestao_para_endereco(
    id_endereco: int,
) -> InlineKeyboardMarkup:
    """
    Cria teclado para selecionar o tipo de sugestão para um endereço
    específico. Usado quando o botão "Sugerir Melhoria" de um endereço
    é clicado. O id_endereco já foi capturado e estará no contexto.
    """
    keyboard = [
        [
            InlineKeyboardButton(
                '✏️ Modificar Este Endereço',
                callback_data='sugest_tipo_modificar_com_id_atual',
            )
        ],
        [
            InlineKeyboardButton(
                '❌ Remover Este Endereço',
                callback_data='sugest_tipo_remover_com_id_atual',
            )
        ],
        [
            InlineKeyboardButton(
                '🚫 Cancelar Sugestão',
                callback_data='sugest_cancelar_geral',
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def criar_teclado_resultados_combinado(
    pagina_atual: int,
    total_resultados: int,
    prefixo_pagina: str = 'pagina',
    mostrar_filtros_botao: bool = True,
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

    # 2. Botão de Filtros
    # Alterado para mostrar filtros apenas se houver MAIS DE UM resultado.
    if mostrar_filtros_botao and total_resultados > 1:
        botoes_acao = [
            InlineKeyboardButton(
                '🔍 Filtrar Resultados', callback_data='mostrar_filtros'
            )
        ]
        keyboard_rows.append(botoes_acao)

    # 3. Botão de Sugestões (presente se houver resultados)
    # Sugestões podem ser aplicáveis a um único resultado também.
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


def teclado_endereco_nao_encontrado_criar() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                '🔍 Tentar outro código',
                callback_data='tentar_outro_codigo_anotacao',
            )
        ],
        [
            InlineKeyboardButton(
                '❌ Cancelar', callback_data='cancelar_nova_anotacao_direto'
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def teclado_simples_cancelar_anotacao() -> InlineKeyboardMarkup:
    """Retorna um teclado inline com um único botão 'Cancelar'."""
    button = [
        InlineKeyboardButton(
            '❌ Cancelar', callback_data='cancelar_processo_anotacao'
        )
    ]
    return InlineKeyboardMarkup([button])


def criar_teclado_acoes_endereco(id_endereco: int) -> InlineKeyboardMarkup:
    """
    Cria teclado com ações para um endereço específico (anotações).

    Args:
        id_endereco: O ID do endereço.

    Returns:
        Teclado inline com ações de anotação.
    """
    keyboard = [
        [
            InlineKeyboardButton(
                '📝 Fazer Anotação',
                callback_data=f'fazer_anotacao_{id_endereco}',
            ),
            InlineKeyboardButton(
                '📖 Ler Anotações',
                callback_data=f'ler_anotacoes_{id_endereco}',
            ),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def criar_teclado_ufs_comuns() -> InlineKeyboardMarkup:
    """
    Cria teclado com as UFs mais comuns para filtro rápido.

    Returns:
        Teclado inline com UFs comuns.
    """
    keyboard = [
        [
            InlineKeyboardButton('SP', callback_data='filtro_uf_SP'),
            InlineKeyboardButton('RJ', callback_data='filtro_uf_RJ'),
            InlineKeyboardButton('MG', callback_data='filtro_uf_MG'),
        ],
        [
            InlineKeyboardButton('RS', callback_data='filtro_uf_RS'),
            InlineKeyboardButton('PR', callback_data='filtro_uf_PR'),
            InlineKeyboardButton('SC', callback_data='filtro_uf_SC'),
        ],
        [
            InlineKeyboardButton('BA', callback_data='filtro_uf_BA'),
            InlineKeyboardButton('GO', callback_data='filtro_uf_GO'),
            InlineKeyboardButton('DF', callback_data='filtro_uf_DF'),
        ],
        [
            InlineKeyboardButton(
                '✏️ Digitar outra UF', callback_data='filtro_uf_custom'
            ),
            InlineKeyboardButton('🔙 Voltar', callback_data='filtro_voltar'),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def criar_teclado_operadoras_comuns() -> InlineKeyboardMarkup:
    """
    Cria teclado com as operadoras mais comuns para filtro rápido.

    Returns:
        Teclado inline com operadoras comuns.
    """
    keyboard = [
        [
            InlineKeyboardButton('CLARO', callback_data='filtro_op_CLARO'),
            InlineKeyboardButton('VIVO', callback_data='filtro_op_VIVO'),
        ],
        [
            InlineKeyboardButton('TIM', callback_data='filtro_op_TIM'),
            InlineKeyboardButton('OI', callback_data='filtro_op_OI'),
        ],
        [
            InlineKeyboardButton('ALGAR', callback_data='filtro_op_ALGAR'),
            InlineKeyboardButton('NEXTEL', callback_data='filtro_op_NEXTEL'),
        ],
        [
            InlineKeyboardButton(
                '✏️ Digitar outra operadora',
                callback_data='filtro_operadora_custom',
            ),
            InlineKeyboardButton('🔙 Voltar', callback_data='filtro_voltar'),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def criar_botoes_acao_endereco(id_sistema: int) -> InlineKeyboardMarkup:
    """
    Cria botões de ação contextual para um endereço visualizado.

    Args:
        id_sistema: ID do sistema do endereço

    Returns:
        Teclado inline com ações contextuais.
    """
    keyboard = [
        [
            InlineKeyboardButton(
                '➕ Nova Anotação', callback_data=f'anotar_{id_sistema}'
            ),
            InlineKeyboardButton(
                '✏️ Sugerir Melhoria', callback_data=f'sugerir_{id_sistema}'
            ),
            InlineKeyboardButton(
                '🗒️ Ver todas as anotações',
                callback_data=f'ver_anotacoes_{id_sistema}',
            ),
        ],
        [
            InlineKeyboardButton(
                '🔄 Nova Busca Rápida', callback_data='nova_busca_rapida'
            ),
            InlineKeyboardButton(
                '↩️ Voltar ao Menu', callback_data='voltar_menu_principal'
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def criar_botoes_nenhum_resultado() -> InlineKeyboardMarkup:
    """
    Cria botões para quando não há resultados na busca.

    Returns:
        Teclado inline com opções para nenhum resultado.
    """
    keyboard = [
        [
            InlineKeyboardButton(
                '💡 Tentar Outro Código', callback_data='nova_busca_rapida'
            )
        ],
        [
            InlineKeyboardButton(
                '🗺️ Explorar Base', callback_data='menu_explorar_base'
            )
        ],
        [
            InlineKeyboardButton(
                '↩️ Voltar ao Menu', callback_data='voltar_menu_principal'
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
