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


async def anotar_command(
        update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handler para o comando /anotar.
    Inicia o fluxo de conversa para adicionar uma anotação.
    """
    if not update.effective_user:
        logger.error(
            "Não foi possível obter effective_user"
            " no handler anotar_command.")
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
                user_id=user_id_telegram
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
            "Não foi possível obter effective_user"
            " no handler receber_id_endereco.")
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
    if not update.message or not update.message.text:
        await update.message.reply_text(
            'Por favor, envie um texto para a anotação.',
            reply_markup=teclado_simples_cancelar_anotacao(),
        )
        return TEXTO  # Permanece no mesmo estado para nova tentativa

    context.user_data['texto_anotacao'] = update.message.text
    id_endereco = context.user_data.get("id_endereco_anotacao")

    if id_endereco is None:
        await update.message.reply_text(
            '❌ ID do endereço não encontrado na conversa. '
            'Por favor, comece novamente com /anotar.'
        )
        return ConversationHandler.END

    mensagem = (
        f'📋 *Confirmação de Anotação*\n\n'
        f'ID do Endereço: *{escape_markdown(str(id_endereco))}*\n\n'
        f'Texto da Anotação:\n{
            escape_markdown(context.user_data["texto_anotacao"])
        }\n\n'
        'Confirma o envio desta anotação?'
    )

    await update.message.reply_text(
        mensagem,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=criar_teclado_confirma_cancelar(
            callback_prefix='confirma_anotacao',
            texto_confirmar="✅ Confirmar",
            texto_cancelar="❌ Cancelar",
        ),
    )
    return CONFIRMAR


async def finalizar_anotacao(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Finaliza o processo de anotação, enviando-a para a API.
    """
    query = update.callback_query
    await query.answer()

    if query.data != 'confirma_anotacao_sim':
        await query.message.reply_text('❌ Anotação cancelada.')
        return ConversationHandler.END

    # Extrai os dados da anotação
    id_endereco = context.user_data.get('id_endereco_anotacao')
    texto = context.user_data.get('texto_anotacao')
    # usuario_id = context.user_data.get('usuario_id')
    #  # Removido, usaremos user_id_telegram
    user_id_telegram = context.user_data.get('user_id_telegram')
    # Recupera o user_id_telegram

    if not id_endereco or not texto or not user_id_telegram:
        # Verificando user_id_telegram
        await query.message.reply_text(
            '❌ Dados incompletos para enviar a anotação. Por favor,'
            ' tente novamente.'
        )
        return ConversationHandler.END

    # Envia a anotação
    try:
        resultado = await criar_anotacao(
            id_usuario=user_id_telegram,
    # Passa user_id_telegram como id_usuario
            id_endereco=id_endereco,
            texto=texto,
            user_id=user_id_telegram
                # Passa user_id_telegram para autenticação
        )

        await query.message.reply_text(
            f'✅ Anotação enviada com sucesso! ID: {resultado.get("id")}'
        )

        # Limpa os dados da anotação
        for key in ['id_endereco_anotacao', 'texto_anotacao']:
            context.user_data.pop(key, None)
    except Exception as e:
        logger.error(f'Erro ao criar anotação: {str(e)}')
        await query.message.reply_text(
            '😞 Ocorreu um erro ao enviar sua anotação. Por favor,'
            ' tente novamente mais tarde.'
        )

    return ConversationHandler.END


async def cancelar_anotacao(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Cancela o processo de anotação via comando /cancelar ou callback.
    """
    query = update.callback_query
    if query:
        await query.answer()
        await query.message.reply_text('❌ Processo de anotação cancelado.')
    elif update.message:  # Se foi um comando /cancelar
        await update.message.reply_text('❌ Processo de anotação cancelado.')
    else:
        logger.warning("cancelar_anotacao chamado sem query ou message")
        chat_id = context.user_data.get('chat_id') or \
                  (update.effective_chat and update.effective_chat.id)
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
            "Não foi possível obter effective_user"
            " no handler listar_anotacoes_command.")
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
            user_id=user_id_telegram
        )
        if not anotacoes:
            if id_endereco_arg:
                mensagem_sem_anotacoes = (
                    f'Você não possui anotações para o endereço com ID '
                    f'{escape_markdown(str(id_endereco_arg))}\\.'
                )
                await update.message.reply_text(
                    mensagem_sem_anotacoes,
                    parse_mode=ParseMode.MARKDOWN_V2
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
                filtros=filtros, id_endereco=anotacao_obj.id_endereco,
                 user_id=user_id_telegram
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
            '😞 Ocorreu um erro ao listar as anotações. Por favor,'
            ' tente novamente mais tarde.'
        )


def get_anotacao_conversation() -> ConversationHandler:
    """
    Retorna o conversation handler configurado para anotações.
    """
    return ConversationHandler(
        entry_points=[CommandHandler('anotar', anotar_command)],
        states={
            ID_ENDERECO: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, receber_id_endereco
                ),
                CallbackQueryHandler(
                    anotar_command, pattern='^tentar_outro_codigo_anotacao$'
                ),  # Para o botão "Tentar outro código"
                CallbackQueryHandler(
                    cancelar_anotacao,
                    pattern='^cancelar_nova_anotacao_direto$'
                ),  # Para o botão "Cancelar" no teclado de não encontrado
            ],
            TEXTO: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, receber_texto_anotacao
                ),
                CallbackQueryHandler(
                    cancelar_anotacao, pattern='^cancelar_processo_anotacao$'
                ),  # Para o botão "Cancelar" simples
            ],
            CONFIRMAR: [
                CallbackQueryHandler(
                    finalizar_anotacao, pattern='^confirma_anotacao_sim$'
                ),
                CallbackQueryHandler(
                    cancelar_anotacao, pattern='^confirma_anotacao_nao$'
                ),
            ],
        },
        fallbacks=[
            CommandHandler('cancelar', cancelar_anotacao),
            CallbackQueryHandler(
                cancelar_anotacao, pattern='^cancelar_.*$'
            ),  # Genérico para outros cancelamentos
        ],
        per_message=False,  # Alterado de True para False
    )
