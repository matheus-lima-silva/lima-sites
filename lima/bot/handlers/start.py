"""
Handlers para comandos básicos como /start e /help.
"""

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from ..formatters import escape_markdown
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
        logger.warning("Comando /start recebido sem um usuário efetivo.")
        await update.message.reply_text(
            "Não foi possível identificar seu usuário. Tente novamente."
        )
        return

    user_id_telegram = user.id
    # O telefone é usado como identificador único no formato 'telegram_<ID>'
    # e também para o campo 'telefone' no schema UsuarioCreate via API.
    telefone_para_registro_e_busca = f"telegram_{user_id_telegram}"
    nome_usuario = user.full_name

    try:
        # obter_ou_criar_usuario agora espera:
        # - telegram_user_id: int
        #  (para o campo telegram_user_id no payload da API)
        # - nome: Optional[str] (para o campo nome no payload da API)
        # - telefone_id_interno:
        # str (para buscar/identificar, ex: "telegram_123")
        # - user_id_telegram_para_get:
        #  int (para autenticar chamadas GET internas se necessário)

        usuario_data = await obter_ou_criar_usuario(
            telegram_user_id=user_id_telegram,
            nome=nome_usuario,
            telefone_id_interno=telefone_para_registro_e_busca,
            user_id_telegram_para_get=user_id_telegram,
        )

        if usuario_data and isinstance(usuario_data, dict):
            context.user_data['usuario_id'] = usuario_data.get('id')
        else:
            logger.error(
                f"Não foi possível obter/criar usuário para "
                f"{user_id_telegram} no comando /start. "
                f"Resposta: {usuario_data}"
            )
            await update.message.reply_text(
                "Houve um problema ao configurar sua conta. "
                "Por favor, tente /start novamente mais tarde."
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
            f"Erro no comando start para user_id {user_id_telegram}: {str(e)}"
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
            '*Comandos Disponíveis:*\n\n'
            '*/buscar* \\<termo\\> \\- Busca endereços por termo geral\n'
            '*/cep* \\<cep\\> \\- Busca endereços por CEP\n'
            '*/id* \\<id\\> \\- Busca um endereço específico por ID\n'
            '*/cidade* \\<cidade\\> \\- Busca endereços em uma cidade\n'
            '*/uf* \\<uf\\> \\- Busca endereços em um estado\n'
            '*/operadora* \\<operadora\\> \\- Busca por operadora\n'
            '*/sugerir* \\- Inicia processo para enviar uma sugestão\n'
            '*/anotar* \\<id\\> \\- Adiciona anotação a um endereço\n'
            '*/compartilhar* \\<id\\> \\- Compartilha dados de um endereço\n'
            '*/localizacao* \\- Busca endereços próximos à sua localização'
            ' atual\n'
            '*/help* \\- Mostra esta ajuda\n\n'
            'Você também pode usar os botões interativos para navegar'
            ' pelos resultados\\.'
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
