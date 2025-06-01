"""
Handler para visualização detalhada de endereços.

Este módulo contém todos os handlers e callbacks relacionados à
exibição de endereços, incluindo visualização única, múltiplos
resultados e callbacks de navegação.
"""

import logging
from typing import Any, Dict, List

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler

from ..formatters.anotacao import (
    filtrar_anotacoes_por_privilegio,
    formatar_anotacoes_para_exibicao,
)
from ..formatters.endereco import formatar_endereco_detalhado
from ..keyboards import (
    criar_botoes_acao_endereco,
    criar_botoes_nenhum_resultado,
)
from ..services.anotacao import listar_anotacoes_por_endereco
from ..services.auth import obter_nivel_acesso_usuario
from ..services.endereco import buscar_endereco_por_codigo
from ..services.resultado_paginacao import ResultadoPaginador
from ..shared.types import SELECIONANDO_TIPO_CODIGO

logger = logging.getLogger(__name__)


async def exibir_endereco_completo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    endereco: Dict[str, Any],
) -> None:
    """
    Exibe os detalhes completos de um endereço com anotações e botões de ação.

    Args:
        update: Update do Telegram
        context: Context do bot
        endereco: Dados do endereço
    """
    try:
        # Formatar detalhes do endereço
        # Presume-se que formatar_endereco_detalhado já escapa corretamente.
        detalhes_endereco = formatar_endereco_detalhado(endereco)

        # Buscar anotações do endereço
        id_sistema = endereco.get('id_sistema') or endereco.get('id')
        usuario_id = context.user_data.get('usuario_id')
        user_id_telegram = context.user_data.get('user_id_telegram')

        anotacoes: List[Dict[str, Any]] = []
        if id_sistema:
            try:
                logger.info(
                    f'Buscando anotações para endereço {id_sistema} com '
                    f'usuario_id={usuario_id} e user_id_telegram='
                    f'{user_id_telegram}'
                )
                anotacoes = await listar_anotacoes_por_endereco(
                    id_sistema=id_sistema,
                    usuario_id=usuario_id,
                    user_id_telegram=user_id_telegram,
                )
                logger.info(
                    f'Anotações encontradas: {len(anotacoes)} itens: '
                    f'{anotacoes}'
                )
            except Exception as e:
                logger.warning(
                    f'Erro ao buscar anotações para endereço {id_sistema}: '
                    f'{str(e)}'
                )

        # Montar mensagem completa
        # A string inicial já é formatada para MarkdownV2 e
        #  não contém caracteres problemáticos.
        mensagem_partes = ['🏠 *Endereço Encontrado*\n', detalhes_endereco]

        if anotacoes:
            nivel_acesso = await obter_nivel_acesso_usuario(user_id_telegram)
            logger.info(
                f'[FILTRO_ANOTACOES] exibir_endereco_completo: aplicando '
                f'filtro para usuário {usuario_id}, nivel: {nivel_acesso}'
            )
            anotacoes_proprias, anotacoes_outras = (
                filtrar_anotacoes_por_privilegio(
                    anotacoes, usuario_id, nivel_acesso
                )
            )

            # Usar a função corrigida de formatação
            anotacoes_formatadas = formatar_anotacoes_para_exibicao(
                anotacoes_proprias, anotacoes_outras
            )
            mensagem_partes.append('\n\n')
            mensagem_partes.append(anotacoes_formatadas)

        else:
            mensagem_partes.append('\n\n📝 *Anotações:*\n')
            mensagem_partes.append(
                '_Nenhuma anotação encontrada para este endereço\\._'
            )

        mensagem_final_escapada = ''.join(mensagem_partes)

        # Log da mensagem final antes do envio para depuração
        logger.debug(
            f'Mensagem final a ser enviada (escapada):\n{
                mensagem_final_escapada
            }'
        )

        # Criar botões de ação
        keyboard = (
            criar_botoes_acao_endereco(id_sistema)
            if id_sistema
            else criar_botoes_nenhum_resultado()
        )

        target_message = update.effective_message
        if not target_message and update.callback_query:
            target_message = update.callback_query.message

        if not target_message:
            logger.error(
                'Não foi possível determinar a mensagem alvo para resposta'
                ' em exibir_endereco_completo.'
            )
            return

        await target_message.reply_text(
            text=mensagem_final_escapada,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboard,
        )

    except Exception as e:
        logger.error(f'Erro ao exibir endereço completo: {str(e)}')
        target_message_on_error = update.effective_message
        if not target_message_on_error and update.callback_query:
            target_message_on_error = update.callback_query.message

        if target_message_on_error:
            await target_message_on_error.reply_text(
                '😞 Erro ao exibir detalhes do endereço. Tente novamente.'
            )


async def exibir_multiplos_resultados(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    resultados: list,
    codigo: str,
    nome_tipo: str,
) -> int:
    """
    Exibe lista de múltiplos resultados para seleção com paginação.
    Utiliza o serviço ResultadoPaginador para criar a página.

    Retorna o estado SELECIONANDO_TIPO_CODIGO para manter o
    ConversationHandler ativo.
    """
    try:
        # Armazena os dados necessários no contexto
        context.user_data['resultados_busca'] = resultados
        context.user_data['codigo_busca'] = codigo
        context.user_data['nome_tipo_busca'] = nome_tipo

        # Se a página atual não estiver definida, inicializa com 0
        if 'pagina_atual_multiplos' not in context.user_data:
            context.user_data['pagina_atual_multiplos'] = 0

        # Obtém o tipo de código da busca do contexto
        tipo_codigo_busca = context.user_data.get(
            'tipo_codigo_selecionado', ''
        )

        # Define a página atual
        pagina_atual = context.user_data.get('pagina_atual_multiplos', 0)

        # Utiliza o serviço de paginação para criar a página
        resultado = await ResultadoPaginador.criar_pagina_multiplos_resultados(
            resultados=resultados,
            codigo=codigo,
            nome_tipo=nome_tipo,
            tipo_codigo_busca=tipo_codigo_busca,
            nova_pagina=pagina_atual,
        )

        if resultado is None:
            logger.error(
                'Erro ao criar página de múltiplos resultados:'
                ' resultado é None'
            )
            if update.effective_chat:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text='Erro ao exibir os resultados. Tente uma nova busca.',
                )
            return ConversationHandler.END

        mensagem, reply_markup = resultado

        # Determina o alvo para enviar a mensagem
        target_message = update.effective_message
        if not target_message and update.callback_query:
            target_message = update.callback_query.message

        if not target_message:
            logger.error(
                'Não foi possível determinar a mensagem alvo para resposta'
            )
            return ConversationHandler.END

        await target_message.reply_text(
            text=mensagem,
            parse_mode='MarkdownV2',
            reply_markup=reply_markup,
        )

        # Retorna o estado para manter o ConversationHandler ativo
        return SELECIONANDO_TIPO_CODIGO

    except Exception as e:
        logger.error(f'Erro ao exibir múltiplos resultados: {e}')
        if update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=(
                    'Ocorreu um erro ao exibir os resultados. '
                    'Tente uma nova busca.'
                ),
            )
        return ConversationHandler.END


async def show_endereco_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Handler para o callback 'show_endereco_{id_sistema}'.
    Exibe novamente os detalhes completos do endereço.
    """
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    # Extrai o id_sistema do callback
    try:
        id_sistema = int(query.data.replace('show_endereco_', ''))
    except Exception:
        await query.edit_message_text('ID do endereço inválido.')
        return

    usuario_id = context.user_data.get('usuario_id')
    user_id_telegram = context.user_data.get('user_id_telegram')
    if not usuario_id or not user_id_telegram:
        await query.edit_message_text('Usuário não autenticado. Tente /start.')
        return

    try:
        # Busca o endereço pelo ID
        endereco_data = await buscar_endereco_por_codigo(
            codigo=str(id_sistema),
            tipo_codigo='id_sistema',
            usuario_id=usuario_id,
            user_id_telegram=user_id_telegram,
        )

        if not endereco_data or len(endereco_data) == 0:
            await query.edit_message_text(
                'Endereço não encontrado. Pode ter sido removido.'
            )
            return

        endereco = endereco_data[0]

        # Deleta a mensagem atual e exibe o endereço completo
        try:
            await query.delete_message()
        except Exception as e:
            logger.info(f'Não foi possível deletar a mensagem: {e}')

        # Exibe o endereço completo usando a função existente
        await exibir_endereco_completo(update, context, endereco)

    except Exception as e:
        logger.error(f'Erro ao exibir endereço {id_sistema}: {e}')
        await query.edit_message_text(
            'Erro ao carregar o endereço. Tente novamente.'
        )


async def paginacao_multiplos_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handler para os callbacks de paginação dos múltiplos resultados.
    Delega para o novo serviço de paginação.
    """
    # Delegar para o serviço de paginação
    await ResultadoPaginador.processar_paginacao_multiplos_callback(
        update, context
    )


async def ver_todas_anotacoes_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Handler para o callback 'ver_anotacoes_{id_sistema}'.
    Exibe todas as anotações do endereço, agrupando próprias e de outros.
    Aplica verificação de privilégios: usuários básicos só veem suas próprias.
    """
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    # Extrai o id_sistema do callback
    try:
        id_sistema = int(query.data.replace('ver_anotacoes_endereco_id_', ''))
    except Exception:
        await query.edit_message_text('ID do endereço inválido.')
        return

    usuario_id = context.user_data.get('usuario_id')
    user_id_telegram = context.user_data.get('user_id_telegram')
    if not usuario_id or not user_id_telegram:
        await query.edit_message_text('Usuário não autenticado. Tente /start.')
        return

    # Obter nível de acesso do usuário
    nivel_acesso = await obter_nivel_acesso_usuario(user_id_telegram)

    # Buscar anotações
    try:
        anotacoes = await listar_anotacoes_por_endereco(
            id_sistema=id_sistema,
            usuario_id=usuario_id,
            user_id_telegram=user_id_telegram,
        )
    except Exception as e:
        logger.error(f'Erro ao buscar anotações para ver todas: {e}')
        await query.edit_message_text(
            'Erro ao buscar anotações. Tente novamente.'
        )
        return

    if not anotacoes:
        await query.edit_message_text(
            'Nenhuma anotação encontrada para este endereço.'
        )
        return

    # Filtrar anotações baseado em privilégios
    anotacoes_proprias, anotacoes_outras = filtrar_anotacoes_por_privilegio(
        anotacoes, usuario_id, nivel_acesso
    )

    # Formatar mensagem
    mensagem = formatar_anotacoes_para_exibicao(
        anotacoes_proprias, anotacoes_outras
    )

    # Botão para voltar ao endereço
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                '⬅️ Voltar ao endereço',
                callback_data=f'show_endereco_{id_sistema}',
            )
        ]
    ])

    try:
        await query.edit_message_text(
            text=mensagem,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboard,
        )
    except Exception as e:
        logger.error(f'Erro ao exibir todas as anotações: {e}')
        await query.edit_message_text('Erro ao exibir anotações.')
