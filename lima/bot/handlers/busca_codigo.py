"""
Handler para Busca Rápida por Código - Refatoração V2.
Implementa o fluxo de busca direta por diferentes tipos de código.
"""

import logging
from typing import Any, Dict, List

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

from ..formatters.base import escape_markdown
from ..keyboards import (
    criar_botoes_nenhum_resultado,
    criar_teclado_tipos_codigo,
)
from ..services.auth import (
    autenticar_e_preparar_contexto_comando,
    reautenticar_usuario_se_necessario,
    validar_dados_usuario_contexto,
)
from ..services.endereco import buscar_endereco_por_codigo
from ..services.usuario import obter_ou_criar_usuario
from ..shared.types import AGUARDANDO_CODIGO, SELECIONANDO_TIPO_CODIGO
from .endereco_visualizacao import (
    exibir_endereco_completo,
    exibir_multiplos_resultados,
)

logger = logging.getLogger(__name__)


async def buscar_por_codigo(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """
    Interface para iniciar busca por código.
    Esta função serve como wrapper para iniciar_busca_rapida.
    Foi criada para compatibilidade de importação em scripts de teste.

    Args:
        update: Objeto update do Telegram
        context: Contexto do bot
    """
    return await iniciar_busca_rapida(update, context)


# Constantes para valores mágicos
MAX_RESULTADOS_MULTIPLOS_EXIBICAO = 5
MAX_DESC_CURTA_LEN = 50


# Funções auxiliares


def _limpar_formatacao_markdown(texto: str) -> str:
    """Remove todos os caracteres especiais do MarkdownV2 para fallback."""
    caracteres_especiais = [
        '*',
        '_',
        '`',
        '\\',
        '[',
        ']',
        '(',
        ')',
        '~',
        '>',
        '#',
        '+',
        '-',
        '=',
        '|',
        '{',
        '}',
        '.',
        '!',
    ]
    texto_limpo = texto
    for char in caracteres_especiais:
        texto_limpo = texto_limpo.replace(char, '')
    return texto_limpo


async def _lidar_com_erro_autenticacao(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    mensagem_erro: str,
    query: Any = None,
    show_alert_query: bool = True,
) -> None:
    """Lida com o envio de mensagens de erro de autenticação."""
    if query:
        await query.answer(
            'Falha na autenticação.' if show_alert_query else None,
            show_alert=show_alert_query,
        )
        try:
            await query.edit_message_text(
                mensagem_erro, parse_mode=ParseMode.MARKDOWN_V2
            )
        except Exception as e:
            logger.warning(
                'Falha ao editar msg do query em'
                ' _lidar_com_erro_autenticacao: %s',
                e,
            )
            # Fallback: tentar enviar sem formatação
            try:
                # Remove todos os caracteres especiais do MarkdownV2
                mensagem_simples = _limpar_formatacao_markdown(mensagem_erro)
                await query.edit_message_text(mensagem_simples)
            except Exception as e2:
                logger.warning(
                    'Falha no fallback de edição'
                    ' em _lidar_com_erro_autenticacao: %s',
                    e2,
                )
                # Último recurso: enviar nova mensagem
                if update.effective_chat:
                    try:
                        mensagem_simples = _limpar_formatacao_markdown(
                            mensagem_erro
                        )
                        await context.bot.send_message(
                            update.effective_chat.id,
                            mensagem_simples,
                        )
                    except Exception as e3:
                        logger.error(
                            'Falha crítica ao enviar mensagem de erro em'
                            ' _lidar_com_erro_autenticacao: %s',
                            e3,
                        )
    elif update.effective_message:
        try:
            await update.effective_message.reply_text(
                mensagem_erro, parse_mode=ParseMode.MARKDOWN_V2
            )
        except Exception as e:
            logger.warning(
                'Falha ao enviar reply com markdown em'
                ' _lidar_com_erro_autenticacao: %s',
                e,
            )
            # Fallback: enviar sem formatação
            try:
                # Remove todos os caracteres especiais do MarkdownV2
                mensagem_simples = _limpar_formatacao_markdown(mensagem_erro)
                await update.effective_message.reply_text(mensagem_simples)
            except Exception as e2:
                logger.error(
                    'Falha crítica no fallback de reply em'
                    ' _lidar_com_erro_autenticacao: %s',
                    e2,
                )


async def _autenticar_usuario_para_busca(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """
    Autentica o usuário para a busca rápida.
    Retorna True se autenticado com sucesso, False caso contrário.
    Lida com o envio de mensagens de erro em caso de falha.
    """
    user = update.effective_user
    query = update.callback_query

    if not user:
        logger.error(
            'Não foi possível identificar o usuário em'
            ' _autenticar_usuario_para_busca.'
        )
        mensagem_erro_usr = 'Erro: Não foi possível identificar o usuário.'
        if query:
            await query.answer(mensagem_erro_usr, show_alert=True)
            exibir_menu_principal_func = context.application.bot_data.get(
                'exibir_menu_principal_func'
            )
            if exibir_menu_principal_func:
                await exibir_menu_principal_func(
                    update, context, editar_mensagem=True
                )
            elif query.message:  # Tentar editar a mensagem do callback
                await query.edit_message_text(
                    mensagem_erro_usr + ' Tente /start.'
                )
            elif update.effective_chat:  # Enviar nova mensagem
                await context.bot.send_message(
                    update.effective_chat.id,
                    text=mensagem_erro_usr + ' Tente /start.',
                )
        elif update.effective_message:
            await update.effective_message.reply_text(
                mensagem_erro_usr + ' Tente /start.'
            )
        return False

    try:
        logger.info(f'Autenticando usuário {user.id} para busca.')
        dados_usuario_api = await obter_ou_criar_usuario(
            telegram_user_id=user.id,
            nome=user.full_name,
            telefone_id_interno=f'telegram_{user.id}',
        )
        if dados_usuario_api and 'error' not in dados_usuario_api:
            context.user_data['usuario_id'] = dados_usuario_api.get('id')
            context.user_data['user_id_telegram'] = dados_usuario_api.get(
                'telegram_user_id', user.id
            )
            logger.info(
                f'Usuário autenticado para busca: id='
                f'{context.user_data.get("usuario_id")}, '
                f'telegram_id={context.user_data.get("user_id_telegram")}'
            )
            return True
        else:
            error_detail = (
                dados_usuario_api.get('detail', 'Erro desconhecido')
                if dados_usuario_api
                else 'Resposta None da API'
            )
            logger.error(
                f'Falha na autenticação para busca (usuário {user.id}): '
                f'{error_detail}'
            )
            msg_erro_auth = (
                f'😞 Falha na autenticação: {
                    escape_markdown(str(error_detail))
                }{escape_markdown(".")} '
                f'Tente {escape_markdown("/start")}{escape_markdown(".")}'
            )
            await _lidar_com_erro_autenticacao(
                update, context, msg_erro_auth, query
            )
            return False
    except Exception as e:
        logger.exception(
            f'Exceção durante autenticação para busca (usuário {user.id}): {e}'
        )
        msg_erro_exc = (
            f'😞 Ocorreu um erro inesperado durante a autenticação'
            f'{escape_markdown(".")}\n'
            f'Tente novamente mais tarde{escape_markdown(".")}'
        )
        await _lidar_com_erro_autenticacao(
            update, context, msg_erro_exc, query
        )
        return False


async def _enviar_ou_editar_mensagem_busca_rapida(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup: InlineKeyboardMarkup,
) -> bool:
    """Envia/edita msg da busca rápida. True se sucesso."""
    query = update.callback_query
    try:
        if query and query.message:  # Para editar, query.message deve existir
            await query.edit_message_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=reply_markup,
            )
        elif update.effective_message:
            await update.effective_message.reply_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=reply_markup,
            )
        elif update.effective_chat:  # Fallback
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=reply_markup,
            )
        else:
            logger.error(
                '_enviar_ou_editar_mensagem_busca_rapida: Não foi possível '
                'enviar mensagem (sem query.message, effective_message ou '
                'effective_chat).'
            )
            return False
        return True
    except Exception as e:
        logger.error(
            'Erro ao enviar/editar msg em '
            '_enviar_ou_editar_mensagem_busca_rapida: %s',
            e,
        )
        return False


async def iniciar_busca_rapida(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Inicia o fluxo de busca rápida por código.
    """
    query = update.callback_query  # Pode ser None

    if not await _autenticar_usuario_para_busca(update, context):
        return ConversationHandler.END

    if query:
        await query.answer()  # Responder ao callback

    mensagem_texto = (
        '🔍 *Busca Rápida por Código*\n\n'
        'Qual tipo de código você gostaria de usar para a busca?\n\n'
        '📱 *Código da Operadora*\n'
        '   Ex: 12345\n\n'
        '🏢 *Código da Detentora*\n'
        '   Ex: DT001\n\n'
        '🆔 *ID do Sistema*\n'
        '   Ex: 987654'
    )
    teclado = criar_teclado_tipos_codigo()

    if await _enviar_ou_editar_mensagem_busca_rapida(
        update, context, mensagem_texto, teclado
    ):
        return SELECIONANDO_TIPO_CODIGO
    else:
        mensagem_erro_geral = (
            '😞 Ocorreu um erro ao iniciar a busca. '
            'Tente novamente com /start.'
        )
        if update.effective_chat:
            try:
                await context.bot.send_message(
                    update.effective_chat.id, text=mensagem_erro_geral
                )
            except Exception as e_send:
                logger.error(
                    'Falha crítica ao enviar msg de erro final em '
                    'iniciar_busca_rapida: %s',
                    e_send,
                )
        return ConversationHandler.END


async def selecionar_tipo_codigo(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Processa a seleção do tipo de código.
    """
    logger.info('[selecionar_tipo_codigo] INICIADO')
    query = update.callback_query
    if not query:
        logger.error('[selecionar_tipo_codigo] Query é None!')
        return ConversationHandler.END

    await query.answer()
    data = query.data
    logger.info(f'[selecionar_tipo_codigo] Callback data: {data}')
    logger.info(
        '[selecionar_tipo_codigo] Estado atual da conversa '
        '(antes do processamento)'
    )

    # Mapear tipos de código
    tipos_codigo = {
        'tipo_cod_operadora': {
            'nome': 'Código da Operadora',
            'tipo': 'cod_operadora',
            'exemplo': '12345',
        },
        'tipo_cod_detentora': {
            'nome': 'Código da Detentora',
            'tipo': 'cod_detentora',
            'exemplo': 'DT001',
        },
        'tipo_id_sistema': {
            'nome': 'ID do Sistema',
            'tipo': 'id_sistema',
            'exemplo': '987654',
        },
    }

    if data == 'voltar_menu_principal':
        logger.info('[selecionar_tipo_codigo] Voltando ao menu principal')
        exibir_menu_principal_func = context.application.bot_data.get(
            'exibir_menu_principal_func'
        )
        if exibir_menu_principal_func:
            await exibir_menu_principal_func(
                update, context, editar_mensagem=True
            )
        else:
            logger.error(
                'Erro: função exibir_menu_principal_func não encontrada em '
                'bot_data após cancelamento'
            )
        return ConversationHandler.END

    if data not in tipos_codigo:
        logger.error(f'[selecionar_tipo_codigo] Dados inválidos: {data}')
        await query.edit_message_text('😞 Opção inválida. Tente novamente.')
        return ConversationHandler.END

    tipo_info = tipos_codigo[data]
    logger.info(f'[selecionar_tipo_codigo] Tipo selecionado: {tipo_info}')
    context.user_data['tipo_codigo_selecionado'] = tipo_info['tipo']
    context.user_data['nome_tipo_codigo'] = tipo_info['nome']

    tipo_nome_lower = escape_markdown(tipo_info['nome'].lower())
    mensagem = (
        f'📝 *{escape_markdown(tipo_info["nome"])}*\n\n'
        f'Por favor, me envie o *{tipo_nome_lower}*{escape_markdown(".")}\n\n'
        f'*Exemplo:* `{tipo_info["exemplo"]}`\n\n'
        f'*Dica:* Você pode digitar apenas'
        f' o código ou usar `/cancelar` para voltar{escape_markdown(".")}'
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton('🚫 Cancelar', callback_data='cancelar_busca')]
    ])

    try:
        await query.edit_message_text(
            text=mensagem,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboard,
        )
        logger.info(
            '[selecionar_tipo_codigo] Mensagem editada com sucesso, '
            'mudando para AGUARDANDO_CODIGO'
        )
        return AGUARDANDO_CODIGO

    except Exception as e:
        logger.error(f'Erro ao selecionar tipo de código: {str(e)}')
        await query.edit_message_text('😞 Ocorreu um erro. Tente novamente.')
        return ConversationHandler.END


async def _validar_entrada_e_obter_codigo_tipo(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> tuple[str | None, str | None, str | None]:
    """Valida e obtém o código e o tipo de código para processamento."""
    codigo: str | None = None
    if 'codigo_para_processar' in context.user_data:
        codigo = context.user_data.pop('codigo_para_processar')
    elif update.message and update.message.text:
        codigo = update.message.text.strip()

    if not codigo:
        if update.message:
            await update.message.reply_text(
                '😞 Por favor, envie um código válido ou use /cancelar.'
            )
        # Retorna None para indicar que a conversa deve aguardar ou
        # ser encerrada dependendo do estado.
        # O chamador (processar_codigo) decidirá o estado de retorno.
        return None, None, None

    tipo_codigo = context.user_data.get('tipo_codigo_selecionado')
    nome_tipo = context.user_data.get('nome_tipo_codigo', 'código')

    if not tipo_codigo:
        logger.error(
            '_validar_entrada_e_obter_codigo_tipo chamado sem '
            'tipo_codigo_selecionado.'
        )
        if update.effective_message:
            await update.effective_message.reply_text(
                '😞 Tipo de código não especificado. '
                'Use o menu ou um comando direto como '
                '`/cod_operadora <código>`.',
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        return None, None, None  # Indica falha que deve encerrar a conversa
    return codigo, tipo_codigo, nome_tipo


async def _enviar_acao_digitando(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Envia a ação 'typing' se houver um alvo de mensagem."""
    target_for_typing = update.effective_message or (
        update.callback_query and update.callback_query.message
    )
    if target_for_typing:
        await context.bot.send_chat_action(
            chat_id=target_for_typing.chat_id, action='typing'
        )
    else:
        logger.warning(
            "Não foi possível enviar 'typing' action: sem mensagem alvo."
        )


async def _processar_resultados_busca(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    resultados: List[Dict[str, Any]],
    codigo: str,
    nome_tipo: str,
) -> int:
    """Processa os resultados da busca e envia a resposta apropriada."""
    logger.info(
        f'DEBUG: _processar_resultados_busca - Resultados recebidos: {
            resultados
        }'
    )
    target_message_for_reply = update.effective_message
    if not target_message_for_reply and update.callback_query:
        target_message_for_reply = update.callback_query.message

    if not target_message_for_reply:
        logger.error(
            'Não foi possível determinar a mensagem alvo para resposta em '
            '_processar_resultados_busca.'
        )
        return ConversationHandler.END

    if not resultados or len(resultados) == 0:
        mensagem = (
            f'❌ *Nenhum endereço encontrado*\n\n'
            f'Não encontrei nenhum endereço para o '
            f'{escape_markdown(nome_tipo.lower())}: `{
                escape_markdown(codigo)
            }`\n\n'
            f'*Sugestões:*\n'
            f'• Verifique se o código está correto\n'
            f'• Tente um tipo de código diferente\n'
            f'• Explore nossa base de endereços'
        )
        keyboard = criar_botoes_nenhum_resultado()
        await target_message_for_reply.reply_text(
            text=mensagem,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboard,
        )
        return ConversationHandler.END

    elif len(resultados) == 1:
        endereco = resultados[0]
        await exibir_endereco_completo(update, context, endereco)
        return ConversationHandler.END

    else:  # Múltiplos resultados
        await exibir_multiplos_resultados(
            update, context, resultados, codigo, nome_tipo
        )
        # Mantém a conversa ativa para permitir cancelamento
        # A seleção de resultados é feita por callbacks globais
        return AGUARDANDO_CODIGO


async def processar_codigo(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Processa o código enviado pelo usuário e executa a busca."""
    (
        codigo,
        tipo_codigo,
        nome_tipo,
    ) = await _validar_entrada_e_obter_codigo_tipo(update, context)

    if codigo is None:  # Falha na validação inicial
        # Se codigo é None mas tipo_codigo existe, aguarda novo código
        # Se tipo_codigo também é None, encerra a conversa
        return AGUARDANDO_CODIGO if tipo_codigo else ConversationHandler.END

    # Se codigo e tipo_codigo são válidos, nome_tipo não deveria ser None
    if nome_tipo is None:
        nome_tipo = 'código'

    await _enviar_acao_digitando(update, context)

    try:
        usuario_id, user_id_telegram = await validar_dados_usuario_contexto(
            update, context
        )
        if not usuario_id or not user_id_telegram:
            # Erro de autenticação já logado e msg enviada
            return ConversationHandler.END

        logger.info(
            f'Buscando endereço. Código: {codigo}, Tipo: {tipo_codigo}, '
            f'UsuarioID: {usuario_id}, TelegramID: {user_id_telegram}'
        )

        resultados = await buscar_endereco_por_codigo(
            codigo=codigo,
            tipo_codigo=tipo_codigo,
            usuario_id=usuario_id,
            user_id_telegram=user_id_telegram,
        )
        logger.info(
            f'DEBUG: processar_codigo - Resultados da API: {resultados}'
        )
        context.user_data['resultados_busca'] = resultados
        context.user_data['codigo_busca'] = codigo
        context.user_data['nome_tipo_busca'] = nome_tipo

        return await _processar_resultados_busca(
            update, context, resultados, codigo, nome_tipo
        )

    except Exception:
        logger.exception(
            f'Erro ao processar código {codigo} (tipo: {tipo_codigo})'
        )
        target_message_on_error = update.effective_message
        if not target_message_on_error and update.callback_query:
            target_message_on_error = update.callback_query.message

        if target_message_on_error:
            await target_message_on_error.reply_text(
                f'😞 Ocorreu um erro ao buscar o {nome_tipo.lower()}. '
                'Tente novamente mais tarde.'
            )
        return ConversationHandler.END


async def _validar_callback_e_obter_id(
    query: CallbackQuery | None,
) -> str | None:
    """Valida o callback query e extrai o ID do sistema selecionado."""
    if not query or not query.data:
        logger.warning(
            '_validar_callback_e_obter_id chamado sem query ou query.data'
        )
        return None

    if not query.data.startswith('select_multi_'):
        logger.warning(
            f'Callback inválido em _validar_callback_e_obter_id: {query.data}'
        )
        await query.edit_message_text(
            'Erro: Seleção inválida.', reply_markup=None
        )
        return None

    try:
        return query.data.split('_')[-1]
    except IndexError:
        logger.error(
            f'ID do resultado inválido no callback (split falhou): '
            f'{query.data}'
        )
        await query.edit_message_text(
            'Erro: ID do resultado malformado.', reply_markup=None
        )
        return None


async def _obter_endereco_selecionado_do_contexto(
    context: ContextTypes.DEFAULT_TYPE,
    id_sistema_selecionado: str,
    query: CallbackQuery,
) -> Dict[str, Any] | None:
    """Obtém o endereço selecionado a partir dos resultados da
    busca no contexto."""
    resultados_busca = context.user_data.get('resultados_busca')
    if not resultados_busca:
        logger.warning(
            'Resultados da busca não encontrados no contexto para '
            '_obter_endereco_selecionado_do_contexto.'
        )
        await query.edit_message_text(
            'Desculpe, não encontrei os resultados da busca anterior. '
            'Por favor, tente uma nova busca.',
            reply_markup=None,
        )
        return None

    endereco_selecionado = next(
        (
            end
            for end in resultados_busca
            if str(end.get('id_sistema') or end.get('id'))
            == id_sistema_selecionado
        ),
        None,
    )

    if not endereco_selecionado:
        logger.warning(
            f'Endereço selecionado (ID: {id_sistema_selecionado}) não '
            f'encontrado nos resultados.'
        )
        await query.edit_message_text(
            'Desculpe, o endereço selecionado não foi encontrado. '
            'Por favor, tente uma nova busca.',
            reply_markup=None,
        )
        return None
    return endereco_selecionado


async def selecionar_resultado_multiplo_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handler para o callback quando o usuário seleciona um dos múltiplos
      resultados.
    Este handler deve ser registrado globalmente na aplicação.
    """
    query = update.callback_query
    if not query:
        logger.error(
            'selecionar_resultado_multiplo_callback chamado sem CallbackQuery.'
        )
        return

    id_sistema_selecionado = await _validar_callback_e_obter_id(query)
    if not id_sistema_selecionado:
        return

    await query.answer()

    endereco_selecionado = await _obter_endereco_selecionado_do_contexto(
        context, id_sistema_selecionado, query
    )
    if not endereco_selecionado:
        return

    try:
        await query.delete_message()
    except Exception as e:
        logger.info(
            f'Não foi possível deletar a mensagem de múltiplos resultados: {e}'
        )

    if not await reautenticar_usuario_se_necessario(query, context):
        return

    await exibir_endereco_completo(update, context, endereco_selecionado)


async def _limpar_dados_busca(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Limpa os dados relacionados à busca do user_data."""
    logger.debug('[cancelar_busca] Iniciando limpeza de context.user_data.')
    keys_to_remove = [
        'tipo_codigo_selecionado',
        'nome_tipo_codigo',
        'codigo_para_processar',
        'resultados_busca',
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
        logger.debug(
            f"Chave '{key}' removida (se existia) de context.user_data."
        )
    logger.debug('[cancelar_busca] Limpeza de context.user_data finalizada.')


async def cancelar_busca(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Cancela a operação de busca atual e retorna para a tela de seleção
    de tipo de código, mantendo o estado da conversa.
    """
    logger.info('Operação de busca cancelada pelo usuário.')
    query = update.callback_query

    if query:
        await query.answer()

    await _limpar_dados_busca(context)

    # Texto do menu inicial de busca rápida
    mensagem_menu = (
        '🔍 *Busca Rápida por Código*\n\n'
        'Qual tipo de código você gostaria de usar para a busca?\n\n'
        '📱 *Código da Operadora*\n   Ex: 12345\n\n'
        '🏢 *Código da Detentora*\n   Ex: DT001\n\n'
        '🆔 *ID do Sistema*\n   Ex: 987654'
    )
    teclado = criar_teclado_tipos_codigo()

    # Editar a mensagem atual em vez de deletar e criar nova
    # Isso mantém a continuidade do ConversationHandler
    if query and query.message:
        try:
            await query.edit_message_text(
                text=mensagem_menu,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=teclado,
            )
            logger.info(
                'Menu de seleção de tipo de código atualizado após '
                'cancelamento via callback'
            )
        except Exception as e:
            logger.warning(f'Falha ao editar mensagem: {e}')
            # Fallback: enviar nova mensagem apenas se a edição falhar
            try:
                await query.delete_message()
                if update.effective_chat:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=mensagem_menu,
                        parse_mode=ParseMode.MARKDOWN_V2,
                        reply_markup=teclado,
                    )
                    logger.info('Nova mensagem enviada após falha na edição')
            except Exception as e2:
                logger.error(f'Falha crítica no fallback: {e2}')
    # Comando direto /cancelar ou fallback
    elif update.effective_message:
        await update.effective_message.reply_text(
            mensagem_menu,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=teclado,
        )
        logger.info(
            'Menu de seleção de tipo de código enviado via comando direto'
        )

    logger.info('Retornando SELECIONANDO_TIPO_CODIGO do cancelar_busca')
    return SELECIONANDO_TIPO_CODIGO


async def comando_cod_operadora(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handler para o comando /cod_operadora."""
    codigo = context.args[0] if context.args else None
    if (
        await autenticar_e_preparar_contexto_comando(update, context)
        is not None
    ):
        logger.info(
            f'Comando /cod_operadora: código {codigo}. '
            f'Chamando processar_codigo.'
        )
        await processar_codigo(update, context)


async def comando_cod_detentora(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handler para o comando /cod_detentora."""
    codigo = context.args[0] if context.args else None
    if (
        await autenticar_e_preparar_contexto_comando(update, context)
        is not None
    ):
        logger.info(
            f'Comando /cod_detentora: código {codigo}. '
            f'Chamando processar_codigo.'
        )
        await processar_codigo(update, context)


async def comando_id_sistema(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handler para o comando /id_sistema."""
    codigo = context.args[0] if context.args else None
    if (
        await autenticar_e_preparar_contexto_comando(update, context)
        is not None
    ):
        logger.info(
            f'Comando /id_sistema: código {codigo}. Chamando processar_codigo.'
        )
        await processar_codigo(update, context)


# Handler da Conversa de Busca Rápida (iniciada pelo menu)
handler_busca_rapida = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            iniciar_busca_rapida, pattern='^menu_busca_rapida$'
        ),
        CallbackQueryHandler(
            iniciar_busca_rapida, pattern='^nova_busca_rapida$'
        ),
    ],
    per_message=True,
    states={
        SELECIONANDO_TIPO_CODIGO: [
            CallbackQueryHandler(
                selecionar_tipo_codigo,
                pattern='^(tipo_cod_operadora|tipo_cod_detentora|tipo_id_sistema|voltar_menu_principal)$',
            ),
            CallbackQueryHandler(cancelar_busca, pattern='^cancelar_busca$'),
        ],
        AGUARDANDO_CODIGO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, processar_codigo),
            CallbackQueryHandler(cancelar_busca, pattern='^cancelar_busca$'),
        ],
    },
    fallbacks=[
        CommandHandler('cancelar', cancelar_busca),
        CallbackQueryHandler(cancelar_busca, pattern='^cancelar_busca$'),
        CallbackQueryHandler(cancelar_busca, pattern='^cancelar_busca_geral$'),
    ],
    map_to_parent={  # Se esta conversa for aninhada
        ConversationHandler.END: ConversationHandler.END,
    },
    allow_reentry=True,
    name='busca_codigo_conversation',  # Nome para persistência
)


def get_busca_codigo_handlers() -> List[CommandHandler]:
    """Retorna uma lista de CommandHandlers para busca direta por código."""
    return [
        CommandHandler('cod_operadora', comando_cod_operadora),
        CommandHandler('cod_detentora', comando_cod_detentora),
        CommandHandler('id_sistema', comando_id_sistema),
    ]
