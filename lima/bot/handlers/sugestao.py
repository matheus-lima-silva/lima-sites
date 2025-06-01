# pylint: disable=line-too-long, too-many-lines, invalid-name
# flake8: noqa: E501
# pycodestyle: noqa: E501
"""Handlers para comandos de sugestão."""

import logging
import re

from telegram import (
    CallbackQuery,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from lima.database import get_async_session  # Adicionado

from ..formatters.base import escape_markdown
from ..keyboards import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    criar_teclado_confirma_cancelar,
    criar_teclado_selecionar_tipo_sugestao_geral,
    criar_teclado_selecionar_tipo_sugestao_para_endereco,
)
from ..services.endereco import buscar_endereco_por_codigo
from ..services.sugestao import criar_sugestao
from ..services.usuario import obter_ou_criar_usuario
from .endereco_visualizacao import exibir_endereco_completo

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

    try:
        async with get_async_session() as session:  # Corrigido
            db_user, access_token = await obter_ou_criar_usuario(
                session=session,  # Passa a sessão
                telegram_user_id=user.id,
                nome=user.full_name,
                telefone=f'telegram_{user.id}',  # Corrigido para telefone
            )

        if db_user:  # Checa se db_user não é None
            context.user_data['usuario_id'] = db_user.id
            context.user_data['user_id_telegram'] = db_user.telegram_user_id
            context.user_data['access_token'] = (
                access_token  # Armazena o token
            )
            logger.info(
                'Usuário para sugestão autenticado: ID Interno %s, Telegram ID %s',
                context.user_data['usuario_id'],
                user.id,
            )
            return True

        # Se db_user for None, houve um problema
        logger.error(
            f'Falha na autenticação para sugestão (usuário {user.id}): obter_ou_criar_usuario retornou None para db_user.'
        )
        msg_erro = (
            '😞 Falha na autenticação. Não foi possível obter ou criar seu usuário no sistema.\\.'
            'Tente /start e depois a sugestão novamente\\.'
        )
        await _responder_erro_autenticacao(update, msg_erro, is_callback)
        return False

    except Exception as e:  # pylint: disable=broad-except
        logger.exception(
            f'Exceção durante autenticação para sugestão (usuário {user.id}): {e}'
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

    try:
        await query.edit_message_text(
            text=mensagem,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=criar_teclado_selecionar_tipo_sugestao_para_endereco(
                id_endereco
            ),
        )
        logger.info('[sugerir_callback_conversation] Mensagem editada com sucesso.')
    except Exception as e:
        logger.warning(f'[sugerir_callback_conversation] Não foi possível editar mensagem: {e}')
        try:
            # Se editar falhar, tentar responder à mensagem original do callback
            if query.message:
                await query.message.reply_text(
                    text=mensagem,
                    parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=criar_teclado_selecionar_tipo_sugestao_para_endereco(
                        id_endereco
                    ),
                )
                logger.info(
                    '[sugerir_callback_conversation] Nova mensagem (reply) enviada com sucesso.'
                )
        except Exception as e2:
            logger.error(
                f'[sugerir_callback_conversation] Falha ao enviar mensagem alternativa: {e2}'
            )

    return ESCOLHENDO_TIPO_SUGESTAO


async def sugestao_endereco_callback_conversation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Inicia a conversa de sugestão a partir de um callback de botão "Sugerir Melhoria"
    da lista de endereços. O ID do endereço está no callback_data
    (sugestao_endereco_id_{id_endereco}).
    """
    query = update.callback_query
    if not query:  # Deve ser um callback
        return ConversationHandler.END

    await query.answer()

    if not await _autenticar_usuario_sugestao(update, context):
        return ConversationHandler.END

    callback_data = query.data
    logger.info('sugestao_endereco_callback_conversation: %s', callback_data)

    match = re.match(r'sugestao_endereco_id_(\d+)', callback_data)
    if not match:
        logger.warning(
            'Callback de sugestão de endereço mal formatado: %s', callback_data
        )
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

    try:
        await query.edit_message_text(
            text=mensagem,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=criar_teclado_selecionar_tipo_sugestao_para_endereco(
                id_endereco
            ),
        )
        logger.info('[sugestao_endereco_callback_conversation] Mensagem editada com sucesso.')
    except Exception as e:
        logger.warning(f'[sugestao_endereco_callback_conversation] Não foi possível editar mensagem: {e}')
        try:
            # Se editar falhar, tentar responder à mensagem original do callback
            if query.message:
                await query.message.reply_text(
                    text=mensagem,
                    parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=criar_teclado_selecionar_tipo_sugestao_para_endereco(
                        id_endereco
                    ),
                )
                logger.info(
                    '[sugestao_endereco_callback_conversation] Nova mensagem (reply) enviada com sucesso.'
                )
        except Exception as e2:
            logger.error(
                f'[sugestao_endereco_callback_conversation] Falha ao enviar mensagem alternativa: {e2}'
            )

    return ESCOLHENDO_TIPO_SUGESTAO


async def _handle_sugest_tipo_adicao(
    query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE
) -> int:
    context.user_data['tipo_sugestao'] = 'adicao'

    # Criar teclado com botão de cancelar
    teclado_cancelar = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                '🚫 Cancelar Sugestão', callback_data='sugest_cancelar_geral'
            )
        ]
    ])

    await query.edit_message_text(
        'Por favor, descreva o endereço que deseja adicionar, \n'
        'incluindo logradouro, número, bairro, cidade, UF e CEP\\:',
        parse_mode=ParseMode.MARKDOWN_V2,  # Mantido para o \n
        reply_markup=teclado_cancelar,
    )
    return COLETANDO_DETALHES_ADICAO


async def _handle_sugest_tipo_modificar_pedir_id(
    query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE
) -> int:
    context.user_data['tipo_sugestao'] = 'modificacao'

    # Criar teclado com botão de cancelar
    teclado_cancelar = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                '🚫 Cancelar Sugestão', callback_data='sugest_cancelar_geral'
            )
        ]
    ])

    await query.edit_message_text(
        'Por favor, informe o ID do sistema do endereço que deseja modificar\\:',
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=teclado_cancelar,
    )
    return PEDINDO_ID_PARA_MODIFICAR


async def _handle_sugest_tipo_remover_pedir_id(
    query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE
) -> int:
    context.user_data['tipo_sugestao'] = 'remocao'

    # Criar teclado com botão de cancelar
    teclado_cancelar = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                '🚫 Cancelar Sugestão', callback_data='sugest_cancelar_geral'
            )
        ]
    ])

    await query.edit_message_text(
        'Por favor, informe o ID do sistema do endereço que deseja remover:',
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=teclado_cancelar,
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

    # Criar teclado com botão de cancelar
    teclado_cancelar = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                '🚫 Cancelar Sugestão', callback_data='sugest_cancelar_geral'
            )
        ]
    ])

    await query.edit_message_text(
        f'Você está modificando o endereço ID {id_endereco_escaped}\\.\n'
        'Por favor, descreva as modificações desejadas:',
        parse_mode=ParseMode.MARKDOWN_V2,  # Mantido para o \n
        reply_markup=teclado_cancelar,
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


async def _process_confirmar_sim(query, context):
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
        context.user_data['detalhe_sugestao'] = detalhes

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
            id_endereco=id_endereco,
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
            return ConversationHandler.END

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
    except Exception:
        logger.exception('Exceção ao chamar criar_sugestao na API')
        msg_erro_api = (
            '😞 Ocorreu um erro inesperado ao enviar sua sugestão\\. '
            'Por favor, tente novamente mais tarde\\.'
        )
        await query.edit_message_text(
            msg_erro_api,
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    return ConversationHandler.END


async def _process_confirmar_nao(query, context):
    """
    Processa o cancelamento da confirmação e retorna ao menu de sugestão.
    Implementa tratamento de erro DRY similar ao sistema de anotações.
    """
    for key in ['tipo_sugestao', 'detalhe_sugestao']:
        context.user_data.pop(key, None)

    id_endereco = context.user_data.get('id_endereco_sugestao')

    if id_endereco:
        id_endereco_escaped = escape_markdown(str(id_endereco))
        mensagem_menu = (
            f'📝 *Sugestão para Endereço ID {id_endereco_escaped}*\n\n'
            'Que tipo de sugestão você deseja fazer\\?'
        )
        teclado = criar_teclado_selecionar_tipo_sugestao_para_endereco(
            id_endereco
        )
    else:
        mensagem_menu = '📝 *Envio de Sugestão*\n\nEscolha uma opção abaixo para continuar:'
        teclado = criar_teclado_selecionar_tipo_sugestao_geral()

    try:
        await query.edit_message_text(
            mensagem_menu,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=teclado,
        )
        logger.info('[_process_confirmar_nao] Mensagem editada com sucesso.')
    except Exception as e:
        logger.warning(f'[_process_confirmar_nao] Não foi possível editar mensagem: {e}')
        try:
            # Se editar falhar, tentar responder à mensagem original do callback
            if query.message:
                await query.message.reply_text(
                    mensagem_menu,
                    parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=teclado,
                )
                logger.info(
                    '[_process_confirmar_nao] Nova mensagem (reply) enviada com sucesso.'
                )
        except Exception as e2:
            logger.error(
                f'[_process_confirmar_nao] Falha ao enviar mensagem alternativa: {e2}'
            )

    return ESCOLHENDO_TIPO_SUGESTAO


async def callback_confirmando_sugestao(
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

    result = None
    if callback_data == 'sugest_confirmar_sim':
        result = await _process_confirmar_sim(query, context)
    elif callback_data == 'sugest_confirmar_nao':
        result = await _process_confirmar_nao(query, context)
    else:
        result = ConversationHandler.END

    # Limpar dados da sugestão após o processamento, exceto se retornou ESCOLHENDO_TIPO_SUGESTAO
    if result != ESCOLHENDO_TIPO_SUGESTAO:
        for key in [
            'tipo_sugestao',
            'detalhe_sugestao',
            'id_endereco_sugestao',
        ]:
            context.user_data.pop(key, None)
    return result


async def _tentar_voltar_endereco(update, context, id_endereco):
    """
    Tenta voltar para a visualização do endereço.
    Retorna True se conseguiu, False caso contrário.
    """
    usuario_id = context.user_data.get('usuario_id')
    user_id_telegram = context.user_data.get('user_id_telegram')

    if not usuario_id or not user_id_telegram:
        return False

    try:
        endereco_data = await buscar_endereco_por_codigo(
            codigo=str(id_endereco),
            tipo_codigo='id_sistema',
            usuario_id=usuario_id,
            user_id_telegram=user_id_telegram,
        )

        if endereco_data and len(endereco_data) > 0:
            endereco = endereco_data[0]

            # Deletar mensagem atual se for callback
            if update.callback_query:
                try:
                    await update.callback_query.delete_message()
                    logger.info('[_tentar_voltar_endereco] Mensagem deletada com sucesso.')
                except Exception as e:
                    logger.info(f'[_tentar_voltar_endereco] Não foi possível deletar mensagem: {e}')

            # Exibir endereço completo
            await exibir_endereco_completo(update, context, endereco)
            logger.info(f'[_tentar_voltar_endereco] Retornando à visualização do endereço ID {id_endereco}.')
            return True

    except Exception as e:
        logger.error(f'[_tentar_voltar_endereco] Erro ao buscar endereço {id_endereco}: {e}')

    return False


async def _enviar_menu_sugestao(update, context, id_endereco, is_callback):
    """
    Envia o menu de sugestão apropriado.
    """
    if id_endereco:
        id_endereco_escaped = escape_markdown(str(id_endereco))
        mensagem_menu = (
            f'📝 *Sugestão para Endereço ID {id_endereco_escaped}*\n\n'
            'Que tipo de sugestão você deseja fazer\\?'
        )
        teclado = criar_teclado_selecionar_tipo_sugestao_para_endereco(id_endereco)
    else:
        mensagem_menu = '📝 *Envio de Sugestão*\n\nEscolha uma opção abaixo para continuar:'
        teclado = criar_teclado_selecionar_tipo_sugestao_geral()

    if is_callback and update.callback_query:
        query = update.callback_query
        await query.answer()
        try:
            await query.edit_message_text(
                text=mensagem_menu,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=teclado,
            )
            logger.info('[_enviar_menu_sugestao] Mensagem editada com sucesso.')
        except Exception as e:
            logger.warning(f'[_enviar_menu_sugestao] Não foi possível editar mensagem: {e}')
            try:
                if query.message:
                    await query.message.reply_text(
                        text=mensagem_menu,
                        parse_mode=ParseMode.MARKDOWN_V2,
                        reply_markup=teclado,
                    )
                    logger.info('[_enviar_menu_sugestao] Nova mensagem (reply) enviada com sucesso.')
            except Exception as e2:
                logger.error(f'[_enviar_menu_sugestao] Falha ao enviar mensagem alternativa: {e2}')
    elif update.message:
        await update.message.reply_text(
            text=mensagem_menu,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=teclado,
        )


async def cancelar_sugestao_geral(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    is_callback: bool = False,
) -> int:
    """
    Handler genérico para cancelar a sugestão (comando /cancelar ou botão
    de cancelamento). Retorna à visualização do endereço se veio de lá,
    senão retorna ao menu inicial de sugestão.
    """
    # Limpar dados da sugestão atual
    for key in ['tipo_sugestao', 'detalhe_sugestao']:
        context.user_data.pop(key, None)

    # Verificar se tem ID do endereço
    id_endereco = context.user_data.get('id_endereco_sugestao')

    # Se tem ID do endereço, tentar voltar para a visualização
    if id_endereco:
        if await _tentar_voltar_endereco(update, context, id_endereco):
            # Limpar o id_endereco_sugestao já que voltamos à visualização
            context.user_data.pop('id_endereco_sugestao', None)
            return ConversationHandler.END

    # Fluxo padrão: retornar ao menu de sugestão
    await _enviar_menu_sugestao(update, context, id_endereco, is_callback or bool(update.callback_query))

    # Retorna ao estado inicial de escolha do tipo de sugestão
    return ESCOLHENDO_TIPO_SUGESTAO


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
            CallbackQueryHandler(
                sugestao_endereco_callback_conversation,
                pattern=r'^sugestao_endereco_id_\d+$',
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
                ),
                CallbackQueryHandler(
                    cancelar_sugestao_geral, pattern='^sugest_cancelar_geral$'
                ),
            ],
            PEDINDO_ID_PARA_REMOVER: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receber_id_para_modificar_ou_remover,
                ),
                CallbackQueryHandler(
                    cancelar_sugestao_geral, pattern='^sugest_cancelar_geral$'
                ),
            ],
            COLETANDO_DETALHES_ADICAO: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, receber_detalhes_sugestao
                ),
                CallbackQueryHandler(
                    cancelar_sugestao_geral, pattern='^sugest_cancelar_geral$'
                ),
            ],
            COLETANDO_DETALHES_MODIFICACAO: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, receber_detalhes_sugestao
                ),
                CallbackQueryHandler(
                    cancelar_sugestao_geral, pattern='^sugest_cancelar_geral$'
                ),
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
        per_message=False,  # False é correto para ConversationHandlers com MessageHandler
        allow_reentry=True,
    )
