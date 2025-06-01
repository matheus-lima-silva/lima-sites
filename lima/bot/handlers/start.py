"""
Handlers para comandos básicos como /start e /help.
"""

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from lima.database import get_async_session  # Adicionado

from ..formatters.base import escape_markdown
from ..services.usuario import obter_ou_criar_usuario

logger = logging.getLogger(__name__)


async def start_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handler para o comando /start.
    Recebe o usuário e exibe uma mensagem de boas-vindas.
    Atualiza o last_seen do usuário através do obter_ou_criar_usuario.
    """
    user = update.effective_user
    if not user:
        logger.warning('Comando /start recebido sem um usuário efetivo.')
        await update.message.reply_text(
            'Não foi possível identificar seu usuário. Tente novamente.'
        )
        return

    user_id_telegram = user.id
    # O telefone é usado como identificador único no formato 'telegram_<ID>'
    # e também para o campo 'telefone' no schema UsuarioCreate via API.
    telefone_para_registro_e_busca = f'telegram_{user_id_telegram}'
    nome_usuario = user.full_name

    try:
        # obter_ou_criar_usuario agora espera:
        # - telegram_user_id: int
        # - nome: Optional[str]
        # - telefone: Optional[str] (anteriormente telefone_id_interno)
        # - session: AsyncSession (novo)
        # O parâmetro user_id_telegram_para_get foi removido.

        db_user, access_token = (None, None)  # Inicializa as variáveis
        async with get_async_session() as session:  # Corrigido
            db_user, access_token = await obter_ou_criar_usuario(
                session=session,
                telegram_user_id=user_id_telegram,
                nome=nome_usuario,
                telefone=telefone_para_registro_e_busca,
            )

        if db_user:  # Checa se db_user não é None
            context.user_data['usuario_id'] = db_user.id
            # O token de acesso pode ser armazenado se necessário para
            # chamadas de API subsequentes
            context.user_data['access_token'] = access_token
        else:
            logger.error(
                f'Não foi possível obter/criar usuário para '
                f'{user_id_telegram} no comando /start. '
                f'Resposta: db_user={db_user}, access_token={access_token}'
            )
            await update.message.reply_text(
                'Houve um problema ao configurar sua conta. '
                'Por favor, tente /start novamente mais tarde.'
            )
            return

        context.user_data['user_id_telegram'] = user_id_telegram

        # Mensagem de boas-vindas
        nome_formatado = escape_markdown(nome_usuario)
        mensagem_ola = f'Olá, {nome_formatado}\\! Bem\\-vindo ao '
        mensagem_bot = '*Bot de Endereços*\\.\n\n'
        mensagem_intro = (
            'Com este bot, você pode:\n'
            '• Buscar endereços por diversos critérios\n'
            '• Consultar detalhes de endereços específicos\n'
            '• Fazer sugestões de novos endereços ou alterações\n'
            '• Adicionar anotações a endereços existentes\n\n'
            'Use /help para ver a lista de comandos disponíveis\\.'
        )
        mensagem = mensagem_ola + mensagem_bot + mensagem_intro

        await update.message.reply_text(
            mensagem, parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        error_log_msg = (
            f'Erro no comando start para user_id {user_id_telegram}: {str(e)}'
        )
        logger.error(error_log_msg)
        await update.message.reply_text(
            'Ocorreu um erro ao iniciar o bot. Por favor,'
            ' tente novamente mais tarde.'
        )


async def help_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handler para o comando /help.
    Exibe a lista de comandos disponíveis.
    """
    try:
        mensagem = (
            '*Comandos de Busca por Código:*\n'
            '*/id\\_operadora* \\<código\\> \\-'
            ' Busca pelo código da operadora\n'
            '*/id\\_detentora* \\<código\\> \\'
            '- Busca pelo código da detentora\n'
            '*/id\\_sistema* \\<id\\> \\- Busca pelo ID interno do sistema\n'
            '*/cep* \\<cep\\> \\- Busca endereços por CEP\n\n'
            '*Comandos de Listagem e Filtros:*\n'
            '*/listar* \\- Lista endereços com paginação\n'
            '*/filtrar\\_cidade* \\<cidade\\> \\- Filtra por cidade\n'
            '*/filtrar\\_uf* \\<uf\\> \\- Filtra por estado\n'
            '*/filtrar\\_operadora* \\<nome\\> \\- Filtra por operadora\n\n'
            '*Comandos de Funcionalidade:*\n'
            '*/anotar* \\<id\\_sistema\\> \\- Adiciona anotação\n'
            '*/anotacoes* \\[id\\_sistema\\] \\- Lista suas anotações\n'
            '*/sugerir* \\- Envia sugestão de melhoria\n'
            '*/localizacao* \\- Busca por proximidade geográfica\n'
            '*/help* \\- Mostra esta ajuda\n\n'
            '*Dica:* Use os botões interativos'
            ' para navegar pelos resultados\\!'
        )

        await update.message.reply_text(
            mensagem, parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f'Erro no comando help: {str(e)}')
        await update.message.reply_text(
            'Ocorreu um erro ao exibir a ajuda.'
            ' Por favor, tente novamente mais tarde.'
        )
