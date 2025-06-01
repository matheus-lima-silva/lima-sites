"""
Handler para o Menu Principal Interativo do Bot (V2).
Este módulo implementa a navegação baseada em menus conforme a refatoração V2.
"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from lima.database import get_async_session

from ..formatters.base import escape_markdown
from ..services.usuario import obter_ou_criar_usuario

logger = logging.getLogger(__name__)

DESCRIPTION = 'Handler para o Menu Principal Interativo do Bot (V2).'

# Padrão de callback para o menu principal e seus submenus diretos.
# Este padrão é cuidadosamente construído para NÃO capturar callbacks
# que iniciam ConversationHandlers, como 'menu_busca_rapida'.
MENU_CALLBACK_PATTERN = (
    r'^('
    r'menu_(explorar_base|minhas_info|ajuda)'
    r'|voltar_menu_principal'
    r'|explorar_(filtrar|proximidade)'
    r'|minhas_anotacoes'
    r'|fazer_sugestao'
    r')$'
)


def criar_menu_principal() -> InlineKeyboardMarkup:
    """
    Cria o teclado inline do Menu Principal.

    Returns:
        Teclado inline com as opções do menu principal.
    """
    keyboard = [
        [
            InlineKeyboardButton(
                '🔍 Busca Rápida por Código', callback_data='menu_busca_rapida'
            )
        ],
        [
            InlineKeyboardButton(
                '🗺️ Explorar Base de Endereços',
                callback_data='menu_explorar_base',
            )
        ],
        [
            InlineKeyboardButton(
                '📝 Minhas Informações e Ações',
                callback_data='menu_minhas_info',
            )
        ],
        [
            InlineKeyboardButton(
                'ℹ️ Ajuda e Suporte', callback_data='menu_ajuda'
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def criar_submenu_explorar() -> InlineKeyboardMarkup:
    """
    Cria o submenu para "Explorar Base de Endereços".

    Returns:
        Teclado inline com opções de exploração.
    """
    keyboard = [
        [
            InlineKeyboardButton(
                '🔸 Listar/Filtrar Endereços', callback_data='explorar_filtrar'
            )
        ],
        [
            InlineKeyboardButton(
                '🔸 Buscar por Proximidade (GPS)',
                callback_data='explorar_proximidade',
            )
        ],
        [
            InlineKeyboardButton(
                '↩️ Voltar ao Menu', callback_data='voltar_menu_principal'
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def criar_submenu_minhas_info() -> InlineKeyboardMarkup:
    """
    Cria o submenu para "Minhas Informações e Ações".

    Returns:
        Teclado inline com opções de informações pessoais.
    """
    keyboard = [
        [
            InlineKeyboardButton(
                '🔸 Ver Todas as Minhas Anotações',
                callback_data='minhas_anotacoes',
            )
        ],
        [
            InlineKeyboardButton(
                '🔸 Fazer uma Sugestão', callback_data='fazer_sugestao'
            )
        ],
        [
            InlineKeyboardButton(
                '↩️ Voltar ao Menu', callback_data='voltar_menu_principal'
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def exibir_menu_principal(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    editar_mensagem: bool = False,
) -> None:
    """
    Exibe o Menu Principal.

    Args:
        update: Update do Telegram
        context: Context do bot
        editar_mensagem: Se True, edita a mensagem atual.
                        Se False, envia nova mensagem.
    """
    mensagem = (
        '🏢 *LimaEndereços \\- Menu Principal*\n\n'
        'Escolha uma opção para encontrar ou explorar endereços:\n\n'
        '🔍 *Busca Rápida por Código*\n'
        '   \\(O bot perguntará qual tipo de código você tem\\)\n\n'
        '🗺️ *Explorar Base de Endereços*\n'
        '   Listar/Filtrar endereços ou buscar por proximidade\n\n'
        '📝 *Minhas Informações e Ações*\n'
        '   Ver anotações e fazer sugestões\n\n'
        'ℹ️ *Ajuda e Suporte*\n'
        '   Documentação e comandos disponíveis'
    )

    keyboard = criar_menu_principal()

    try:
        if editar_mensagem and update.callback_query:
            await update.callback_query.edit_message_text(
                text=mensagem,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=keyboard,
            )
        else:
            # Usar update.effective_message para compatibilidade
            await update.effective_message.reply_text(
                text=mensagem,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=keyboard,
            )
    except Exception as e:
        logger.error(f'Erro ao exibir menu principal: {str(e)}')
        await update.effective_message.reply_text(
            '😞 Ocorreu um erro ao exibir o menu. Tente novamente com /start.'
        )


async def start_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handler para o comando /start - Versão V2 com Menu Principal.
    """
    user = update.effective_user
    if not user:
        logger.warning('Comando /start recebido sem um usuário efetivo.')
        await update.message.reply_text(
            'Não foi possível identificar seu usuário. Tente novamente.'
        )
        return

    user_id_telegram = user.id
    nome_usuario = user.full_name
    telefone_para_registro_e_busca = f'telegram_{user_id_telegram}'

    async with get_async_session() as session:
        try:
            usuario_data_tuple = await obter_ou_criar_usuario(
                telegram_user_id=user_id_telegram,
                session=session,
                nome=nome_usuario,
                telefone=telefone_para_registro_e_busca,
                # Adicionado parâmetro telefone
            )

            if usuario_data_tuple and isinstance(usuario_data_tuple, tuple):
                db_usuario = usuario_data_tuple[0]
                if db_usuario and hasattr(db_usuario, 'id'):
                    context.user_data['usuario_id'] = db_usuario.id
                else:
                    logger.error(
                        'Não foi possível obter/criar usuário (DBUsuario '
                        'ausente ou sem ID) para %s no comando /start. '
                        'Resposta: %s',
                        user_id_telegram,
                        usuario_data_tuple,
                    )
                    await update.message.reply_text(
                        'Houve um problema ao configurar sua conta. '
                        'Por favor, tente /start novamente mais tarde.'
                    )
                    return
            else:
                logger.error(
                    'Resposta inesperada de obter_ou_criar_usuario para '
                    '%s no comando /start. Resposta: %s',
                    user_id_telegram,
                    usuario_data_tuple,
                )
                await update.message.reply_text(
                    'Houve um problema ao configurar sua conta. '
                    'Por favor, tente /start novamente mais tarde.'
                )
                return

            context.user_data['user_id_telegram'] = user_id_telegram

            context.user_data.pop('filtros_ativos', None)
            context.user_data.pop('endereco_atual', None)
            context.user_data.pop('busca_estado', None)

            nome_formatado = escape_markdown(nome_usuario)
            usuario_id_str = str(context.user_data['usuario_id'])
            user_id_telegram_str = str(user_id_telegram)

            mensagem_ola = (
                f'Olá, {nome_formatado}\\! Bem\\-vindo ao '
                f'*LimaEndereços*\\.\n\n'
                f'Seu ID de usuário no sistema é: `{usuario_id_str}`\\.\n'
                f'Seu ID no Telegram é: `{user_id_telegram_str}`\\.\n\n'
                f'Use os botões abaixo para navegar:\n'
            )

            await update.message.reply_text(
                mensagem_ola, parse_mode=ParseMode.MARKDOWN_V2
            )

            # Exibir Menu Principal
            await exibir_menu_principal(update, context)

        except Exception as e:
            error_log_msg = (
                f'Erro no comando start para user_id {user_id_telegram}: '
                f'{str(e)}'
            )
            logger.error(error_log_msg)
            await update.message.reply_text(
                'Ocorreu um erro ao iniciar o bot. Por favor,'
                ' tente novamente mais tarde.'
            )


async def listar_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handler para o comando /listar - Vai direto para o Menu Principal.
    """
    await exibir_menu_principal(update, context)


async def menu_principal(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Exibe o Menu Principal.
    """
    texto_menu = (
        '🏢 *LimaEndereços \\- Menu Principal*\n\n'
        'Escolha uma opção para encontrar ou explorar endereços:\n\n'
        '🔍 *Busca Rápida por Código*\n'
        '   \\(O bot perguntará qual tipo de código você tem\\)\n\n'
        '🗺️ *Explorar Base de Endereços*\n'
        '   Listar/Filtrar endereços ou buscar por proximidade\n\n'
        '📝 *Minhas Informações e Ações*\n'
        '   Ver anotações e fazer sugestões\n\n'
        'ℹ️ *Ajuda e Suporte*\n'
        '   Documentação e comandos disponíveis'
    )

    await update.message.reply_text(
        text=texto_menu,
        reply_markup=criar_menu_principal(),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def handle_menu_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Processa os callbacks do menu principal e seus submenus."""
    query = update.callback_query
    if not query or not query.data:
        logger.warning('handle_menu_callback recebido sem query ou query.data')
        return

    await query.answer()
    data = query.data

    # Mapeamento de callbacks para funções/ações
    callback_actions = {
        # 'menu_busca_rapida' removido - será tratado pelo ConversationHandler
        'menu_explorar_base': _handle_explorar_base,
        'menu_minhas_info': _handle_minhas_info,
        'menu_ajuda': _handle_ajuda,
        'voltar_menu_principal': _handle_voltar_menu_principal,
        'explorar_filtrar': _handle_explorar_filtrar,
        'explorar_proximidade': _handle_explorar_proximidade,
        'minhas_anotacoes': _handle_minhas_anotacoes,
        'fazer_sugestao': _handle_fazer_sugestao,
    }

    action = callback_actions.get(data)

    if action:
        await action(update, context)
    else:
        logger.warning(f'Opção de menu desconhecida: {data}')
        await query.edit_message_text(
            '😕 Opção de menu desconhecida. Tente novamente com /start.'
        )


# Funções auxiliares para handle_menu_callback
async def _handle_explorar_base(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    iniciar_exploracao_func = context.application.bot_data.get(
        'iniciar_exploracao_func'
    )
    if iniciar_exploracao_func:
        await iniciar_exploracao_func(update, context)
    else:
        logger.error(
            'Função iniciar_exploracao_func não encontrada em bot_data.'
        )
        if update.callback_query:
            await update.callback_query.edit_message_text(
                'Erro ao iniciar a exploração. Tente /start.'
            )


async def _handle_minhas_info(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    mensagem = (
        '📝 *Minhas Informações e Ações*\n\n'
        'Gerencie suas informações e contribuições:\n\n'
        '🔸 *Ver Todas as Minhas Anotações*\n'
        '   Lista completa das suas anotações\n\n'
        '🔸 *Fazer uma Sugestão*\n'
        '   Sugira melhorias ou novos endereços'
    )
    # Ajuste: Corrigir formatação para Markdown V2 e remover barras extras
    mensagem = (
        '📝 *Minhas Informações e Ações*\n\n'
        'Gerencie suas informações e contribuições:\n\n'
        '🔸 *Ver Todas as Minhas Anotações*\n'
        '   Lista completa das suas anotações\n\n'
        '🔸 *Fazer uma Sugestão*\n'
        '   Sugira melhorias ou novos endereços'
    )
    mensagem = mensagem.replace('\n', '\n')
    keyboard = criar_submenu_minhas_info()
    if query:
        await query.edit_message_text(
            text=mensagem,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboard,
        )


async def _handle_ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await help_command_v2(update, context)


async def _handle_voltar_menu_principal(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    await exibir_menu_principal(update, context, editar_mensagem=True)


async def _handle_explorar_filtrar(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    try:
        iniciar_exploracao_func = context.application.bot_data.get(
            'iniciar_exploracao_func'
        )
        if iniciar_exploracao_func:
            await iniciar_exploracao_func(update, context)
        else:
            logger.error(
                'Função iniciar_exploracao_func não encontrada em bot_data'
            )
            if query:
                await query.edit_message_text(
                    'Erro ao iniciar a exploração. Tente /start.'
                )
    except ImportError:
        if query:
            await query.edit_message_text(
                text='🔸 *Listar/Filtrar Endereços*\n\n'
                'Funcionalidade em desenvolvimento',
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            '↩️ Voltar', callback_data='menu_explorar_base'
                        )
                    ]
                ]),
            )


async def _handle_explorar_proximidade(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    if query:
        mensagem = (
            '🔸 *Buscar por Proximidade*\n\n'
            'Use o comando `/localizacao` para buscar '
            'endereços próximos.'
        )
        await query.edit_message_text(
            text=escape_markdown(mensagem),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        '↩️ Voltar', callback_data='menu_explorar_base'
                    )
                ]
            ]),
        )


async def _handle_minhas_anotacoes(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    if query:
        mensagem = (
            '📝 *Suas Anotações*\n\n'
            'Use o comando `/anotacoes` para ver todas '
            'as suas anotações.'
        )
        await query.edit_message_text(
            text=escape_markdown(mensagem),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        '↩️ Voltar', callback_data='menu_minhas_info'
                    )
                ]
            ]),
        )


async def _handle_fazer_sugestao(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    if query:
        mensagem = (
            '💡 *Fazer Sugestão*\n\n'
            'Use o comando `/sugerir` para enviar sua sugestão.'
        )
        await query.edit_message_text(
            text=escape_markdown(mensagem),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        '↩️ Voltar', callback_data='menu_minhas_info'
                    )
                ]
            ]),
        )


async def help_command_v2(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handler para o comando /help - Versão V2 atualizada.
    """
    try:
        mensagem = (
            'ℹ️ *Ajuda e Suporte \\- LimaEndereços*\n\n'
            '*🏠 Menu Principal:*\n'
            '• `/start` \\- Inicia o bot e exibe o menu principal\n'
            '• `/listar` \\- Vai direto para o menu principal\n'
            '• `/cancelar` \\- Cancela qualquer operação em andamento\n\n'
            '*🔍 Comandos de Busca Direta:*\n'
            '• `/cod_operadora <código>` \\- '
            'Busca pelo código da operadora\n'
            '• `/cod_detentora <código>` \\- '
            'Busca pelo código da detentora\n'
            '• `/id_sistema <id>` \\- '
            'Busca pelo ID interno do sistema\n'
            '• `/cep <cep>` \\- Busca endereços por CEP\n\n'
            '*🗺️ Comandos de Exploração:*\n'
            '• `/cidade <cidade>` \\- Filtra por cidade\n'
            '• `/uf <uf>` \\- Filtra por estado\n'
            '• `/operadora <nome>` \\- Filtra por operadora\n'
            '• `/localizacao` \\- Busca por proximidade geográfica\n\n'
            '*📝 Comandos de Recursos:*\n'
            '• `/anotar <id_sistema>` \\- '
            'Adiciona anotação a um endereço\n'
            '• `/anotacoes` \\- Lista suas anotações\n'
            '• `/sugerir` \\- Envia sugestão de melhoria\n\n'
            '*💡 Dica:* Use o menu interativo para navegar facilmente\\!'
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    '↩️ Voltar ao Menu', callback_data='voltar_menu_principal'
                )
            ]
        ])

        # Determinar se edita ou envia nova mensagem
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=mensagem,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=keyboard,
            )
        elif update.message:
            await update.message.reply_text(
                text=mensagem,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=keyboard,
            )
    except Exception as e:
        logger.error(f'Erro no comando help_v2: {str(e)}')
        if update.effective_message:
            await update.effective_message.reply_text(
                'Ocorreu um erro ao exibir a ajuda.'
            )


async def cancelar_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handler para o comando /cancelar - Cancela qualquer operação
    e volta ao menu.
    """
    # Limpar dados da conversa
    context.user_data.clear()

    await update.message.reply_text(
        '🚫 Operação cancelada. Voltando ao menu principal...'
    )

    # Exibir menu principal
    await exibir_menu_principal(update, context)


# Handlers para registro
def get_menu_handlers():
    """
    Retorna os handlers do menu para registro no main.py.
    """
    return [
        CommandHandler('start', start_command),
        CommandHandler('listar', listar_command),
        CommandHandler('help', help_command_v2),
        CommandHandler('cancelar', cancelar_command),
        CallbackQueryHandler(
            handle_menu_callback,
            pattern=MENU_CALLBACK_PATTERN,
        ),
    ]
