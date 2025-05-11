"""
Módulo para integração core com a API do Telegram Bot.
Este módulo contém funções básicas para envio e recebimento de mensagens via
 Telegram.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
)
from telegram.helpers import escape_markdown

from ...settings import Settings

settings = Settings()
logger = logging.getLogger(__name__)

# Constantes
BOTOES_POR_LINHA = 2  # Número de botões por linha no teclado inline


class TelegramError(Exception):
    """Exceção para erros relacionados à API do Telegram"""
    pass


def check_telegram_credentials():
    """
    Verifica se as credenciais do Telegram estão disponíveis.

    Raises:
        TelegramError: Se as credenciais necessárias não estiverem
         configuradas.
    """
    if not settings.telegram_configured:
        error_msg = 'Token do bot do Telegram não configurado'
        logger.error(error_msg)
        raise TelegramError(error_msg)


class BotManager:
    """
    Gerenciador de instância do bot do Telegram.
    Implementa o padrão Singleton para garantir uma única instância do bot.
    """

    _instance: Optional[Bot] = None

    @classmethod
    def get_instance(cls) -> Bot:
        """
        Retorna a instância atual do bot ou cria uma nova se não existir.

        Returns:
            Bot: Instância do bot do Telegram

        Raises:
            TelegramError: Se as credenciais do Telegram não estiverem
             configuradas
        """
        if cls._instance is None:
            check_telegram_credentials()
            cls._instance = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """
        Reinicia a instância do bot.
        Útil principalmente para testes ou quando é necessário
        recriar a conexão com o bot.
        """
        cls._instance = None


async def get_bot() -> Bot:
    """
    Retorna uma instância do bot do Telegram,
    inicializando-a se necessário.

    Returns:
        Bot: Instância do bot do Telegram.

    Raises:
        TelegramError: Se o token do bot não estiver configurado.
    """
    return BotManager.get_instance()


async def initialize_application() -> Application:
    """
    Inicializa a aplicação do Telegram bot.

    Returns:
        Application: Instância da aplicação do Telegram bot.
    """
    check_telegram_credentials()

    # Inicializa a aplicação com o token do bot
    application = (
        Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    )

    if settings.TELEGRAM_WEBHOOK_URL:
        # Configura o webhook se a URL estiver definida
        webhook_url = settings.TELEGRAM_WEBHOOK_URL
        await application.bot.set_webhook(
            url=webhook_url,
            secret_token=settings.TELEGRAM_SECRET_TOKEN,
        )
        logger.info(f'Webhook configurado para: {webhook_url}')

    return application


async def send_text_message(
    chat_id: Union[int, str], message: str
) -> Dict[str, Any]:
    """
    Envia uma mensagem de texto via Telegram Bot API.

    Args:
        chat_id: ID do chat (usuário ou grupo)
        message: Texto da mensagem a ser enviada

    Returns:
        Dict: Resultado do envio da mensagem

    Raises:
        TelegramError: Se as credenciais do Telegram não estiverem
         configuradas.
    """
    try:
        telegram_bot = await get_bot()

        # Envia a mensagem
        sent_message = await telegram_bot.send_message(
            chat_id=chat_id, text=message, parse_mode=ParseMode.MARKDOWN_V2
        )

        return {'message_id': sent_message.message_id, 'status': 'sent'}
    except Exception as e:
        logger.error(f'Erro ao enviar mensagem: {str(e)}')
        return {'error': str(e)}


async def send_interactive_message(
    chat_id: Union[int, str],
    header_text: str,
    body_text: str,
    footer_text: str = '',
    buttons: List[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Envia uma mensagem interativa com botões via Telegram Bot API.

    Args:
        chat_id: ID do chat (usuário ou grupo)
        header_text: Título da mensagem
        body_text: Corpo da mensagem
        footer_text: Texto do rodapé (opcional)
        buttons: Lista de botões no formato [{"id": "btn_id", "title": "Texto
          do botão"}]

    Returns:
        Dict: Resultado do envio da mensagem

    Raises:
        TelegramError: Se as credenciais do Telegram não estiverem
          configuradas.
    """
    try:
        telegram_bot = await get_bot()

        # Escapa os caracteres especiais para Markdown
        header_escaped = escape_markdown(header_text, version=2)
        body_escaped = escape_markdown(body_text, version=2)
        footer_escaped = (
            escape_markdown(footer_text, version=2) if footer_text else ''
        )

        # Constrói a mensagem completa
        message_text = f'*{header_escaped}*\n\n{body_escaped}'
        if footer_escaped:
            message_text += f'\n\n{footer_escaped}'

        # Cria os botões, se fornecidos
        keyboard = None
        if buttons and len(buttons) > 0:
            keyboard_buttons = []
            # Organiza os botões em linhas de 2 botões cada
            row = []
            for btn in buttons:
                row.append(
                    InlineKeyboardButton(
                        text=btn['title'], callback_data=btn['id']
                    )
                )
                if len(row) == BOTOES_POR_LINHA:
                    keyboard_buttons.append(row)
                    row = []

            # Adiciona a última linha se tiver botões restantes
            if row:
                keyboard_buttons.append(row)

            keyboard = InlineKeyboardMarkup(keyboard_buttons)

        # Envia a mensagem
        sent_message = await telegram_bot.send_message(
            chat_id=chat_id,
            text=message_text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboard,
        )

        return {'message_id': sent_message.message_id, 'status': 'sent'}
    except Exception as e:
        logger.error(f'Erro ao enviar mensagem interativa: {str(e)}')
        return {'error': str(e)}


async def send_location(
    chat_id: Union[int, str],
    latitude: float,
    longitude: float,
    title: str = None,
) -> Dict[str, Any]:
    """
    Envia uma localização via Telegram Bot API.

    Args:
        chat_id: ID do chat (usuário ou grupo)
        latitude: Latitude da localização
        longitude: Longitude da localização
        title: Título opcional para o ponto no mapa

    Returns:
        Dict: Resultado do envio da localização

    Raises:
        TelegramError: Se as credenciais do Telegram não estiverem configuradas
    """
    try:
        telegram_bot = await get_bot()

        # Envia a localização
        sent_message = await telegram_bot.send_location(
            chat_id=chat_id, latitude=latitude, longitude=longitude
        )

        # Se tiver título, envia uma mensagem adicional para contextualizar
        #  a localização
        if title:
            await telegram_bot.send_message(
                chat_id=chat_id,
                text=f'📍 {escape_markdown(title, version=2)}',
                parse_mode=ParseMode.MARKDOWN_V2,
            )

        return {'message_id': sent_message.message_id, 'status': 'sent'}
    except Exception as e:
        logger.error(f'Erro ao enviar localização: {str(e)}')
        return {'error': str(e)}


async def process_webhook_update(update_data: Dict[str, Any]) -> Update:
    """
    Processa uma atualização recebida via webhook.

    Args:
        update_data: Dados da atualização recebida via webhook

    Returns:
        Update: Objeto Update do Telegram
    """
    bot = await get_bot()  # Já faz a verificação de credenciais
    update = Update.de_json(update_data, bot)
    return update


async def extract_message_data(update: Update) -> Dict[str, Any]:
    """
    Extrai dados relevantes de uma atualização do Telegram.

    Args:
        update: Objeto Update do Telegram

    Returns:
        Dict: Dados extraídos da mensagem
    """
    result = {
        'chat_id': None,
        'user_id': None,
        'message_type': None,
        'message_content': None,
        'first_name': None,
        'username': None,
        'is_callback': False,
    }

    if update.message:
        message = update.message
        result['chat_id'] = message.chat_id
        result['user_id'] = message.from_user.id
        result['first_name'] = message.from_user.first_name
        result['username'] = message.from_user.username

        if message.text:
            result['message_type'] = 'text'
            result['message_content'] = message.text
        elif message.location:
            result['message_type'] = 'location'
            result['message_content'] = {
                'latitude': message.location.latitude,
                'longitude': message.location.longitude,
            }

    elif update.callback_query:
        callback = update.callback_query
        result['chat_id'] = callback.message.chat_id
        result['user_id'] = callback.from_user.id
        result['first_name'] = callback.from_user.first_name
        result['username'] = callback.from_user.username
        result['message_type'] = 'interactive'
        result['message_content'] = callback.data
        result['is_callback'] = True

    return result
