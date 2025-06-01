"""
Handler para Exploração da Base de Endereços (V2).
Este módulo implementa o sistema de filtros e
 navegação paginada da base de endereços.
"""

import logging
from typing import Any, Dict, List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from ..formatters.base import escape_markdown
from ..formatters.endereco import (
    formatar_endereco_detalhado,
    formatar_lista_resultados,
)
from ..services.anotacao import listar_anotacoes_por_endereco
from ..services.endereco import FiltrosEndereco, buscar_endereco

# Import para integração com sistema de anotação
try:
    from .anotacao import iniciar_anotacao_por_callback
except ImportError:
    iniciar_anotacao_por_callback = None

logger = logging.getLogger(__name__)

# Estados da conversa
AGUARDANDO_FILTRO_UF = 1
AGUARDANDO_FILTRO_CIDADE = 2
AGUARDANDO_FILTRO_BAIRRO = 3
AGUARDANDO_FILTRO_OPERADORA = 4
AGUARDANDO_FILTRO_TIPO = 5
AGUARDANDO_FILTRO_STATUS = 6

# Constantes para exibição de anotações
MAX_TEXTO_ANOTACAO_LEN = 100
MAX_ANOTACOES_EXIBIDAS = 3


def criar_teclado_filtros(
    filtros_ativos: Dict[str, Any],
) -> InlineKeyboardMarkup:
    """
    Cria o teclado inline para seleção de filtros.

    Args:
        filtros_ativos: Dicionário com os filtros atualmente ativos.

    Returns:
        Teclado inline com opções de filtros.
    """
    # Indicadores de filtros ativos
    uf_icon = '✅' if filtros_ativos.get('uf') else '⚪'
    cidade_icon = '✅' if filtros_ativos.get('municipio') else '⚪'
    bairro_icon = '✅' if filtros_ativos.get('bairro') else '⚪'
    operadora_icon = '✅' if filtros_ativos.get('operadora_nome') else '⚪'
    tipo_icon = '✅' if filtros_ativos.get('tipo') else '⚪'
    status_icon = '✅' if filtros_ativos.get('status') else '⚪'

    keyboard = [
        [
            InlineKeyboardButton(
                f'{uf_icon} UF/Estado', callback_data='filtro_uf'
            ),
            InlineKeyboardButton(
                f'{cidade_icon} Cidade', callback_data='filtro_cidade'
            ),
        ],
        [
            InlineKeyboardButton(
                f'{bairro_icon} Bairro', callback_data='filtro_bairro'
            ),
            InlineKeyboardButton(
                f'{operadora_icon} Operadora', callback_data='filtro_operadora'
            ),
        ],
        [
            InlineKeyboardButton(
                f'{tipo_icon} Tipo', callback_data='filtro_tipo'
            ),
            InlineKeyboardButton(
                f'{status_icon} Status', callback_data='filtro_status'
            ),
        ],
        [
            InlineKeyboardButton(
                '🔍 Buscar com Filtros', callback_data='executar_busca'
            ),
        ],
        [
            InlineKeyboardButton(
                '🗑️ Limpar Filtros', callback_data='limpar_filtros'
            ),
            InlineKeyboardButton(
                '↩️ Voltar ao Menu', callback_data='voltar_menu_explorar'
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def criar_teclado_navegacao_resultados(
    pagina_atual: int, total_paginas: int, endereco_ids: List[str]
) -> InlineKeyboardMarkup:
    """
    Cria o teclado para navegação de resultados.

    Args:
        pagina_atual: Página atual (0-based).
        total_paginas: Total de páginas.
        endereco_ids: Lista de IDs dos endereços da página atual.

    Returns:
        Teclado inline para navegação.
    """
    keyboard = []

    # Botões de seleção de endereços (primeiros 5 da página)
    if endereco_ids:
        endereco_buttons = []
        for i, endereco_id in enumerate(
            endereco_ids[:5]
        ):  # Máximo 5 por linha
            endereco_buttons.append(
                InlineKeyboardButton(
                    f'📍 {i + 1}', callback_data=f'ver_endereco_{endereco_id}'
                )
            )
        if endereco_buttons:
            keyboard.append(endereco_buttons)

    # Navegação de páginas
    nav_buttons = []
    if pagina_atual > 0:
        nav_buttons.append(
            InlineKeyboardButton('⬅️ Anterior', callback_data='pagina_anterior')
        )

    if total_paginas > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                f'{pagina_atual + 1}/{total_paginas}',
                callback_data='info_pagina',
            )
        )

    if pagina_atual < total_paginas - 1:
        nav_buttons.append(
            InlineKeyboardButton('➡️ Próxima', callback_data='pagina_proxima')
        )

    if nav_buttons:
        keyboard.append(nav_buttons)

    # Botões de ação
    keyboard.extend([
        [
            InlineKeyboardButton(
                '🔄 Refazer Busca', callback_data='refazer_busca'
            ),
            InlineKeyboardButton('↩️ Voltar', callback_data='voltar_filtros'),
        ]
    ])

    return InlineKeyboardMarkup(keyboard)


def criar_teclado_endereco_detalhes(endereco_id: str) -> InlineKeyboardMarkup:
    """
    Cria o teclado para ações em um endereço específico.

    Args:
        endereco_id: ID do endereço.

    Returns:
        Teclado inline para ações no endereço.
    """
    keyboard = [
        [
            InlineKeyboardButton(
                '➕ Nova Anotação',
                callback_data=f'anotacao_iniciar_id_{endereco_id}'
            ),
        ],
        [
            InlineKeyboardButton(
                '↩️ Voltar aos Resultados', callback_data='voltar_resultados'
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def iniciar_exploracao(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Inicia o fluxo de exploração da base de endereços.
    """
    query = update.callback_query
    if query:
        await query.answer()

    # Inicializar filtros vazios
    context.user_data['filtros_ativos'] = {}
    context.user_data['pagina_atual'] = 0
    context.user_data['resultados_busca'] = []

    await exibir_tela_filtros(update, context)
    return ConversationHandler.END


async def exibir_tela_filtros(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Exibe a tela de seleção de filtros.
    """
    filtros_ativos = context.user_data.get('filtros_ativos', {})

    # Construir texto dos filtros ativos
    filtros_texto = []
    if filtros_ativos.get('uf'):
        filtros_texto.append(f'UF: {escape_markdown(filtros_ativos["uf"])}')
    if filtros_ativos.get('municipio'):
        filtros_texto.append(
            f'Cidade: {escape_markdown(filtros_ativos["municipio"])}'
        )
    if filtros_ativos.get('bairro'):
        filtros_texto.append(
            f'Bairro: {escape_markdown(filtros_ativos["bairro"])}'
        )
    if filtros_ativos.get('operadora_nome'):
        filtros_texto.append(
            f'Operadora: {escape_markdown(filtros_ativos["operadora_nome"])}'
        )
    if filtros_ativos.get('tipo'):
        filtros_texto.append(
            f'Tipo: {escape_markdown(filtros_ativos["tipo"])}'
        )
    if filtros_ativos.get('status'):
        filtros_texto.append(
            f'Status: {escape_markdown(filtros_ativos["status"])}'
        )

    filtros_str = (
        '\n'.join([f'• {f}' for f in filtros_texto])
        if filtros_texto
        else 'Nenhum filtro ativo'
    )

    mensagem = (
        '🗺️ *Explorar Base de Endereços*\n\n'
        '*Filtros Ativos:*\n'
        f'{filtros_str}\n\n'
        "Selecione os filtros desejados e clique em 'Buscar':"
    )

    keyboard = criar_teclado_filtros(filtros_ativos)

    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=mensagem,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=keyboard,
            )
        else:
            await update.effective_message.reply_text(
                text=mensagem,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=keyboard,
            )
    except Exception as e:
        logger.error(f'Erro ao exibir tela de filtros: {str(e)}')


async def processar_filtro_texto(
    update: Update, context: ContextTypes.DEFAULT_TYPE, filtro_nome: str
) -> int:
    """
    Processa a entrada de texto para um filtro.
    """
    texto = update.message.text.strip()

    if not texto:
        await update.message.reply_text(
            '❌ Valor vazio não é permitido. '
            'Tente novamente ou use /cancelar para voltar.'
        )
        return AGUARDANDO_FILTRO_UF  # Ou o estado correspondente

    # Salvar o filtro
    if 'filtros_ativos' not in context.user_data:
        context.user_data['filtros_ativos'] = {}

    context.user_data['filtros_ativos'][filtro_nome] = texto

    await update.message.reply_text(
        f'✅ Filtro {filtro_nome} definido como: {escape_markdown(texto)}',
        parse_mode=ParseMode.MARKDOWN_V2,
    )

    # Voltar para a tela de filtros
    await exibir_tela_filtros(update, context)
    return ConversationHandler.END


async def executar_busca_filtrada(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Executa a busca com os filtros aplicados.
    """
    query = update.callback_query
    if query:
        await query.answer()

    filtros = context.user_data.get('filtros_ativos', {})

    if not filtros:
        await query.edit_message_text(
            '⚠️ Nenhum filtro foi definido. '
            'Defina pelo menos um filtro antes de buscar.',
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        '↩️ Voltar', callback_data='voltar_filtros'
                    )
                ]
            ]),
        )
        return

    try:
        # Criar filtros usando a estrutura FiltrosEndereco
        filtros_busca = FiltrosEndereco(
            municipio=filtros.get('municipio'),
            uf=filtros.get('uf'),
            tipo=filtros.get('tipo'),
            limite=20,  # 20 resultados por página
        )

        # Adicionar outros filtros se estiverem presentes
        if filtros.get('bairro'):
            filtros_busca.query = filtros.get(
                'bairro'
            )  # Usar query para bairro

        # Executar busca
        enderecos_lista = await buscar_endereco(
            filtros=filtros_busca,
            user_id=update.effective_user.id
            if update.effective_user
            else None,
        )

        # Simular estrutura de resposta paginada
        resultados = {
            'enderecos': enderecos_lista,
            'total': len(enderecos_lista),
            'total_paginas': 1,  # Por enquanto uma página apenas
        }

        if not resultados or not resultados.get('enderecos'):
            await query.edit_message_text(
                '❌ Nenhum endereço encontrado com os filtros aplicados.\n\n'
                'Tente ajustar os filtros.',
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            '↩️ Voltar', callback_data='voltar_filtros'
                        )
                    ]
                ]),
            )
            return

        # Salvar resultados no contexto
        context.user_data['resultados_busca'] = resultados
        context.user_data['pagina_atual'] = 0

        await exibir_resultados_busca(update, context)

    except Exception as e:
        logger.error(f'Erro ao executar busca filtrada: {str(e)}')
        await query.edit_message_text(
            '❌ Erro ao executar a busca. Tente novamente.',
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        '↩️ Voltar', callback_data='voltar_filtros'
                    )
                ]
            ]),
        )


async def exibir_resultados_busca(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Exibe os resultados da busca com navegação.
    """
    resultados = context.user_data.get('resultados_busca', {})
    pagina_atual = context.user_data.get('pagina_atual', 0)

    enderecos = resultados.get('enderecos', [])
    total = resultados.get('total', 0)
    total_paginas = resultados.get('total_paginas', 1)

    if not enderecos:
        mensagem = '❌ Nenhum resultado encontrado.'
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton('↩️ Voltar', callback_data='voltar_filtros')]
        ])
    else:
        # Formatar endereços da página atual
        mensagem_resultados = formatar_lista_resultados(
            enderecos, pagina_atual, total_paginas, formatar_endereco_detalhado
        )

        mensagem = (
            f'🗺️ *Resultados da Busca*\n\n'
            f'Total encontrado: {total} endereços\n\n'
            f'{mensagem_resultados}\n\n'
            'Clique em um número para ver detalhes:'
        )

        # Extrair IDs dos endereços para navegação
        endereco_ids = [
            str(end.get('id') or end.get('id_sistema', ''))
            for end in enderecos
        ]
        keyboard = criar_teclado_navegacao_resultados(
            pagina_atual, total_paginas, endereco_ids
        )

    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=mensagem,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=keyboard,
            )
        else:
            await update.effective_message.reply_text(
                text=mensagem,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=keyboard,
            )
    except Exception as e:
        logger.error(f'Erro ao exibir resultados da busca: {str(e)}')


async def exibir_endereco_detalhado(
    update: Update, context: ContextTypes.DEFAULT_TYPE, endereco_id: str
) -> None:
    """
    Exibe os detalhes completos de um endereço específico.
    """
    query = update.callback_query
    if query:
        await query.answer()

    try:
        # Buscar endereço nos resultados salvos
        resultados = context.user_data.get('resultados_busca', {})
        enderecos = resultados.get('enderecos', [])

        endereco = None
        for end in enderecos:
            if str(end.get('id') or end.get('id_sistema', '')) == endereco_id:
                endereco = end
                break

        if not endereco:
            await query.edit_message_text(
                '❌ Endereço não encontrado.',
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            '↩️ Voltar', callback_data='voltar_resultados'
                        )
                    ]
                ]),
            )
            return

        # Salvar endereço atual no contexto
        context.user_data['endereco_atual'] = endereco

        # Formatar detalhes do endereço
        detalhes = formatar_endereco_detalhado(endereco)

        # Buscar anotações do endereço
        try:
            anotacoes = await listar_anotacoes_por_endereco(endereco_id)
            if anotacoes:
                detalhes += f'\n\n📝 *Anotações \\\\({len(anotacoes)}\\\\):*'
                for i, anotacao in enumerate(
                    anotacoes[:MAX_ANOTACOES_EXIBIDAS], 1
                ):  # Mostrar até MAX_ANOTACOES_EXIBIDAS
                    texto = escape_markdown(
                        anotacao.get('texto', '')[:MAX_TEXTO_ANOTACAO_LEN]
                    )
                    if len(anotacao.get('texto', '')) > MAX_TEXTO_ANOTACAO_LEN:
                        texto += '\\\\.\\\\.\\\\.'
                    detalhes += f'\\n{i}\\\\. {texto}'

                if len(anotacoes) > MAX_ANOTACOES_EXIBIDAS:
                    detalhes += f'\\n\\\\.\\\\.\\\\. e mais {
                        len(anotacoes) - MAX_ANOTACOES_EXIBIDAS
                    } anotações'
            else:
                detalhes += '\n\n📝 *Anotações:* Nenhuma anotação encontrada'
        except Exception as e:
            logger.warning(
                f'Erro ao buscar anotações para endereco {endereco_id}: {
                    str(e)
                }'
            )
            detalhes += '\n\n📝 *Anotações:* Erro ao carregar'

        keyboard = criar_teclado_endereco_detalhes(endereco_id)

        await query.edit_message_text(
            text=detalhes,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboard,
        )

    except Exception as e:
        logger.error(
            f'Erro ao exibir endereco detalhado {endereco_id}: {str(e)}'
        )
        await query.edit_message_text(
            '❌ Erro ao carregar detalhes do endereço.',
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        '↩️ Voltar', callback_data='voltar_resultados'
                    )
                ]
            ]),
        )


async def handle_explorar_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Handler principal para callbacks da exploração.
    """
    query = update.callback_query
    if not query:
        return ConversationHandler.END

    await query.answer()
    data = query.data

    try:
        # Handle filter selection callbacks separately
        if data in {
            'filtro_uf',
            'filtro_cidade',
            'filtro_bairro',
            'filtro_operadora',
            'filtro_tipo',
            'filtro_status',
        }:
            return await processar_selecao_filtro(update, context, data)

        # Handle other callbacks
        return await handle_action_callbacks(update, context, data)
    except Exception as e:
        logger.error(f'Erro no handle_explorar_callback: {str(e)}')
        await query.edit_message_text(
            '❌ Erro interno. Use /cancelar para recomeçar.'
        )

    return ConversationHandler.END


async def handle_action_callbacks(
    update: Update, context: ContextTypes.DEFAULT_TYPE, data: str
) -> int:
    """Handle action callbacks like navigation, search execution etc."""
    query = update.callback_query

    if data == 'explorar_filtrar':
        await iniciar_exploracao(update, context)
    elif data == 'voltar_filtros':
        await exibir_tela_filtros(update, context)
    elif data == 'voltar_resultados':
        await exibir_resultados_busca(update, context)
    elif data == 'executar_busca':
        await executar_busca_filtrada(update, context)
    elif data == 'limpar_filtros':
        context.user_data['filtros_ativos'] = {}
        await exibir_tela_filtros(update, context)
    elif data == 'refazer_busca':
        await executar_busca_filtrada(update, context)
    elif data.startswith('ver_endereco_'):
        endereco_id = data.replace('ver_endereco_', '')
        await exibir_endereco_detalhado(update, context, endereco_id)
    elif data.startswith('anotar_'):
        endereco_id = data.replace('anotar_', '')
        # Chamar diretamente a função de anotação sem modificar query.data
        if iniciar_anotacao_por_callback:
            # Passamos o endereco_id diretamente para o contexto do usuário
            context.user_data['endereco_id_para_anotacao'] = endereco_id
            return await iniciar_anotacao_por_callback(update, context)
        else:
            await query.edit_message_text(
                '❌ Sistema de anotações não disponível.',
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            '↩️ Voltar', callback_data='voltar_resultados'
                        )
                    ]
                ]),
            )
            return ConversationHandler.END

    return ConversationHandler.END


async def processar_selecao_filtro(
    update: Update, context: ContextTypes.DEFAULT_TYPE, filtro_tipo: str
) -> int:
    """
    Processa a seleção de um tipo de filtro específico.
    """
    query = update.callback_query

    filtro_maps = {
        'filtro_uf': ('UF/Estado (ex: SP, RJ)', 'uf', AGUARDANDO_FILTRO_UF),
        'filtro_cidade': (
            'nome da cidade',
            'municipio',
            AGUARDANDO_FILTRO_CIDADE,
        ),
        'filtro_bairro': (
            'nome do bairro',
            'bairro',
            AGUARDANDO_FILTRO_BAIRRO,
        ),
        'filtro_operadora': (
            'nome da operadora',
            'operadora_nome',
            AGUARDANDO_FILTRO_OPERADORA,
        ),
        'filtro_tipo': ('tipo do endereço', 'tipo', AGUARDANDO_FILTRO_TIPO),
        'filtro_status': ('status', 'status', AGUARDANDO_FILTRO_STATUS),
    }

    if filtro_tipo not in filtro_maps:
        await query.edit_message_text('❌ Tipo de filtro não reconhecido.')
        return ConversationHandler.END

    descricao, campo_nome, estado = filtro_maps[filtro_tipo]

    # Salvar qual filtro está sendo editado
    context.user_data['filtro_sendo_editado'] = campo_nome

    await query.edit_message_text(
        f'📝 Digite o {descricao}:\n\n'
        'Use /cancelar para voltar ao menu de filtros.',
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    '❌ Cancelar', callback_data='voltar_filtros'
                )
            ]
        ]),
    )

    return estado


# Handlers para estados específicos
async def handle_filtro_uf(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    return await processar_filtro_texto(update, context, 'uf')


async def handle_filtro_cidade(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    return await processar_filtro_texto(update, context, 'municipio')


async def handle_filtro_bairro(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    return await processar_filtro_texto(update, context, 'bairro')


async def handle_filtro_operadora(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    return await processar_filtro_texto(update, context, 'operadora_nome')


async def handle_filtro_tipo(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    return await processar_filtro_texto(update, context, 'tipo')


async def handle_filtro_status(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    return await processar_filtro_texto(update, context, 'status')


async def cancelar_exploracao(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Cancela o fluxo de exploração.
    """
    # Limpar dados da exploração
    context.user_data.pop('filtros_ativos', None)
    context.user_data.pop('resultados_busca', None)
    context.user_data.pop('pagina_atual', None)
    context.user_data.pop('endereco_atual', None)

    await update.effective_message.reply_text(
        '❌ Exploração cancelada. Use /listar para voltar ao menu.'
    )
    return ConversationHandler.END


# Conversation handler principal
def criar_conversation_handler_exploracao():
    """
    Cria o ConversationHandler para exploração da base.
    """
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                handle_explorar_callback, pattern='^explorar_filtrar$'
            ),
        ],
        states={
            AGUARDANDO_FILTRO_UF: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, handle_filtro_uf
                ),
            ],
            AGUARDANDO_FILTRO_CIDADE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, handle_filtro_cidade
                ),
            ],
            AGUARDANDO_FILTRO_BAIRRO: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, handle_filtro_bairro
                ),
            ],
            AGUARDANDO_FILTRO_OPERADORA: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, handle_filtro_operadora
                ),
            ],
            AGUARDANDO_FILTRO_TIPO: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, handle_filtro_tipo
                ),
            ],
            AGUARDANDO_FILTRO_STATUS: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, handle_filtro_status
                ),
            ],
        },
        fallbacks=[
            CommandHandler('cancelar', cancelar_exploracao),
            CallbackQueryHandler(
                handle_explorar_callback,
                pattern=r'^(explorar_|voltar_filtros|voltar_resultados|'
                r'executar_busca|limpar_filtros|refazer_busca|'
                r'ver_endereco_|anotar_|filtro_).*$'
            ),
        ],
        allow_reentry=True,
        per_message=False,
        # False é correto para ConversationHandlers com MessageHandler
    )
