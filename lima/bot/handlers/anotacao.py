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
from ..keyboards import criar_teclado_confirma_cancelar
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
    # Salva para uso posterior na conversa

    # Se o ID já foi informado no comando
    if context.args and context.args[0].isdigit():
        id_endereco = int(context.args[0])
        context.user_data['id_endereco_anotacao'] = id_endereco

        # Busca o endereço para confirmar
        try:
            # Atualizado para usar FiltrosEndereco
            filtros = FiltrosEndereco(limite=1)
            # Apenas para buscar por ID, limite não é estritamente necessário
            #  aqui mas mantido para consistência
            endereco = await buscar_endereco(
                filtros=filtros, id_endereco=id_endereco,
                  user_id=user_id_telegram
            )

            if not endereco or len(endereco) == 0:
                await update.message.reply_text(
                    '⚠️ Endereço não encontrado. Por favor,'
                    ' verifique o ID e tente novamente:'
                )
                return ID_ENDERECO

            # Mostra os dados do endereço
            endereco = endereco[0]

            await update.message.reply_text(
                f'📝 *Adicionar Anotação*\n\n'
                f'Endereço selecionado:\n{formatar_endereco(endereco)}\n\n'
                f'Por favor, digite o texto da sua anotação:',
                parse_mode=ParseMode.MARKDOWN_V2,
            )

            return TEXTO
        except Exception as e:
            logger.error(f'Erro ao buscar endereço para anotação: {str(e)}')
            await update.message.reply_text(
                '😞 Ocorreu um erro ao buscar os dados do endereço. Por favor,'
                ' tente novamente mais tarde.'
            )
            return ConversationHandler.END

    # Se não, solicita o ID
    await update.message.reply_text(
        '📝 *Adicionar Anotação*\n\n'
        'Por favor, informe o ID do endereço que deseja anotar:',
        parse_mode=ParseMode.MARKDOWN_V2,
    )

    return ID_ENDERECO


async def receber_id_endereco(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Recebe o ID do endereço para adicionar uma anotação.
    """
    texto = update.message.text.strip()

    if not update.effective_user:
        logger.error(
            "Não foi possível obter effective_user"
            " no handler receber_id_endereco.")
        await update.message.reply_text(
            '😞 Ocorreu um erro ao processar sua identidade. '
            'Por favor, tente novamente mais tarde.'
        )
        return ID_ENDERECO
    # Ou ConversationHandler.END dependendo do fluxo desejado
    user_id_telegram = update.effective_user.id
    context.user_data['user_id_telegram'] = user_id_telegram
    # Garante que está salvo

    if not texto.isdigit():
        await update.message.reply_text(
            '⚠️ Por favor, digite apenas o número do ID do endereço:'
        )
        return ID_ENDERECO

    id_endereco = int(texto)
    context.user_data['id_endereco_anotacao'] = id_endereco

    # Busca o endereço para confirmar
    try:
        # Atualizado para usar FiltrosEndereco
        filtros = FiltrosEndereco(limite=1)
        endereco = await buscar_endereco(
            filtros=filtros, id_endereco=id_endereco, user_id=user_id_telegram
        )

        if not endereco or len(endereco) == 0:
            await update.message.reply_text(
                '⚠️ Endereço não encontrado. Por favor,'
                ' verifique o ID e tente novamente:'
            )
            return ID_ENDERECO

        # Mostra os dados do endereço
        endereco = endereco[0]

        await update.message.reply_text(
            f'📝 *Adicionar Anotação*\n\n'
            f'Endereço selecionado:\n{formatar_endereco(endereco)}\n\n'
            f'Por favor, digite o texto da sua anotação:',
            parse_mode=ParseMode.MARKDOWN_V2,
        )

        return TEXTO
    except Exception as e:
        logger.error(f'Erro ao buscar endereço para anotação: {str(e)}')
        await update.message.reply_text(
            '😞 Ocorreu um erro ao buscar os dados do endereço.'
            ' Por favor, tente novamente mais tarde.'
        )
        return ConversationHandler.END


async def receber_texto_anotacao(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Recebe o texto da anotação.
    """
    # Armazena o texto
    context.user_data['texto_anotacao'] = update.message.text

    # Prepara mensagem de confirmação
    mensagem = (
        f'📋 *Confirmação de Anotação*\n\n'
        f'ID do Endereço: *{
            escape_markdown(str(context.user_data["id_endereco_anotacao"]))
        }*\n\n'
        f'Texto da Anotação:\n{
            escape_markdown(context.user_data["texto_anotacao"])
        }\n\n'
        'Confirma o envio desta anotação?'
    )

    await update.message.reply_text(
        mensagem,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=criar_teclado_confirma_cancelar('confirma_anotacao'),
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
    Cancela o processo de anotação.
    """
    user = update.effective_user

    # Limpa os dados da anotação
    for key in ['id_endereco_anotacao', 'texto_anotacao']:
        context.user_data.pop(key, None)

    await update.message.reply_text(
        f'❌ Anotação cancelada. Até mais, {user.first_name}!'
    )

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
    # Imports movidos para o topo do arquivo
    # from telegram.ext import (
    #     CallbackQueryHandler,
    #     CommandHandler,
    #     MessageHandler,
    #     filters,
    # )

    return ConversationHandler(
        entry_points=[CommandHandler('anotar', anotar_command)],
        states={
            ID_ENDERECO: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, receber_id_endereco
                )
            ],
            TEXTO: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, receber_texto_anotacao
                )
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
        fallbacks=[CommandHandler('cancelar', cancelar_anotacao)],
        # Adicionado para suprimir o aviso e melhor semântica
        per_message=True,
    )
