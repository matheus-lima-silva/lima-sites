"""
Handlers para o fluxo de anotações de endereços no bot Telegram.

Este módulo contém toda a lógica para criação de anotações em endereços,
incluindo:
- Início do fluxo por callback ou comando
- Busca e validação de endereços
- Coleta do texto da anotação
- Confirmação e persistência da anotação

Estados da conversa:
- ID_ENDERECO: Busca do endereço (se necessário)
- TEXTO: Coleta do texto da anotação
- CONFIRMAR: Confirmação final antes de salvar
"""

import logging  # Adicionado para resolver o NameError em logger
from typing import Any, Dict  # Removido Optional

from telegram import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
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

from lima.bot.handlers.menu import exibir_menu_principal
from lima.schemas import AnotacaoRead, EnderecoRead  # Adicionado EnderecoRead

from ..formatters.base import escape_markdown
from ..formatters.endereco import formatar_endereco
from ..keyboards import (
    criar_teclado_confirma_cancelar,
    teclado_endereco_nao_encontrado_criar,
    teclado_simples_cancelar_anotacao,
)
from ..services.anotacao import criar_anotacao, listar_anotacoes
from ..services.endereco import (
    FiltrosEndereco,
    buscar_endereco,
)

# Imports removidos - não vamos mais chamar iniciar_busca_rapida diretamente

logger = logging.getLogger(__name__)

# Estados para a conversa de anotação
ID_ENDERECO, TEXTO, CONFIRMAR = range(3)


async def _verificar_usuario_e_definir_id_telegram(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """
    Verifica se update.effective_user existe e define user_id_telegram
    em user_data. Retorna True se o usuário for válido, False caso contrário.
    Envia uma mensagem de erro se o usuário não for encontrado.
    """
    if not update.effective_user:
        logger.error(
            '[_verificar_usuario_e_definir_id_telegram] effective_user não'
            ' encontrado.'
        )
        mensagem_erro = (
            '😞 Ocorreu um erro ao processar sua identidade. '
            'Por favor, tente novamente mais tarde.'
        )
        query = update.callback_query
        message = update.message or (query and query.message)

        if query:
            try:
                await query.answer()  # Responde ao callback antes de editar
                await query.edit_message_text(text=mensagem_erro)
                return False
            except Exception as e_edit:
                logger.warning(
                    f'[_verificar_usuario_e_definir_id_telegram] Falha ao'
                    f' editar mensagem de callback: {e_edit}'
                )
                # Tenta enviar nova mensagem se a edição falhar
                if query.message:
                    try:
                        await query.message.reply_text(text=mensagem_erro)
                        return False
                    except Exception as e_reply:
                        logger.error(
                            f'[_verificar_usuario_e_definir_id_telegram] Falha'
                            f' ao enviar reply_text: {e_reply}'
                        )
        elif message:
            try:
                await message.reply_text(text=mensagem_erro)
                return False
            except Exception as e_reply_msg:
                logger.error(
                    f'[_verificar_usuario_e_definir_id_telegram] Falha ao'
                    f' enviar reply_text para mensagem: {e_reply_msg}'
                )

        # Fallback se tudo falhar, mas improvável de ser útil sem chat_id
        chat_id = update.effective_chat.id if update.effective_chat else None
        if chat_id:
            try:
                await context.bot.send_message(
                    chat_id=chat_id, text=mensagem_erro
                )
            except Exception as e_send:
                logger.error(
                    f'[_verificar_usuario_e_definir_id_telegram] Falha crítica'
                    f' ao enviar mensagem: {e_send}'
                )
        return False

    context.user_data['user_id_telegram'] = update.effective_user.id
    return True


async def _buscar_endereco_para_anotacao(
    user_id_telegram: int,
    id_endereco: int | None = None,
    codigo_endereco: str | None = None,
) -> list[EnderecoRead]:
    """
    Busca o endereço por ID ou código_endereco.
    Retorna uma lista de EnderecoRead (espera-se no máximo 1 devido ao limite).
    """
    filtros = FiltrosEndereco(limite=1)
    if id_endereco is not None:
        return await buscar_endereco(
            filtros=filtros, id_endereco=id_endereco, user_id=user_id_telegram
        )
    if codigo_endereco is not None:
        return await buscar_endereco(
            filtros=filtros,
            codigo_endereco=codigo_endereco,
            user_id=user_id_telegram,
        )
    logger.warning(
        '[_buscar_endereco_para_anotacao] Nenhum identificador'
        ' (id_endereco ou codigo_endereco) foi fornecido.'
    )
    return []


async def _pedir_texto_anotacao_para_endereco(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    endereco: Dict[str, Any],
):
    """
    Prepara e envia a mensagem solicitando o texto da anotação para um
    endereço específico. Armazena o ID do endereço em user_data.
    """
    if not endereco:
        logger.warning(
            '[_pedir_texto_anotacao_para_endereco] '
            'Tentativa de pedir anotação para endereço nulo.'
        )
        await update.effective_message.reply_text(
            'Não foi possível encontrar o endereço para a anotação.'
        )
        return ConversationHandler.END

    # Armazena o ID do endereço para uso posterior
    context.user_data['id_endereco_anotacao'] = endereco['id']

    # Formata os detalhes do endereço para exibição
    # TODO: Verificar se formatar_endereco_telegram é compatível com 'endereco'
    #       sendo um dict.
    mensagem_texto = (
        f'📝 *Adicionar Anotação*\\n\\n'
        f'Endereço selecionado:\\n{formatar_endereco(endereco)}\\n\\n'
        f'Por favor, digite o texto da sua anotação:'
    )
    reply_markup = teclado_simples_cancelar_anotacao()

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=mensagem_texto,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=reply_markup,
        )
    elif update.message:
        await update.message.reply_text(
            text=mensagem_texto,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=reply_markup,
        )
    else:
        logger.warning(
            '[_pedir_texto_anotacao_para_endereco] Não foi possível determinar'
            ' como responder (nem callback_query nem message).'
        )
        # Tentar enviar para o chat_id se disponível como fallback
        chat_id = context.user_data.get('chat_id') or (
            update.effective_chat and update.effective_chat.id
        )
        if chat_id:
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=mensagem_texto,
                    parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=reply_markup,
                )
            except Exception as e:
                logger.error(
                    f'[_pedir_texto_anotacao_para_endereco] Falha ao enviar'
                    f' mensagem de fallback: {e}'
                )
        return ConversationHandler.END
    return TEXTO


async def iniciar_anotacao_por_id(
    update: Update, context: ContextTypes.DEFAULT_TYPE, endereco_id_str: str
) -> int:
    """
    Inicia o fluxo de anotação com o ID do endereço já conhecido (como string).
    """
    if not await _verificar_usuario_e_definir_id_telegram(update, context):
        return ConversationHandler.END
    user_id_telegram = context.user_data['user_id_telegram']

    # Esta função pode ser chamada por um CallbackQuery ou outro meio.
    # Se for CallbackQuery, é bom responder.
    if update.callback_query:
        await update.callback_query.answer()

    logger.info(
        f'[iniciar_anotacao_por_id] INICIADO com '
        f'endereco_id_str: {endereco_id_str}, user_id: {user_id_telegram}'
    )

    try:
        id_endereco = int(endereco_id_str)
    except ValueError:
        logger.warning(
            f'[iniciar_anotacao_por_id] endereco_id_str inválido: '
            f'{endereco_id_str}. Não é um inteiro.'
        )
        msg_erro = 'ID do endereço fornecido é inválido.'
        if update.callback_query:
            await update.callback_query.edit_message_text(text=msg_erro)
        elif update.message:  # Se chamado por comando com arg não numérico
            await update.message.reply_text(text=msg_erro)
        return ConversationHandler.END

    try:
        enderecos = await _buscar_endereco_para_anotacao(
            user_id_telegram=user_id_telegram, id_endereco=id_endereco
        )
        if not enderecos:
            logger.warning(
                f'[iniciar_anotacao_por_id] Endereço {id_endereco} não '
                f'encontrado para usuário {user_id_telegram}.'
            )
            msg_nao_encontrado = (
                '⚠️ O endereço especificado não foi encontrado ou você não '
                'tem permissão para vê-lo.'
            )
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text=msg_nao_encontrado
                )
            elif update.message:
                await update.message.reply_text(text=msg_nao_encontrado)
            return ConversationHandler.END

        return await _pedir_texto_anotacao_para_endereco(
            update, context, enderecos[0]
        )
    except Exception as e:
        logger.exception(
            f'[iniciar_anotacao_por_id] Erro ao processar anotação para '
            f'id_endereco {id_endereco}: {e}'
        )
        msg_erro_geral = (
            '😞 Ocorreu um erro ao iniciar a anotação. '
            'Por favor, tente novamente.'
        )
        if update.callback_query:
            await update.callback_query.edit_message_text(text=msg_erro_geral)
        elif update.message:
            await update.message.reply_text(text=msg_erro_geral)
        return ConversationHandler.END


def _extrair_id_endereco_callback(
    query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE
) -> tuple[int | None, str | None]:
    """Extrai e valida o id_endereco a partir do callback data."""
    # Padronizado para usar o prefixo 'anotacao_iniciar_id_'
    prefixo_esperado = 'anotacao_iniciar_id_'
    if not query.data or not query.data.startswith(prefixo_esperado):
        logger.warning(
            f"[_extrair_id_endereco_callback] Callback data '{query.data}' "
            f"não inicia com o prefixo esperado '{prefixo_esperado}'."
        )
        return (
            None,
            f'ID do endereço não encontrado no callback data (prefixo '
            f'{prefixo_esperado} ausente)',
        )
    try:
        # Extrai a parte do ID após o prefixo
        id_endereco_str = query.data[len(prefixo_esperado) :]
        id_endereco = int(id_endereco_str)
        logger.info(
            f'[_extrair_id_endereco_callback] ID do endereço extraído do'
            f' callback: {id_endereco}'
        )
        return id_endereco, None
    except (IndexError, ValueError) as e:
        logger.exception(
            f'[_extrair_id_endereco_callback] Erro ao tentar extrair o ID'
            f' do endereço do callback data ({query.data}): {e}'
        )
        return None, 'Erro ao processar ID do endereço do callback data'


async def iniciar_anotacao_por_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Inicia o fluxo de anotação a partir de um callback query
      (botão "Fazer Anotação").
    """
    logger.info(
        f'[ANOT_CALLBACK_DEBUG] iniciar_anotacao_por_callback chamada com '
        f'update: {update}, callback_data: '
        f'{update.callback_query.data if update.callback_query else "N/A"}'
    )
    if not await _verificar_usuario_e_definir_id_telegram(update, context):
        logger.info(
            '[ANOT_CALLBACK_DEBUG] iniciar_anotacao_por_callback retornando '
            'ConversationHandler.END devido a '
            '_verificar_usuario_e_definir_id_telegram.'
        )
        return ConversationHandler.END
    user_id_telegram = context.user_data['user_id_telegram']

    query = update.callback_query
    await query.answer()

    logger.info(
        f'[iniciar_anotacao_por_callback] INICIADO com callback_data: '
        f'{query.data}, user_id: {user_id_telegram}'
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
            f'[iniciar_anotacao_por_callback] Erro ao extrair id_endereco: '
            f'{erro_id}'
        )
        try:
            if query:
                await query.edit_message_text(
                    '😞 Ocorreu um erro ao identificar o endereço. '
                    'Por favor, tente novamente.'
                )
        except Exception:
            logger.error(
                '[iniciar_anotacao_por_callback] Falha ao editar mensagem de'
                ' erro para id_endereco ausente.'
            )
        logger.info(
            '[ANOT_CALLBACK_DEBUG] iniciar_anotacao_por_callback retornando '
            'ConversationHandler.END devido a erro_id em '
            '_extrair_id_endereco_callback.'
        )
        return ConversationHandler.END

    logger.info(
        f'[iniciar_anotacao_por_callback] Usuário {user_id_telegram} '
        f'iniciando anotação para id_endereco: {id_endereco} via callback.'
    )

    try:
        enderecos = await _buscar_endereco_para_anotacao(
            user_id_telegram=user_id_telegram,
            id_endereco=id_endereco,
        )
        if not enderecos:  # Simplificado
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
            logger.info(
                '[ANOT_CALLBACK_DEBUG] iniciar_anotacao_por_callback '
                'retornando ConversationHandler.END porque endereço não foi '
                'encontrado.'
            )
            return ConversationHandler.END

        proximo_estado = await _pedir_texto_anotacao_para_endereco(
            update, context, enderecos[0]
        )
        logger.info(
            f'[ANOT_CALLBACK_DEBUG] iniciar_anotacao_por_callback: '
            f'_pedir_texto_anotacao_para_endereco retornou {proximo_estado}. '
            'Retornando isso.'
        )
        return proximo_estado
    except Exception as e:
        logger.exception(
            f'[iniciar_anotacao_por_callback] Erro ao buscar endereço '
            f'{id_endereco} para anotação via callback: {e}'
        )
        try:
            await query.edit_message_text(
                '😞 Ocorreu um erro ao buscar os dados do endereço. '
                'Por favor, tente novamente mais tarde.'
            )
        except Exception:
            chat_id = update.effective_chat.id
            if chat_id:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text='😞 Ocorreu um erro ao buscar os dados do endereço. '
                    'Por favor, tente novamente mais tarde.',
                )
        logger.info(
            '[ANOT_CALLBACK_DEBUG] iniciar_anotacao_por_callback retornando '
            'ConversationHandler.END devido a exceção geral.'
        )
        return ConversationHandler.END


async def anotar_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Handler para o comando /anotar.
    Inicia o fluxo de conversa para adicionar uma anotação.
    """
    if not await _verificar_usuario_e_definir_id_telegram(update, context):
        return ConversationHandler.END
    user_id_telegram = context.user_data['user_id_telegram']

    if context.args and len(context.args) > 0 and context.args[0].isdigit():
        id_endereco_arg = int(context.args[0])

        try:
            enderecos = await _buscar_endereco_para_anotacao(
                user_id_telegram=user_id_telegram, id_endereco=id_endereco_arg
            )

            if not enderecos:
                await update.message.reply_text(
                    (
                        '⚠️ Endereço não encontrado. Verifique o ID ou tente'
                        ' outro.'
                    ),
                    reply_markup=teclado_endereco_nao_encontrado_criar(),
                )
                return ID_ENDERECO  # Permanece pedindo ID

            return await _pedir_texto_anotacao_para_endereco(
                update, context, enderecos[0]
            )
        except Exception as e:
            logger.exception(  # Mudado para exception
                f'Erro ao buscar endereço para anotação: {e}'
            )
            await update.message.reply_text(
                '😞 Ocorreu um erro ao buscar os dados do endereço. '
                'Por favor, tente novamente mais tarde.'
            )
            return ConversationHandler.END

    await update.message.reply_text(
        '📝 *Adicionar Anotação*\\n\\n'
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
    if not await _verificar_usuario_e_definir_id_telegram(update, context):
        return ConversationHandler.END
    user_id_telegram = context.user_data['user_id_telegram']

    if not update.message or not update.message.text:
        await update.message.reply_text(
            'Por favor, envie um ID ou código de endereço válido.',
            reply_markup=teclado_simples_cancelar_anotacao(),
        )
        return ID_ENDERECO

    texto_id_ou_codigo = update.message.text.strip()

    try:
        if texto_id_ou_codigo.isdigit():
            enderecos = await _buscar_endereco_para_anotacao(
                user_id_telegram=user_id_telegram,
                id_endereco=int(texto_id_ou_codigo),
            )
        else:
            enderecos = await _buscar_endereco_para_anotacao(
                user_id_telegram=user_id_telegram,
                codigo_endereco=texto_id_ou_codigo,
            )

        if not enderecos:
            await update.message.reply_text(
                (
                    '⚠️ Endereço não encontrado. Verifique o ID/código ou'
                    ' tente outro.'
                ),
                reply_markup=teclado_endereco_nao_encontrado_criar(),
            )
            return ID_ENDERECO

        return await _pedir_texto_anotacao_para_endereco(
            update, context, enderecos[0]
        )
    except Exception as e:
        logger.exception(  # Mudado para exception
            f'Erro ao buscar endereço para anotação: {e}'
        )
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
    if not await _verificar_usuario_e_definir_id_telegram(update, context):
        return ConversationHandler.END
    user_id_telegram = context.user_data['user_id_telegram']

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
            prefixo='finalizar_anotacao'
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
    if not await _verificar_usuario_e_definir_id_telegram(update, context):
        return ConversationHandler.END
    user_id_telegram = context.user_data['user_id_telegram']

    query = update.callback_query
    await query.answer()

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

    if query.data == 'finalizar_anotacao_nao':
        logger.info(
            f'[finalizar_anotacao] Usuário {user_id_telegram} '
            'cancelou a anotação na etapa de confirmação. '
            'Chamando cancelar_anotacao.'
        )
        # Chama a função de cancelamento completa para garantir limpeza
        # e redirecionamento adequados.
        return await cancelar_anotacao(update, context)

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
                user_id=user_id_telegram,  # Passando user_id_telegram
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
                # Se editar falhar, tentar responder
                # à mensagem original do callback
                if query.message:
                    await query.message.reply_text(texto)
                    logger.info(
                        '[cancelar_anotacao] Nova mensagem'
                        ' (reply) enviada com sucesso.'
                    )
                    return
            except Exception as e2:
                logger.error(
                    'Falha ao enviar mensagem alternativa de cancelamento: '
                    f'{e2}'
                )
    if message:  # Se veio de um comando /cancelar
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
    # Fallback final: enviar para o chat_id se disponível
    chat_id = context.user_data.get('chat_id') or (
        update.effective_chat and update.effective_chat.id
    )
    if chat_id:
        try:
            await context.bot.send_message(chat_id=chat_id, text=texto)
            logger.info(
                '[cancelar_anotacao] Mensagem enviada via'
                ' send_message (fallback).'
            )
        except Exception as e:
            logger.error(
                'Falha ao enviar mensagem de cancelamento via send_message: '
                f'{e}'
            )


async def _tentar_exibir_menu_principal_com_fallback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    query: CallbackQuery | None,
):
    """Tenta exibir o menu principal, primeiro editando a mensagem se query
    existir, depois enviando uma nova mensagem como fallback."""
    try:
        await exibir_menu_principal(
            update, context, editar_mensagem=bool(query)
        )
        logger.info(
            '[_tentar_exibir_menu_principal_com_fallback] Menu principal'
            ' exibido/editado.'
        )
    except Exception as e:
        logger.error(
            f'[_tentar_exibir_menu_principal_com_fallback] Erro ao exibir'
            f' menu (tentativa 1, editar_mensagem={bool(query)}): {e}'
        )
        # Se query existe, a primeira tentativa foi com editar_mensagem=True.
        # Tentar enviar nova mensagem como fallback.
        if query:
            try:
                logger.info(
                    '[_tentar_exibir_menu_principal_com_fallback] Tentando'
                    ' exibir menu como nova mensagem.'
                )
                await exibir_menu_principal(
                    update, context, editar_mensagem=False
                )
                logger.info(
                    '[_tentar_exibir_menu_principal_com_fallback] Menu'
                    ' principal exibido como nova mensagem (fallback).'
                )
            except Exception as e2:
                logger.error(
                    '[_tentar_exibir_menu_principal_com_fallback] Erro'
                    f' crítico ao exibir menu como nova mensagem: {e2}'
                )
        # Se não era query, a primeira tentativa (editar_mensagem=False)
        # já falhou. O erro já foi logado.


async def cancelar_anotacao(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Cancela a operação de anotação."""
    user_id_telegram = context.user_data.get('user_id_telegram')
    if not user_id_telegram:
        if not await _verificar_usuario_e_definir_id_telegram(update, context):
            user_id_telegram = 'ID Desconhecido (Falha na verificação)'
        else:
            user_id_telegram = context.user_data['user_id_telegram']

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

    veio_de_busca_rapida = context.user_data.pop('veio_de_busca_rapida', False)

    if veio_de_busca_rapida:
        try:
            logger.info(
                '[cancelar_anotacao] Iniciando conversa de busca rápida.'
            )
            # Criar botão que irá acionar o conversation handler
            # usando um callback pattern que está nos entry_points

            teclado = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔍 Iniciar Busca Rápida",
                    callback_data="nova_busca_rapida"
                )],
                [InlineKeyboardButton(
                    "↩️ Voltar ao Menu",
                    callback_data="voltar_menu_principal"
                )]
            ])

            await query.edit_message_text(
                text=(
                    "✅ *Anotação cancelada*\n\n"
                    "Deseja continuar com a busca rápida?"
                ),
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=teclado,
            )

            logger.info(
                '[cancelar_anotacao] Interface para iniciar busca rápida '
                'exibida com sucesso.'
            )
        except Exception as e:
            logger.error(
                f'[cancelar_anotacao] Erro ao iniciar conversa '
                f'de busca rápida: {e}'
            )
            # Fallback para menu principal
            await _tentar_exibir_menu_principal_com_fallback(
                update, context, query
            )
    else:
        # Exibir menu principal
        await _tentar_exibir_menu_principal_com_fallback(
            update, context, query
        )

    return ConversationHandler.END


async def listar_anotacoes_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Lista as anotações do usuário ou de um endereço específico.
    """
    if not await _verificar_usuario_e_definir_id_telegram(update, context):
        return  # Não é ConversationHandler, então só retorna
    user_id_telegram = context.user_data['user_id_telegram']

    id_endereco_arg = None
    if context.args and context.args[0].isdigit():
        id_endereco_arg = int(context.args[0])

    try:
        # FiltrosEndereco não é usado diretamente aqui,
        # mas sim em buscar_endereco
        anotacoes_dicts = await listar_anotacoes(
            id_usuario=user_id_telegram if not id_endereco_arg else None,
            id_endereco=id_endereco_arg,
            user_id=user_id_telegram,  # user_id para a camada de serviço
        )
        if not anotacoes_dicts:
            if id_endereco_arg:
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

        mensagem = '📝 *Suas Anotações*\\n\\n'

        for anotacao_dict in anotacoes_dicts:
            try:
                anotacao_obj = AnotacaoRead.model_validate(anotacao_dict)
            except Exception as e:
                logger.error(
                    f'Erro ao validar anotação: {anotacao_dict}. Erro: {e}'
                )
                continue  # Pula esta anotação se a validação falhar

            # Buscar o endereço associado a esta anotação
            # É importante passar user_id_telegram para buscar_endereco
            # para respeitar permissões.
            enderecos_anotacao = await _buscar_endereco_para_anotacao(
                user_id_telegram=user_id_telegram,
                id_endereco=anotacao_obj.id_endereco,
            )

            if enderecos_anotacao:
                endereco_formatado = formatar_endereco(enderecos_anotacao[0])
                mensagem += f'📍 *Endereço*: {endereco_formatado}\\n'
                mensagem += (
                    f'📝 *Anotação*: {escape_markdown(anotacao_obj.texto)}\\n'
                )
                mensagem += '\\n'
            else:
                id_endereco_str = str(anotacao_obj.id_endereco)
                mensagem += (
                    f'⚠️ *Endereço ID {escape_markdown(id_endereco_str)} '
                    f'não encontrado ou inacessível*\\n'
                )
                mensagem += (
                    f'📝 *Anotação*: {escape_markdown(anotacao_obj.texto)}\\n'
                )
                mensagem += '\\n'

        await update.message.reply_text(
            mensagem, parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.exception(f'Erro ao listar anotações: {str(e)}')
        # Mudado para exception
        await update.message.reply_text(
            '😞 Ocorreu um erro ao listar as anotações. '
            'Por favor, tente novamente mais tarde.'
        )


def get_anotacao_conversation() -> ConversationHandler:
    """
    Cria e retorna o ConversationHandler para o fluxo de anotação.
    """
    entry_pattern = r'^anotacao_iniciar_id_\d+$'
    logger.info(
        f'[AnotacaoConvBuilder] Criando ConversationHandler com '
        f"entry_pattern para callback: '{entry_pattern}'"
    )
    return ConversationHandler(
        entry_points=[
            CommandHandler('anotar', anotar_command),
            CallbackQueryHandler(
                iniciar_anotacao_por_callback,
                pattern=entry_pattern,
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
                ),
                CallbackQueryHandler(
                    finalizar_anotacao,
                    # Trata o _nao também (agora chama cancelar_anotacao)
                    pattern=r'^finalizar_anotacao_nao$',
                ),
            ],
        },
        fallbacks=[
            CommandHandler('cancelar', cancelar_anotacao),
            CallbackQueryHandler(
                cancelar_anotacao, pattern=r'^anotacao_cancelar_fluxo$'
            ),
            # Removidos os handlers para cancelar_anotacao_simples e
            # cancelar_processo_anotacao pois foram unificados em
            # anotacao_cancelar_fluxo.
            # O CallbackQueryHandler para finalizar_anotacao_nao foi removido
            # pois o estado CONFIRMAR agora lida com isso diretamente
            # chamando cancelar_anotacao.
        ],
        map_to_parent={
            # Se a conversa de busca rápida chamou esta, ela pode retornar
            # para um estado específico da busca rápida.
            ConversationHandler.END: ConversationHandler.END
            # TODO: Considerar se um estado específico de retorno é necessário
            # para a busca rápida.
        },
        persistent=False,  # Manter como False se não houver necessidade clara
        name='anotacao_conversation',
    )
