"""
Handlers para comandos de anotação.
"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,  # Movido para o topo
    CommandHandler,  # Movido para o topo
    ContextTypes,
    ConversationHandler,
    MessageHandler,  # Movido para o topo
    filters,  # Movido para o topo
)

from lima.bot.handlers.menu import exibir_menu_principal
from lima.schemas import AnotacaoRead  # Importa o schema Pydantic

from ..formatters.base import escape_markdown
from ..formatters.endereco import formatar_endereco
from ..keyboards import (
    criar_teclado_confirma_cancelar,
    teclado_endereco_nao_encontrado_criar,  # Adicionado
    teclado_simples_cancelar_anotacao,  # Adicionado
)
from ..services.anotacao import criar_anotacao, listar_anotacoes
from ..services.endereco import (  # Adicionado FiltrosEndereco
    FiltrosEndereco,
    buscar_endereco,
)
from .busca_codigo import iniciar_busca_rapida

logger = logging.getLogger(__name__)

# Estados para a conversa de anotação
ID_ENDERECO, TEXTO, CONFIRMAR = range(3)


async def iniciar_anotacao_por_id(
    update: Update, context: ContextTypes.DEFAULT_TYPE, endereco_id: str
) -> int:
    """
    Inicia o fluxo de anotação com o ID do endereço já conhecido.
    Usado quando vem do sistema de exploração da base.

    Args:
        update: Update do Telegram
        context: Context do Telegram
        endereco_id: ID do endereço (como string)

    Returns:
        Próximo estado da conversa
    """
    query = update.callback_query
    await query.answer()

    logger.info(
        f'[iniciar_anotacao_por_id] INICIADO com endereco_id: {endereco_id}'
    )

    if not update.effective_user:
        logger.error(
            '[iniciar_anotacao_por_id] Não foi possível obter effective_user.'
        )
        await query.edit_message_text(
            '😞 Ocorreu um erro ao processar sua identidade. '
            'Por favor, tente novamente mais tarde.'
        )
        return ConversationHandler.END

    try:
        id_endereco = int(endereco_id)
    except ValueError:
        logger.error(f'[iniciar_anotacao_por_id] ID inválido: {endereco_id}')
        await query.edit_message_text(
            '❌ ID do endereço inválido.',
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        '↩️ Voltar', callback_data='voltar_resultados'
                    )
                ]
            ]),
        )
        return ConversationHandler.END

    user_id_telegram = update.effective_user.id
    context.user_data['user_id_telegram'] = user_id_telegram
    context.user_data['id_endereco_anotacao'] = id_endereco

    # Buscar dados do endereço para confirmação
    try:
        filtros = FiltrosEndereco(limite=1)
        enderecos = await buscar_endereco(
            filtros=filtros,
            id_endereco=id_endereco,
            user_id=user_id_telegram,
        )

        if not enderecos or len(enderecos) == 0:
            await query.edit_message_text(
                '⚠️ Endereço não encontrado.',
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            '↩️ Voltar', callback_data='voltar_resultados'
                        )
                    ]
                ]),
            )
            return ConversationHandler.END

        endereco = enderecos[0]
        await query.edit_message_text(
            f'📝 *Adicionar Anotação*\n\n'
            f'Endereço selecionado:\n{formatar_endereco(endereco)}\n\n'
            f'Por favor, digite o texto da sua anotação:',
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=teclado_simples_cancelar_anotacao(),
        )
        return TEXTO

    except Exception as e:
        logger.error(f'Erro ao buscar endereço para anotação: {str(e)}')
        await query.edit_message_text(
            '😞 Ocorreu um erro ao buscar os dados do endereço. '
            'Por favor, tente novamente mais tarde.',
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        '↩️ Voltar', callback_data='voltar_resultados'
                    )
                ]
            ]),
        )
        return ConversationHandler.END


def _extrair_id_endereco_callback(query, context):
    """Extrai e valida o id_endereco a partir do callback ou contexto."""
    if not query.data or not (
        query.data.startswith('fazer_anotacao_')
        or query.data.startswith('anotar_')
    ):
        id_endereco_contexto = context.user_data.get(
            'endereco_id_para_anotacao'
        )
        if id_endereco_contexto:
            return int(id_endereco_contexto), None
        else:
            return None, '❌ Ocorreu um erro ao processar sua solicitação.'
    else:
        try:
            return int(query.data.split('_')[-1]), None
        except (IndexError, ValueError):
            return None, '❌ Erro ao identificar o endereço para anotação.'


async def iniciar_anotacao_por_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Inicia o fluxo de anotação a partir de um callback query
      (botão "Fazer Anotação").
    """
    query = update.callback_query
    await query.answer()

    logger.info(
        f'[iniciar_anotacao_por_callback] INICIADO com callback_data: '
        f'{query.data}'
    )
    logger.info(
        f'[iniciar_anotacao_por_callback] user_data atual: {context.user_data}'
    )

    # Verificar se o usuário está vindo de uma busca rápida ativa
    if 'tipo_codigo_selecionado' in context.user_data:
        context.user_data['veio_de_busca_rapida'] = True
        logger.info(
            '[iniciar_anotacao_por_callback] Detectada busca rápida ativa'
        )

    id_endereco, erro_id = _extrair_id_endereco_callback(query, context)
    if erro_id:
        logger.warning(
            f'[iniciar_anotacao_por_callback] Erro ao extrair id_endereco: {
                erro_id
            }'
        )
        try:
            await query.edit_message_text(erro_id)
        except Exception:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=erro_id,
            )
        return ConversationHandler.END
    if not update.effective_user:
        logger.error(
            '[iniciar_anotacao_por_callback] Não foi possível obter'
            ' effective_user.'
        )
        try:
            await query.edit_message_text(
                '😞 Ocorreu um erro ao processar sua identidade. '
                'Por favor, tente novamente mais tarde.'
            )
        except Exception:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text='😞 Ocorreu um erro ao processar sua identidade. '
                'Por favor, tente novamente mais tarde.',
            )
        return ConversationHandler.END

    user_id_telegram = update.effective_user.id
    context.user_data['user_id_telegram'] = user_id_telegram
    context.user_data['id_endereco_anotacao'] = id_endereco

    logger.info(
        f'[iniciar_anotacao_por_callback] Usuário {user_id_telegram} '
        f'iniciando anotação para id_endereco: {id_endereco} via callback.'
    )

    try:
        enderecos = await _buscar_endereco_para_anotacao(
            id_endereco, user_id_telegram, query, context
        )
        if not enderecos or len(enderecos) == 0:
            logger.warning(
                f'[iniciar_anotacao_por_callback] Endereço {id_endereco} '
                f'(de callback) não encontrado para usuário '
                f'{user_id_telegram}.'
            )
            await query.edit_message_text(
                text='⚠️ O endereço associado a esta anotação não'
                ' foi encontrado. '
                'Pode ter sido removido. Por favor,'
                ' tente iniciar uma nova busca.'
            )
            context.user_data.pop('id_endereco_anotacao', None)
            return ConversationHandler.END

        endereco = enderecos[0]
        await query.edit_message_text(
            text=f'📝 *Adicionar Anotação*\n\n'
            f'Endereço selecionado:\n{formatar_endereco(endereco)}\n\n'
            f'Por favor, digite o texto da sua anotação:',
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=teclado_simples_cancelar_anotacao(),
        )
        return TEXTO
    except Exception as e:
        logger.error(
            f'[iniciar_anotacao_por_callback] Erro ao buscar endereço '
            f'{id_endereco} para anotação via callback: {str(e)}'
        )
        try:
            await query.edit_message_text(
                '😞 Ocorreu um erro ao buscar os dados do endereço. '
                'Por favor, tente novamente mais tarde.'
            )
        except Exception:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text='😞 Ocorreu um erro ao buscar os dados do endereço. '
                'Por favor, tente novamente mais tarde.',
            )
        return ConversationHandler.END


# Função de logging temporário removida após conclusão do debugging


async def anotar_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Handler para o comando /anotar.
    Inicia o fluxo de conversa para adicionar uma anotação.
    """
    if not update.effective_user:
        logger.error(
            'Não foi possível obter effective_user no handler anotar_command.'
        )
        await update.message.reply_text(
            '😞 Ocorreu um erro ao processar sua identidade. '
            'Por favor, tente novamente mais tarde.'
        )
        return ConversationHandler.END
    user_id_telegram = update.effective_user.id
    context.user_data['user_id_telegram'] = user_id_telegram

    if context.args and len(context.args) > 0 and context.args[0].isdigit():
        id_endereco = int(context.args[0])
        context.user_data['id_endereco_anotacao'] = id_endereco

        try:
            filtros = FiltrosEndereco(limite=1)
            enderecos = await buscar_endereco(
                filtros=filtros,
                id_endereco=id_endereco,
                user_id=user_id_telegram,
            )

            if not enderecos or len(enderecos) == 0:
                await update.message.reply_text(
                    (
                        '⚠️ Endereço não encontrado. Verifique o ID ou tente'
                        ' outro.'
                    ),
                    reply_markup=teclado_endereco_nao_encontrado_criar(),
                )
                return ID_ENDERECO

            endereco = enderecos[0]
            await update.message.reply_text(
                f'📝 *Adicionar Anotação*\n\n'
                f'Endereço selecionado:\n{formatar_endereco(endereco)}\n\n'
                f'Por favor, digite o texto da sua anotação:',
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=teclado_simples_cancelar_anotacao(),
            )
            return TEXTO
        except Exception as e:
            logger.error(f'Erro ao buscar endereço para anotação: {str(e)}')
            await update.message.reply_text(
                '😞 Ocorreu um erro ao buscar os dados do endereço. '
                'Por favor, tente novamente mais tarde.'
            )
            return ConversationHandler.END

    await update.message.reply_text(
        '📝 *Adicionar Anotação*\n\n'
        'Por favor, informe o ID ou código do endereço que deseja anotar:',
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=teclado_simples_cancelar_anotacao(),
    )
    return ID_ENDERECO


async def receber_id_endereco(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Recebe o ID ou código do endereço para adicionar uma anotação.
    """
    if not update.message or not update.message.text:
        await update.message.reply_text(
            'Por favor, envie um ID ou código de endereço válido.',
            reply_markup=teclado_simples_cancelar_anotacao(),
        )
        return ID_ENDERECO

    texto_id_ou_codigo = update.message.text.strip()

    if not update.effective_user:
        logger.error(
            'Não foi possível obter effective_user'
            ' no handler receber_id_endereco.'
        )
        await update.message.reply_text(
            '😞 Ocorreu um erro ao processar sua identidade. '
            'Por favor, tente novamente mais tarde.'
        )
        return ConversationHandler.END

    user_id_telegram = update.effective_user.id
    context.user_data['user_id_telegram'] = user_id_telegram

    try:
        filtros = FiltrosEndereco(limite=1)
        # Tenta buscar por ID numérico ou por código_endereco
        if texto_id_ou_codigo.isdigit():
            enderecos = await buscar_endereco(
                filtros=filtros,
                id_endereco=int(texto_id_ou_codigo),
                user_id=user_id_telegram,
            )
        else:
            enderecos = await buscar_endereco(
                filtros=filtros,
                codigo_endereco=texto_id_ou_codigo,
                user_id=user_id_telegram,
            )

        if not enderecos or len(enderecos) == 0:
            await update.message.reply_text(
                (
                    '⚠️ Endereço não encontrado. Verifique o ID/código ou'
                    ' tente outro.'
                ),
                reply_markup=teclado_endereco_nao_encontrado_criar(),
            )
            return ID_ENDERECO

        endereco = enderecos[0]
        context.user_data['id_endereco_anotacao'] = endereco.id

        await update.message.reply_text(
            f'📝 *Adicionar Anotação*\n\n'
            f'Endereço selecionado:\n{formatar_endereco(endereco)}\n\n'
            f'Por favor, digite o texto da sua anotação:',
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=teclado_simples_cancelar_anotacao(),
        )
        return TEXTO
    except Exception as e:
        logger.error(f'Erro ao buscar endereço para anotação: {str(e)}')
        await update.message.reply_text(
            '😞 Ocorreu um erro ao buscar os dados do endereço. '
            'Por favor, tente novamente mais tarde.'
        )
        return ConversationHandler.END


async def receber_texto_anotacao(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Recebe o texto da anotação.
    """
    user_id_telegram = 'ID Desconhecido'
    if update.effective_user:
        user_id_telegram = update.effective_user.id

    texto_recebido = 'Texto não recebido'
    if update.message and update.message.text:
        texto_recebido = update.message.text

    logger.info(
        f'[receber_texto_anotacao] Usuário {user_id_telegram} enviou texto: '
        f"'{texto_recebido}'"
    )

    if not update.message or not update.message.text:
        await update.message.reply_text(
            'Por favor, envie um texto para a anotação.',
            reply_markup=teclado_simples_cancelar_anotacao(),
        )
        return TEXTO  # Permanece no mesmo estado para nova tentativa

    context.user_data['texto_anotacao'] = update.message.text
    id_endereco = context.user_data.get('id_endereco_anotacao')
    logger.info(
        f'[receber_texto_anotacao] Usuário {user_id_telegram} - '
        f'id_endereco_anotacao de user_data: {id_endereco}'
    )

    if id_endereco is None:
        logger.warning(
            f'[receber_texto_anotacao] Usuário {user_id_telegram} - '
            'id_endereco_anotacao não encontrado em user_data. Encerrando.'
        )
        await update.message.reply_text(
            '❌ ID do endereço não encontrado na conversa. '
            'Por favor, comece novamente com /anotar.'
        )
        return ConversationHandler.END

    mensagem = (
        f'📋 *Confirmação de Anotação*\n\n'
        f'ID do Endereço: *{escape_markdown(str(id_endereco))}*\n\n'
        f'Texto da Anotação:\n'
        f'{escape_markdown(context.user_data["texto_anotacao"])}\n\n'
        'Confirma o envio desta anotação?'
    )

    await update.message.reply_text(
        mensagem,
        reply_markup=criar_teclado_confirma_cancelar(
            prefixo='finalizar_anotacao'  # Corrigido: Usa apenas 'prefixo'
        ),
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    logger.info(
        f'[receber_texto_anotacao] Usuário {user_id_telegram} - '
        'Indo para o estado CONFIRMAR.'
    )
    return CONFIRMAR


async def finalizar_anotacao(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Finaliza o processo de anotação após confirmação ou cancelamento.
    """
    query = update.callback_query
    await query.answer()

    user_id_telegram = 'ID Desconhecido'
    if update.effective_user:
        user_id_telegram = update.effective_user.id

    logger.info(
        f'[finalizar_anotacao] Usuário {user_id_telegram} - '
        f'Callback recebido: {query.data}'
    )

    id_endereco = context.user_data.get('id_endereco_anotacao')
    texto_anotacao = context.user_data.get('texto_anotacao')
    logger.info(
        f'[finalizar_anotacao] Usuário {user_id_telegram} - user_data: '
        f"id_endereco={id_endereco}, texto_anotacao='{texto_anotacao}'"
    )

    # Modificado para corresponder ao prefixo
    #  'finalizar_anotacao' e sufixos _sim/_nao
    if query.data == 'finalizar_anotacao_nao':
        logger.info(
            f'[finalizar_anotacao] Usuário {user_id_telegram} '
            'cancelou a anotação.'
        )
        await query.edit_message_text(text='❌ Anotação cancelada.')
        return ConversationHandler.END

    if query.data == 'finalizar_anotacao_sim':
        if id_endereco is None or texto_anotacao is None:
            logger.error(
                f'[finalizar_anotacao] Usuário {user_id_telegram} - Erro: '
                'id_endereco ou texto_anotacao ausentes em user_data ao '
                'confirmar.'
            )
            await query.edit_message_text(
                text='❌ Erro ao confirmar anotação. Tente novamente.'
            )
            return ConversationHandler.END

        try:
            logger.info(
                f'[finalizar_anotacao] Usuário {user_id_telegram} confirmou. '
                'Tentando criar anotação para id_endereco: '
                f'{id_endereco}.'
            )
            sucesso, mensagem_erro = await criar_anotacao(
                id_endereco=id_endereco,
                texto=texto_anotacao,
                user_id=user_id_telegram,
            )
            if sucesso:
                logger.info(
                    f'[finalizar_anotacao] Usuário {user_id_telegram} - '
                    'Anotação criada com sucesso para id_endereco: '
                    f'{id_endereco}.'
                )
                await query.edit_message_text(
                    text=f'✅ Anotação enviada com sucesso! ID: {sucesso.get("id")}'  # noqa: E501
                )
            else:
                logger.error(
                    f'[finalizar_anotacao] Usuário {user_id_telegram} - '
                    'Falha ao criar anotação para id_endereco: '
                    f'{id_endereco}. Erro: {mensagem_erro}'
                )
                await query.edit_message_text(
                    text=f'❌ Erro ao salvar anotação: {escape_markdown(mensagem_erro)}'  # noqa: E501
                )
        except Exception:
            logger.exception(
                f'[finalizar_anotacao] Usuário {user_id_telegram} - '
                'Exceção ao criar anotação para id_endereco: '
                f'{id_endereco}.'
            )
            await query.edit_message_text(
                text='😞 Ocorreu um erro ao enviar sua anotação. Por favor,'
                ' tente novamente mais tarde.'
            )

    return ConversationHandler.END


async def _enviar_msg_cancelamento(
    update, context, query, message, texto='❌ Processo de anotação cancelado.'
):
    """Envia mensagem de cancelamento de forma centralizada."""
    if query:
        try:
            await query.edit_message_text(texto)
            logger.info('[cancelar_anotacao] Mensagem editada com sucesso.')
            return
        except Exception as e:
            logger.warning(f'Não foi possível editar mensagem: {e}')
            try:
                await query.message.reply_text(texto)
                logger.info(
                    '[cancelar_anotacao] Nova mensagem enviada com sucesso.'
                )
                return
            except Exception as e2:
                logger.error(
                    'Falha ao enviar mensagem alternativa de cancelamento: '
                    f'{e2}'
                )
    if message:
        try:
            await message.reply_text(texto)
            logger.info(
                '[cancelar_anotacao] Mensagem enviada via comando /cancelar.'
            )
            return
        except Exception as e:
            logger.error(
                f'Falha ao enviar mensagem de cancelamento via comando: {e}'
            )
    chat_id = context.user_data.get('chat_id') or (
        update.effective_chat and update.effective_chat.id
    )
    if chat_id:
        try:
            await context.bot.send_message(chat_id=chat_id, text=texto)
            logger.info(
                '[cancelar_anotacao] Mensagem enviada via send_message.'
            )
        except Exception as e:
            logger.error(
                'Falha ao enviar mensagem de cancelamento via send_message: '
                f'{e}'
            )


async def cancelar_anotacao(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Cancela a operação de anotação."""
    user_id_telegram = 'ID Desconhecido'
    if update.effective_user:
        user_id_telegram = update.effective_user.id

    logger.info(
        f'[cancelar_anotacao] Usuário {user_id_telegram} cancelou a anotação.'
    )
    message = update.message or (
        update.callback_query and update.callback_query.message
    )
    query = update.callback_query

    if query:
        await query.answer()
    await _enviar_msg_cancelamento(update, context, query, message)

    for key in ['id_endereco_anotacao', 'texto_anotacao', 'user_id_telegram']:
        context.user_data.pop(key, None)

    # Após cancelar, verificar se veio de busca rápida
    veio_de_busca_rapida = context.user_data.get('veio_de_busca_rapida', False)

    if veio_de_busca_rapida:
        # Limpar o flag
        context.user_data.pop('veio_de_busca_rapida', None)

        # Retornar para a busca rápida no estado inicial
        try:
            logger.info('Retornando para busca rápida após cancelar anotação')
            # Chamar iniciar_busca_rapida e retornar o estado correto
            return await iniciar_busca_rapida(update, context)
        except Exception as e:
            logger.error(f'Erro ao retornar para busca rápida: {e}')
            # Fallback: mostrar menu principal
            try:
                await exibir_menu_principal(
                    update, context, editar_mensagem=True
                )
            except Exception as e2:
                logger.error(f'Erro crítico no fallback: {e2}')
    else:
        # Comportamento padrão: exibir menu principal
        try:
            await exibir_menu_principal(update, context, editar_mensagem=True)
        except Exception as e:
            logger.error(
                f'Erro ao exibir menu principal após cancelar anotação: {e}'
            )
            # Fallback: tentar enviar uma nova mensagem
            try:
                await exibir_menu_principal(
                    update, context, editar_mensagem=False
                )
            except Exception as e2:
                logger.error(f'Erro crítico no fallback: {e2}')
    return ConversationHandler.END


async def listar_anotacoes_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Lista as anotações do usuário ou de um endereço específico.
    """
    if not update.effective_user:
        logger.error(
            'Não foi possível obter effective_user'
            ' no handler listar_anotacoes_command.'
        )
        await update.message.reply_text(
            '😞 Ocorreu um erro ao processar sua identidade. '
            'Por favor, tente novamente mais tarde.'
        )
        return
    user_id_telegram = update.effective_user.id

    id_endereco_arg = None
    if context.args and context.args[0].isdigit():
        id_endereco_arg = int(context.args[0])

    try:
        filtros = FiltrosEndereco()
        anotacoes_dicts = await listar_anotacoes(
            id_usuario=user_id_telegram if not id_endereco_arg else None,
            id_endereco=id_endereco_arg,
            user_id=user_id_telegram,
        )
        if not anotacoes_dicts:
            if id_endereco_arg:
                # Usar escape_markdown para tudo, inclusive o ponto final
                texto_base = (
                    f'Você não possui anotações para o endereço com ID '
                    f'{id_endereco_arg}.'
                )
                mensagem_sem_anotacoes = escape_markdown(texto_base)
                await update.message.reply_text(
                    mensagem_sem_anotacoes, parse_mode=ParseMode.MARKDOWN_V2
                )
            else:
                mensagem_sem_anotacoes = escape_markdown(
                    'Você ainda não possui nenhuma anotação.'
                )
                await update.message.reply_text(
                    mensagem_sem_anotacoes, parse_mode=ParseMode.MARKDOWN_V2
                )
            return

        # Construir mensagem de forma mais limpa
        mensagem = '📝 *Suas Anotações*\n\n'

        for anotacao_dict in anotacoes_dicts:
            try:
                anotacao_obj = AnotacaoRead.model_validate(anotacao_dict)
            except Exception as e:
                logger.error(
                    f'Erro ao validar anotação: {anotacao_dict}. Erro: {e}'
                )
                continue

            endereco_anotacao_list = await buscar_endereco(
                filtros=filtros,
                id_endereco=anotacao_obj.id_endereco,
                user_id=user_id_telegram,
            )
            if endereco_anotacao_list and len(endereco_anotacao_list) > 0:
                endereco_formatado = formatar_endereco(
                    endereco_anotacao_list[0]
                )
                # endereco_formatado já vem escapado, não aplicar escape
                #  novamente
                # Apenas escapar os textos que não são markdown
                mensagem += f'📍 *Endereço*: {endereco_formatado}\n'
                mensagem += (
                    f'📝 *Anotação*: {escape_markdown(anotacao_obj.texto)}\n'
                )
                mensagem += '\n'  # Linha em branco entre anotações
            else:
                id_endereco_str = str(anotacao_obj.id_endereco)
                # Escapar apenas os dados dinâmicos, não a formatação markdown
                mensagem += (
                    f'⚠️ *Endereço ID {escape_markdown(id_endereco_str)} '
                    f'não encontrado ou inacessível*\n'
                )
                mensagem += (
                    f'📝 *Anotação*: {escape_markdown(anotacao_obj.texto)}\n'
                )
                mensagem += '\n'  # Linha em branco entre anotações

        # Enviar mensagem final
        await update.message.reply_text(
            mensagem, parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f'Erro ao listar anotações: {str(e)}')
        await update.message.reply_text(
            '😞 Ocorreu um erro ao listar as anotações. '
            'Por favor, tente novamente mais tarde.'
        )


async def _buscar_endereco_para_anotacao(
    id_endereco, user_id_telegram, query, context
):
    """Busca o endereço e retorna o objeto ou mensagem de erro."""
    filtros = FiltrosEndereco(limite=1)
    return await buscar_endereco(
        filtros=filtros, id_endereco=id_endereco, user_id=user_id_telegram
    )


def get_anotacao_conversation() -> ConversationHandler:
    """
    Retorna o ConversationHandler para o fluxo de anotação.
    """
    logger.info(
        '[get_anotacao_conversation] Criando ConversationHandler de anotação'
    )

    return ConversationHandler(
        entry_points=[
            CommandHandler('anotar', anotar_command),
            CallbackQueryHandler(
                iniciar_anotacao_por_callback,
                pattern=r'^(fazer_anotacao_|anotar_)\d+$',
            ),
        ],
        states={
            ID_ENDERECO: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receber_id_endereco,
                )
            ],
            TEXTO: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receber_texto_anotacao,
                )
            ],
            CONFIRMAR: [
                CallbackQueryHandler(
                    finalizar_anotacao,
                    pattern=r'^finalizar_anotacao_sim$',
                    # Corresponde a prefixo_sim
                ),
                CallbackQueryHandler(
                    finalizar_anotacao,  # Trata o _nao também
                    pattern=r'^finalizar_anotacao_nao$',
                    # Corresponde a prefixo_nao
                ),
            ],
        },
        fallbacks=[
            CommandHandler('cancelar', cancelar_anotacao),
            CallbackQueryHandler(
                cancelar_anotacao, pattern=r'^cancelar_anotacao_simples$'
            ),
            CallbackQueryHandler(
                cancelar_anotacao, pattern=r'^cancelar_processo_anotacao$'
            ),
            CallbackQueryHandler(
                cancelar_anotacao, pattern=r'^finalizar_anotacao_nao$'
            ),  # Garante limpeza no cancelamento da confirmação
        ],
        per_message=False,  # False porque há MessageHandlers nos estados
        per_user=True,
        per_chat=True,
        # name="anotacao_conversation",  # Para persistência
        # persistent=True,  # Para persistência
    )
