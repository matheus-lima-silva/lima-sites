"""
Handlers para comandos de sugestão.
"""

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from ..formatters import escape_markdown, formatar_endereco
from ..keyboards import criar_teclado_confirma_cancelar
from ..services.endereco import (
    FiltrosEndereco,
    buscar_endereco,
)
from ..services.sugestao import criar_sugestao

logger = logging.getLogger(__name__)

# Estados para a conversa de sugestão
TIPO, DETALHES, ID_ENDERECO, CONFIRMAR = range(4)


async def sugerir_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Handler para o comando /sugerir.
    Inicia o fluxo de conversa para criar uma sugestão.
    """
    if update.effective_user:
        user_id_telegram = update.effective_user.id
        context.user_data['usuario_id'] = user_id_telegram
        context.user_data['user_id_telegram'] = user_id_telegram
    else:
        await update.message.reply_text(
            'Não foi possível identificar o usuário. Tente novamente.'
        )
        return ConversationHandler.END

    await update.message.reply_text(
        '📝 *Envio de Sugestão*\\n\\n'
        'Você pode fazer sugestões para:\\n'
        '1\\\\. Adicionar um novo endereço\\n'
        '2\\\\. Modificar um endereço existente\\n'
        '3\\\\. Remover um endereço incorreto\\n\\n'
        'Por favor, digite o número da opção desejada \\\\(1, 2 ou 3\\\\):',
        parse_mode=ParseMode.MARKDOWN_V2,
    )

    return TIPO


async def receber_tipo_sugestao(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Recebe o tipo de sugestão escolhido pelo usuário.
    """
    texto = update.message.text.strip()
    tipos = {'1': 'adicao', '2': 'modificacao', '3': 'remocao'}

    if texto not in tipos:
        await update.message.reply_text(
            '⚠️ Opção inválida. Por favor, digite 1, 2 ou 3:'
        )
        return TIPO

    tipo = tipos[texto]
    context.user_data['tipo_sugestao'] = tipo

    if tipo == 'adicao':
        await update.message.reply_text(
            'Por favor, descreva o endereço que deseja adicionar, '
            'incluindo logradouro, número, bairro, cidade, UF e CEP:'
        )
        return DETALHES
    elif tipo == 'modificacao':
        await update.message.reply_text(
            'Por favor, informe o ID do endereço que deseja modificar:'
        )
        return ID_ENDERECO
    elif tipo == 'remocao':
        await update.message.reply_text(
            'Por favor, informe o ID do endereço que deseja remover:'
        )
        return ID_ENDERECO
    return TIPO  # Retorno padrão


async def receber_id_endereco(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Recebe o ID do endereço para modificação ou remoção.
    """
    texto = update.message.text.strip()
    user_id_telegram = None
    if update.effective_user:
        user_id_telegram = update.effective_user.id
        context.user_data['user_id_telegram'] = user_id_telegram
    else:
        await update.message.reply_text(
            'Não foi possível identificar o'
            ' usuário para autenticação. Tente novamente.'
        )
        return ConversationHandler.END

    if not texto.isdigit():
        await update.message.reply_text(
            '⚠️ Por favor, digite apenas o número do ID do endereço:'
        )
        return ID_ENDERECO

    id_endereco = int(texto)
    context.user_data['id_endereco_sugestao'] = id_endereco

    try:
        filtros = FiltrosEndereco(limite=1)
        endereco_lista = await buscar_endereco(
            filtros=filtros,
            id_endereco=id_endereco,
            user_id=user_id_telegram
        )

        if not endereco_lista:
            await update.message.reply_text(
                '⚠️ Endereço não encontrado. '
                'Por favor, verifique o ID e tente novamente:'
            )
            return ID_ENDERECO

        endereco = endereco_lista[0]
        endereco_formatado = formatar_endereco(endereco)
        tipo_sugestao = context.user_data['tipo_sugestao']

        if tipo_sugestao == 'modificacao':
            acao_texto = 'modificar'
            prompt_texto = (
                'Por favor, descreva as alterações que deseja propor:'
            )
        else:  # remocao
            acao_texto = 'remover'
            prompt_texto = 'Por favor, explique o motivo da remoção:'

        mensagem = (
            f'Você escolheu {acao_texto} o endereço: \\n'
            f'{endereco_formatado}\\n\\n'
            f'{prompt_texto}'
        )

        await update.message.reply_text(
            mensagem,
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return DETALHES
    except Exception as e:
        logger.error(f'Erro ao buscar endereço para sugestão: {str(e)}')
        await update.message.reply_text(
            '😞 Ocorreu um erro ao buscar os dados do endereço. '
            'Por favor, tente novamente mais tarde.'
        )
        return ConversationHandler.END


async def receber_detalhes_sugestao(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Recebe os detalhes da sugestão.
    """
    context.user_data['detalhe_sugestao'] = update.message.text
    tipo_sugestao = context.user_data['tipo_sugestao']
    tipo_texto_map = {
        'adicao': 'adicionar',
        'modificacao': 'modificar',
        'remocao': 'remover',
    }
    tipo_sugestao_str = tipo_texto_map.get(tipo_sugestao, tipo_sugestao)

    mensagem_confirmacao = (
        f'📋 *Confirmação de Sugestão*\n\n'
        f'Tipo: *{escape_markdown(tipo_sugestao_str)}*\n'
    )
    if tipo_sugestao != 'adicao':
        id_endereco_sug = context.user_data.get('id_endereco_sugestao')
        mensagem_confirmacao += (
            f'ID do Endereço: *{escape_markdown(str(id_endereco_sug))}*\n'
        )
    detalhe_sugestao_escaped = escape_markdown(
        context.user_data["detalhe_sugestao"]
    )
    mensagem_confirmacao += (
        f'Detalhes: {detalhe_sugestao_escaped}\n\n'
        'Confirma o envio desta sugestão?'
    )
    await update.message.reply_text(
        mensagem_confirmacao,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=criar_teclado_confirma_cancelar('confirma_sugestao'),
    )
    return CONFIRMAR


async def finalizar_sugestao(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Finaliza o processo de sugestão, enviando-a para a API.
    """
    query = update.callback_query
    await query.answer()

    if query.data != 'confirma_sugestao_sim':
        await query.message.reply_text('❌ Sugestão cancelada.')
        return ConversationHandler.END

    tipo = context.user_data.get('tipo_sugestao')
    detalhes = context.user_data.get('detalhe_sugestao')
    id_endereco = context.user_data.get('id_endereco_sugestao')
    user_id_telegram = context.user_data.get('user_id_telegram')

    # Corrigido: "ou" para "or"
    if not tipo or not detalhes or not user_id_telegram:
        await query.message.reply_text(
            '❌ Dados incompletos para enviar a sugestão. Por favor,'
            ' tente novamente.'
        )
        return ConversationHandler.END

    try:
        resultado = await criar_sugestao(
            id_usuario_telegram=user_id_telegram,
            tipo=tipo,
            detalhes=detalhes,
            id_endereco=id_endereco,
            user_id=user_id_telegram
        )
        await query.message.reply_text(
            f'✅ Sugestão enviada com sucesso! ID: {resultado.get("id")}'
        )
        for key in [
            'tipo_sugestao',
            'detalhe_sugestao',
            'id_endereco_sugestao',
        ]:
            context.user_data.pop(key, None)
    except Exception as e:
        logger.error(f'Erro ao criar sugestão: {str(e)}')
        await query.message.reply_text(
            '😞 Ocorreu um erro ao enviar sua sugestão. Por favor,'
            ' tente novamente mais tarde.'
        )
    return ConversationHandler.END


async def cancelar_sugestao(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Cancela o processo de sugestão.
    """
    user = update.effective_user
    for key in [
        'tipo_sugestao',
        'detalhe_sugestao',
        'id_endereco_sugestao',
    ]:
        context.user_data.pop(key, None)

    nome_usuario = user.first_name if user else ""
    await update.message.reply_text(
        f'❌ Sugestão cancelada. Até mais, {escape_markdown(nome_usuario)}!',
        parse_mode=ParseMode.MARKDOWN_V2
    )
    return ConversationHandler.END


def get_sugestao_conversation() -> ConversationHandler:
    """
    Retorna o conversation handler configurado para sugestões.
    """
    return ConversationHandler(
        entry_points=[CommandHandler('sugerir', sugerir_command)],
        states={
            TIPO: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, receber_tipo_sugestao
                )
            ],
            ID_ENDERECO: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, receber_id_endereco
                )
            ],
            DETALHES: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, receber_detalhes_sugestao
                )
            ],
            CONFIRMAR: [
                CallbackQueryHandler(
                    finalizar_sugestao, pattern='^confirma_sugestao_sim$'
                ),
                CallbackQueryHandler(
                    cancelar_sugestao, pattern='^confirma_sugestao_nao$'
                ),
            ],
        },
        fallbacks=[CommandHandler('cancelar', cancelar_sugestao)],
        per_message=True,
    )
