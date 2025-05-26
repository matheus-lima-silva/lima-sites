"""
Handlers para comandos de anotação.
"""

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,  # Movido para o topo
    CommandHandler,  # Movido para o topo
    ContextTypes,
    ConversationHandler,
    MessageHandler,  # Movido para o topo
    filters,  # Movido para o topo
)

from ..formatters import escape_markdown, formatar_endereco
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

logger = logging.getLogger(__name__)

# Estados para a conversa de anotação
ID_ENDERECO, TEXTO, CONFIRMAR = range(3)


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

    if not query.data or not query.data.startswith('fazer_anotacao_'):
        logger.warning(
            f'[iniciar_anotacao_por_callback] Chamado com dados inválidos: '
            f'{query.data}'
        )
        # Tenta editar a mensagem original se possível, ou envia uma
        #  nova se falhar.
        try:
            await query.edit_message_text(
                '❌ Ocorreu um erro ao processar sua solicitação.'
            )
        except Exception:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text='❌ Ocorreu um erro ao processar sua solicitação.',
            )
        return ConversationHandler.END

    try:
        id_endereco = int(query.data.split('_')[-1])
    except (IndexError, ValueError):
        logger.error(
            f'[iniciar_anotacao_por_callback] Não foi possível extrair '
            f'id_endereco de callback_data: {query.data}'
        )
        try:
            await query.edit_message_text(
                '❌ Erro ao identificar o endereço para anotação.'
            )
        except Exception:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text='❌ Erro ao identificar o endereço para anotação.',
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
        filtros = FiltrosEndereco(limite=1)
        enderecos = await buscar_endereco(
            filtros=filtros, id_endereco=id_endereco, user_id=user_id_telegram
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
            # user_id_telegram é mantido para outros possíveis usos na sessão
            return ConversationHandler.END

        endereco = enderecos[0]
        # Edita a mensagem original do botão para pedir o texto da anotação
        await query.edit_message_text(
            text=f'📝 *Adicionar Anotação*\n\n'
            f'Endereço selecionado:\n{formatar_endereco(endereco)}\n\n'
            f'Por favor, digite o texto da sua anotação:',
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=teclado_simples_cancelar_anotacao(),
            # Reutiliza o teclado de cancelamento
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
        await query.message.reply_text('❌ Processo de anotação cancelado.')
    elif message:  # Se foi um comando /cancelar
        await message.reply_text('❌ Processo de anotação cancelado.')
    else:
        logger.warning('cancelar_anotacao chamado sem query ou message')
        chat_id = context.user_data.get('chat_id') or (
            update.effective_chat and update.effective_chat.id
        )
        if chat_id:
            await context.bot.send_message(
                chat_id=chat_id, text='❌ Processo de anotação cancelado.'
            )

    for key in ['id_endereco_anotacao', 'texto_anotacao', 'user_id_telegram']:
        context.user_data.pop(key, None)

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
        # Atualizado para usar FiltrosEndereco
        # Nenhum filtro específico além do ID,
        #  então um FiltrosEndereco vazio é usado
        # O limite padrão de FiltrosEndereco (10)
        #  não se aplica quando id_endereco é fornecido.
        filtros = FiltrosEndereco()
        anotacoes = await listar_anotacoes(
            id_usuario_telegram=user_id_telegram,
            id_endereco=id_endereco_arg,  # Passa o id_endereco_arg
            user_id=user_id_telegram,
        )
        if not anotacoes:
            if id_endereco_arg:
                mensagem_sem_anotacoes = (
                    f'Você não possui anotações para o endereço com ID '
                    f'{escape_markdown(str(id_endereco_arg))}\\.'
                )
                await update.message.reply_text(
                    mensagem_sem_anotacoes, parse_mode=ParseMode.MARKDOWN_V2
                )
            else:
                await update.message.reply_text(
                    'Você ainda não possui nenhuma anotação.'
                )
            return

        mensagem = '📝 *Suas Anotações*\n\n'
        for anotacao_obj in anotacoes:  # Renomeado para evitar conflito
            # Busca o endereço para cada anotação
            # O ideal seria otimizar isso no backend para evitar N+1 queries
            endereco_anotacao = await buscar_endereco(
                filtros=filtros,
                id_endereco=anotacao_obj.id_endereco,
                user_id=user_id_telegram,
            )
            if endereco_anotacao and len(endereco_anotacao) > 0:
                endereco_formatado = formatar_endereco(endereco_anotacao[0])
                mensagem += (
                    f'📍 *Endereço*: {endereco_formatado}\n'
                    f'📝 *Anotação*: {escape_markdown(anotacao_obj.texto)}\n\n'
                )

        await update.message.reply_text(
            mensagem, parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f'Erro ao listar anotações: {str(e)}')
        await update.message.reply_text(
            '😞 Ocorreu um erro ao listar as anotações. '
            'Por favor, tente novamente mais tarde.'
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
                pattern=r'^fazer_anotacao_(\d+)$',
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
                cancelar_anotacao, pattern=r'^finalizar_anotacao_nao$'
            ),  # Garante limpeza no cancelamento da confirmação
        ],
        per_message=False,
        per_user=True,
        per_chat=True,
        # name="anotacao_conversation",  # Para persistência
        # persistent=True,  # Para persistência
    )
