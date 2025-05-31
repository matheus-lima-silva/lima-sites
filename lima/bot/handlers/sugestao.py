# pylint: disable=line-too-long, too-many-lines, invalid-name
# flake8: noqa: E501
# pycodestyle: noqa: E501
"""Handlers para comandos de sugestão."""

import logging
import re

from telegram import CallbackQuery, Update
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
from ..keyboards import (
    criar_teclado_confirma_cancelar,
    criar_teclado_selecionar_tipo_sugestao_geral,
    criar_teclado_selecionar_tipo_sugestao_para_endereco,
)
from ..services.sugestao import criar_sugestao
from ..services.usuario import obter_ou_criar_usuario

logger = logging.getLogger(__name__)

# Novos estados para a conversa de sugestão baseada em teclado
(
    ESCOLHENDO_TIPO_SUGESTAO,
    PEDINDO_ID_PARA_MODIFICAR,
    PEDINDO_ID_PARA_REMOVER,
    COLETANDO_DETALHES_ADICAO,
    COLETANDO_DETALHES_MODIFICACAO,
    CONFIRMANDO_SUGESTAO,
) = range(6)


async def _responder_erro_autenticacao(
    update: Update, mensagem: str, is_callback: bool
):
    """Envia uma mensagem de erro de autenticação."""
    if is_callback and update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                mensagem, parse_mode=ParseMode.MARKDOWN_V2
            )
        except Exception:
            logger.warning(
                'Falha ao editar mensagem de erro de autenticação no callback.',
                exc_info=True,
            )
            # Se editar falhar, tenta enviar uma nova mensagem se possível
            if update.effective_chat:
                await update.effective_chat.send_message(
                    mensagem, parse_mode=ParseMode.MARKDOWN_V2
                )
    elif update.message:
        await update.message.reply_text(
            mensagem, parse_mode=ParseMode.MARKDOWN_V2
        )
    elif update.effective_chat:  # Fallback para outros tipos de update
        await update.effective_chat.send_message(
            mensagem, parse_mode=ParseMode.MARKDOWN_V2
        )


async def _autenticar_usuario_sugestao(  # pylint: disable=too-many-return-statements
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """Garante que o usuário está autenticado e armazena IDs no contexto."""
    user = update.effective_user
    is_callback = update.callback_query is not None

    if not user:
        await _responder_erro_autenticacao(
            update,
            'Não foi possível identificar o usuário\\. Tente novamente\\.',
            is_callback,
        )
        return False

    if context.user_data.get('usuario_id'):
        if 'user_id_telegram' not in context.user_data:
            context.user_data['user_id_telegram'] = user.id
        return True

    try:
        dados_usuario_api = await obter_ou_criar_usuario(
            telegram_user_id=user.id,
            nome=user.full_name,
            telefone_id_interno=f'telegram_{user.id}',
        )
        if dados_usuario_api and 'id' in dados_usuario_api:
            context.user_data['usuario_id'] = dados_usuario_api['id']
            context.user_data['user_id_telegram'] = dados_usuario_api.get(
                'telegram_user_id', user.id
            )
            logger.info(
                'Usuário para sugestão autenticado: ID Interno %s, Telegram ID %s',
                context.user_data['usuario_id'],
                user.id,
            )
            return True

        error_detail = 'API não respondeu'  # Default error
        if dados_usuario_api and 'error' in dados_usuario_api:
            error_detail = dados_usuario_api.get(
                'detail', 'Erro desconhecido na autenticação'
            )
        elif (
            dados_usuario_api and 'detail' in dados_usuario_api
        ):  # Outro formato de erro?
            error_detail = dados_usuario_api['detail']

        logger.error(
            'Falha na autenticação para sugestão (usuário %s): %s',
            user.id,
            error_detail,
        )
        msg_erro = (
            f'😞 Falha na autenticação: {escape_markdown(error_detail)}\\. '
            'Tente /start e depois a sugestão novamente\\.'
        )
        await _responder_erro_autenticacao(update, msg_erro, is_callback)
        return False

    except Exception:  # pylint: disable=broad-except
        logger.exception(
            'Exceção durante autenticação para sugestão (usuário %s)', user.id
        )
        msg_erro_exc = (
            '😞 Ocorreu um erro inesperado durante a autenticação\\. '
            'Tente novamente mais tarde\\.'
        )
        await _responder_erro_autenticacao(update, msg_erro_exc, is_callback)
        return False


async def sugerir_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Handler para o comando /sugerir. Inicia o fluxo de conversa para criar
    uma sugestão, mostrando o teclado de tipos.
    """
    if not update.message:  # Comando deve vir de uma mensagem
        return ConversationHandler.END

    if not await _autenticar_usuario_sugestao(update, context):
        return ConversationHandler.END

    await update.message.reply_text(
        '📝 *Envio de Sugestão*\n\nEscolha uma opção abaixo para continuar:',
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=criar_teclado_selecionar_tipo_sugestao_geral(),
    )
    return ESCOLHENDO_TIPO_SUGESTAO


async def sugerir_callback_conversation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Inicia a conversa de sugestão a partir de um callback de botão
    (ex: "Sugerir Melhoria"). O ID do endereço já está no callback_data
    (sugerir_{id_endereco}).
    """
    query = update.callback_query
    if not query:  # Deve ser um callback
        return ConversationHandler.END

    await query.answer()

    if not await _autenticar_usuario_sugestao(update, context):
        return ConversationHandler.END

    callback_data = query.data
    logger.info('sugerir_callback_conversation: %s', callback_data)

    match = re.match(r'sugerir_(\d+)', callback_data)
    if not match:
        logger.warning('Callback de sugestão mal formatado: %s', callback_data)
        await query.edit_message_text(
            'Erro ao processar o ID do endereço para sugestão\\.',
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return ConversationHandler.END

    id_endereco = int(match.group(1))
    context.user_data['id_endereco_sugestao'] = id_endereco
    id_endereco_escaped = escape_markdown(str(id_endereco))

    mensagem = (
        f'📝 *Sugestão para Endereço ID {id_endereco_escaped}*\n\n'
        'Que tipo de sugestão você deseja fazer\\?'
    )
    await query.edit_message_text(
        text=mensagem,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=criar_teclado_selecionar_tipo_sugestao_para_endereco(
            id_endereco
        ),
    )
    return ESCOLHENDO_TIPO_SUGESTAO


async def _handle_sugest_tipo_adicao(
    query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE
) -> int:
    context.user_data['tipo_sugestao'] = 'adicao'
    await query.edit_message_text(
        'Por favor, descreva o endereço que deseja adicionar, \n'
        'incluindo logradouro, número, bairro, cidade, UF e CEP\\:',
        parse_mode=ParseMode.MARKDOWN_V2,  # Mantido para o \n
    )
    return COLETANDO_DETALHES_ADICAO


async def _handle_sugest_tipo_modificar_pedir_id(
    query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE
) -> int:
    context.user_data['tipo_sugestao'] = 'modificacao'
    await query.edit_message_text(
        'Por favor, informe o ID do sistema do endereço que deseja modificar\\:'
    )
    return PEDINDO_ID_PARA_MODIFICAR


async def _handle_sugest_tipo_remover_pedir_id(
    query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE
) -> int:
    context.user_data['tipo_sugestao'] = 'remocao'
    await query.edit_message_text(
        'Por favor, informe o ID do sistema do endereço que deseja remover:'
    )
    return PEDINDO_ID_PARA_REMOVER


async def _handle_sugest_tipo_modificar_com_id_atual(
    query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE
) -> int:
    context.user_data['tipo_sugestao'] = 'modificacao'
    id_endereco = context.user_data.get('id_endereco_sugestao')
    if not id_endereco:
        await query.edit_message_text(
            'ID do endereço não encontrado\\. Tente novamente\\.'
        )
        return ConversationHandler.END
    id_endereco_escaped = escape_markdown(str(id_endereco))
    await query.edit_message_text(
        f'Você está modificando o endereço ID {id_endereco_escaped}\\.\n'
        'Por favor, descreva as modificações desejadas:',
        parse_mode=ParseMode.MARKDOWN_V2,  # Mantido para o \n
    )
    return COLETANDO_DETALHES_MODIFICACAO


async def _handle_sugest_tipo_remover_com_id_atual(
    query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE
) -> int:
    context.user_data['tipo_sugestao'] = 'remocao'
    id_endereco = context.user_data.get('id_endereco_sugestao')
    if not id_endereco:
        await query.edit_message_text(
            'ID do endereço não encontrado\\. Tente novamente\\.'
        )
        return ConversationHandler.END

    id_endereco_escaped = escape_markdown(str(id_endereco))
    # Detalhe é preenchido automaticamente para este fluxo de remoção
    context.user_data['detalhe_sugestao'] = (
        f'Remoção do endereço ID {id_endereco}'
    )

    mensagem_confirmacao = (
        f'📋 *Confirmação de Sugestão*\n\n'
        f'Tipo: *Remover Endereço*\n'
        f'ID do Endereço: *{id_endereco_escaped}*\n\n'
        'Confirma o envio desta sugestão de remoção\\?'
    )
    await query.edit_message_text(
        mensagem_confirmacao,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=criar_teclado_confirma_cancelar('sugest_confirmar'),
    )
    return CONFIRMANDO_SUGESTAO


async def callback_escolhendo_tipo_sugestao(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Processa a escolha do tipo de sugestão feita pelo usuário via
    teclado inline.
    """
    query = update.callback_query
    if not query:
        return ConversationHandler.END

    await query.answer()
    callback_data = query.data
    logger.info('Callback tipo sugestão: %s', callback_data)

    if not context.user_data.get(
        'usuario_id'
    ) and not await _autenticar_usuario_sugestao(update, context):
        return ConversationHandler.END

    handlers = {
        'sugest_tipo_adicao': _handle_sugest_tipo_adicao,
        'sugest_tipo_modificar_pedir_id': (
            _handle_sugest_tipo_modificar_pedir_id
        ),
        'sugest_tipo_remover_pedir_id': _handle_sugest_tipo_remover_pedir_id,
        'sugest_tipo_modificar_com_id_atual': (
            _handle_sugest_tipo_modificar_com_id_atual
        ),
        'sugest_tipo_remover_com_id_atual': (
            _handle_sugest_tipo_remover_com_id_atual
        ),
    }

    if callback_data in handlers:
        return await handlers[callback_data](query, context)

    if callback_data == 'sugest_cancelar_geral':
        return await cancelar_sugestao_geral(update, context, is_callback=True)

    await query.edit_message_text(
        'Opção inválida\\. Tente novamente\\.',
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    return ESCOLHENDO_TIPO_SUGESTAO


async def receber_id_para_modificar_ou_remover(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Recebe o ID do endereço para modificação ou remoção, quando solicitado
    por texto.
    """
    current_state_fallback = (
        PEDINDO_ID_PARA_MODIFICAR
        if context.user_data.get('tipo_sugestao') == 'modificacao'
        else PEDINDO_ID_PARA_REMOVER
    )
    if not update.message or not update.message.text:
        return current_state_fallback

    texto_id = update.message.text.strip()
    tipo_sugestao = context.user_data.get('tipo_sugestao')

    if not texto_id.isdigit():
        await update.message.reply_text(
            'ID inválido. Por favor, envie um número correspondente ao ID do sistema.'
        )
        return current_state_fallback

    id_endereco = int(texto_id)
    context.user_data['id_endereco_sugestao'] = id_endereco
    id_endereco_escaped = escape_markdown(str(id_endereco))

    if tipo_sugestao == 'modificacao':
        await update.message.reply_text(
            f'Você está modificando o endereço ID {id_endereco_escaped}\\.\n'
            'Por favor, descreva as modificações desejadas:',
            parse_mode=ParseMode.MARKDOWN_V2,  # Mantido para o \n
        )
        return COLETANDO_DETALHES_MODIFICACAO

    if tipo_sugestao == 'remocao':
        context.user_data['detalhe_sugestao'] = (
            f'Remoção do endereço ID {id_endereco}'
        )
        mensagem_confirmacao = (
            f'📋 *Confirmação de Sugestão*\n\n'
            f'Tipo: *Remover Endereço*\n'
            f'ID do Endereço: *{id_endereco_escaped}*\n\n'
            'Confirma o envio desta sugestão de remoção\\?'
        )
        await update.message.reply_text(
            mensagem_confirmacao,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=criar_teclado_confirma_cancelar('sugest_confirmar'),
        )
        return CONFIRMANDO_SUGESTAO

    logger.error(
        'Estado inválido em receber_id_para_modificar_ou_remover: tipo_sugestao=%s',
        tipo_sugestao,
    )
    await update.message.reply_text(
        'Ocorreu um erro interno\\. Por favor, tente /cancelar e comece novamente\\.'
    )
    return ConversationHandler.END


async def receber_detalhes_sugestao(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Recebe os detalhes da sugestão (para adição ou modificação) via mensagem
    de texto.
    """
    current_state_fallback = (
        COLETANDO_DETALHES_ADICAO
        if context.user_data.get('tipo_sugestao') == 'adicao'
        else COLETANDO_DETALHES_MODIFICACAO
    )
    if not update.message or not update.message.text:
        return current_state_fallback

    context.user_data['detalhe_sugestao'] = update.message.text
    tipo_sugestao = context.user_data['tipo_sugestao']
    tipo_texto_map = {
        'adicao': 'Adicionar Novo Endereço',
        'modificacao': 'Modificar Endereço Existente',
    }
    tipo_sugestao_str = tipo_texto_map.get(
        tipo_sugestao, tipo_sugestao.capitalize()
    )

    mensagem_confirmacao = (
        f'📋 *Confirmação de Sugestão*\n\n'
        f'Tipo: *{escape_markdown(tipo_sugestao_str)}*\n'
    )
    if tipo_sugestao == 'modificacao':
        id_endereco = context.user_data.get('id_endereco_sugestao')
        if id_endereco:
            id_endereco_escaped = escape_markdown(str(id_endereco))
            mensagem_confirmacao += (
                f'ID do Endereço: *{id_endereco_escaped}*\n'
            )
        else:
            logger.warning(
                'ID do endereço não encontrado no contexto para modificação em receber_detalhes_sugestao'
            )
            mensagem_confirmacao += 'ID do Endereço: *N/A*\n'

    detalhe_sugestao_escaped = escape_markdown(
        context.user_data['detalhe_sugestao']
    )
    mensagem_confirmacao += (
        f'Detalhes: {detalhe_sugestao_escaped}\n\n'
        'Confirma o envio desta sugestão?'
    )
    await update.message.reply_text(
        mensagem_confirmacao,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=criar_teclado_confirma_cancelar('sugest_confirmar'),
    )
    return CONFIRMANDO_SUGESTAO


async def callback_confirmando_sugestao(  # pylint: disable=too-many-branches, too-many-statements
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Processa a confirmação (Sim/Não) do envio da sugestão a partir de um
    callback.
    """
    query = update.callback_query
    if not query:
        return ConversationHandler.END

    await query.answer()
    callback_data = query.data

    if callback_data == 'sugest_confirmar_sim':
        tipo = context.user_data.get('tipo_sugestao')
        detalhes = context.user_data.get('detalhe_sugestao')
        id_endereco = context.user_data.get('id_endereco_sugestao')
        usuario_id_interno = context.user_data.get('usuario_id')

        if not usuario_id_interno:
            logger.error(
                'ID de usuário interno não encontrado no contexto ao confirmar sugestão.'
            )
            await query.edit_message_text(
                'Falha na autenticação ao enviar sugestão\\. '
                'Tente /start e inicie novamente\\.',
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            return ConversationHandler.END

        if tipo == 'remocao' and not detalhes and id_endereco:
            detalhes = f'Remoção do endereço ID {id_endereco}'
            context.user_data['detalhe_sugestao'] = (
                detalhes  # Salva para consistência
            )

        if not tipo or not detalhes:
            await query.edit_message_text(
                'Dados da sugestão estão incompletos\\. Tente novamente\\.',
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            return ConversationHandler.END

        if tipo in {'modificacao', 'remocao'} and not id_endereco:
            msg_erro_id = (
                f'É necessário um ID de endereço para a sugestão de '
                f'{escape_markdown(tipo)}\\. Tente novamente\\.'
            )
            await query.edit_message_text(
                msg_erro_id,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            return ConversationHandler.END

        try:
            resultado_sugestao = await criar_sugestao(
                id_usuario=usuario_id_interno,
                tipo_sugestao=tipo,
                detalhe=detalhes,
                id_endereco=id_endereco,  # Será None para 'adicao'
            )

            if resultado_sugestao and 'error' in resultado_sugestao:
                error_msg = resultado_sugestao.get(
                    'detail', 'Erro desconhecido ao criar sugestão na API.'
                )
                logger.error('Erro da API ao criar sugestão: %s', error_msg)
                await query.edit_message_text(
                    f'😞 Erro ao enviar sugestão: {escape_markdown(error_msg)}',
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
                return ConversationHandler.END  # Fim após erro da API

            id_sugestao_criada = resultado_sugestao.get('id', 'N/A')
            id_sugestao_escaped = escape_markdown(str(id_sugestao_criada))
            msg_sucesso = (
                f'✅ Sugestão enviada com sucesso! ID da Sugestão: `{id_sugestao_escaped}`\n'
                'Nossa equipe irá analisar e responder em breve.'
            )
            await query.edit_message_text(
                msg_sucesso,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        except Exception:  # pylint: disable=broad-except
            logger.exception('Exceção ao chamar criar_sugestao na API')
            msg_erro_api = (
                '😞 Ocorreu um erro inesperado ao enviar sua sugestão\\. '
                'Por favor, tente novamente mais tarde\\.'
            )
            await query.edit_message_text(
                msg_erro_api,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
    elif callback_data == 'sugest_confirmar_nao':
        await query.edit_message_text(
            'Sugestão cancelada\\.', parse_mode=ParseMode.MARKDOWN_V2
        )

    for key in [
        'tipo_sugestao',
        'detalhe_sugestao',
        'id_endereco_sugestao',
    ]:
        context.user_data.pop(key, None)
    return ConversationHandler.END


async def cancelar_sugestao_geral(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    is_callback: bool = False,
) -> int:
    """
    Handler genérico para cancelar a sugestão (comando /cancelar ou botão
    de cancelamento).
    """
    mensagem_cancelamento = 'Sugestão cancelada\\.'

    if is_callback or update.callback_query:
        query = update.callback_query
        if query:
            await query.answer()
            try:
                await query.edit_message_text(
                    text=mensagem_cancelamento,
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
            except Exception:  # pylint: disable=broad-except
                logger.warning(
                    'Falha ao editar mensagem no cancelamento via callback. Enviando nova mensagem.',
                    exc_info=True,
                )
                chat_id_to_send = None
                if query.message:
                    chat_id_to_send = query.message.chat_id
                elif update.effective_chat:
                    chat_id_to_send = update.effective_chat.id

                if chat_id_to_send:
                    try:
                        await context.bot.send_message(
                            chat_id=chat_id_to_send,
                            text=mensagem_cancelamento,
                            parse_mode=ParseMode.MARKDOWN_V2,
                        )
                    except Exception:
                        logger.exception(
                            'Falha ao enviar nova mensagem de cancelamento.'
                        )

    elif update.message:
        await update.message.reply_text(
            text=mensagem_cancelamento, parse_mode=ParseMode.MARKDOWN_V2
        )

    for key in [
        'tipo_sugestao',
        'detalhe_sugestao',
        'id_endereco_sugestao',
    ]:
        context.user_data.pop(key, None)
    return ConversationHandler.END


def get_sugestao_conversation() -> ConversationHandler:
    """
    Retorna o conversation handler configurado para sugestões, agora usando
    teclados.
    """
    pattern_escolhendo_tipo = (
        r'^sugest_tipo_(adicao|modificar_pedir_id|remover_pedir_id|'
        r'modificar_com_id_atual|remover_com_id_atual)|sugest_cancelar_geral$'
    )

    return ConversationHandler(
        entry_points=[
            CommandHandler('sugerir', sugerir_command),
            CallbackQueryHandler(
                sugerir_callback_conversation, pattern=r'^sugerir_\d+$'
            ),
        ],
        states={
            ESCOLHENDO_TIPO_SUGESTAO: [
                CallbackQueryHandler(
                    callback_escolhendo_tipo_sugestao,
                    pattern=pattern_escolhendo_tipo,
                )
            ],
            PEDINDO_ID_PARA_MODIFICAR: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receber_id_para_modificar_ou_remover,
                )
            ],
            PEDINDO_ID_PARA_REMOVER: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receber_id_para_modificar_ou_remover,
                )
            ],
            COLETANDO_DETALHES_ADICAO: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, receber_detalhes_sugestao
                )
            ],
            COLETANDO_DETALHES_MODIFICACAO: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, receber_detalhes_sugestao
                )
            ],
            CONFIRMANDO_SUGESTAO: [
                CallbackQueryHandler(
                    callback_confirmando_sugestao,
                    pattern=r'^sugest_confirmar_(sim|nao)$',
                )
            ],
        },
        fallbacks=[
            CommandHandler('cancelar', cancelar_sugestao_geral),
            CallbackQueryHandler(
                cancelar_sugestao_geral, pattern='^sugest_cancelar_geral$'
            ),
        ],
        per_message=False,
        allow_reentry=True,
    )
