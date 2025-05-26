"""
Módulo principal do bot Telegram.
Este módulo contém a inicialização e configuração do bot.
"""

import logging
import sys
from typing import Optional

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .config import (
    LOG_LEVEL,
    SECRET_TOKEN,
    TOKEN_BOT,
    USE_WEBHOOK,
    WEBHOOK_PORT,
    WEBHOOK_URL,
)
from .handlers import anotacao, busca, start, sugestao
from .handlers.callback import handle_callback

logger = logging.getLogger(__name__)

_application: Optional[Application] = None


async def error_handler(
    update: Optional[Update], context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Manipulador global de erros.
    """
    # Log de erro
    logger.error(f'Erro ao processar update: {context.error}')

    # Notifica o usuário com mensagem amigável
    if update and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='😞 Ocorreu um erro ao processar sua solicitação.'
            ' Por favor, tente novamente mais tarde.',
        )


def configurar_logging() -> None:
    """
    Configura o logging do bot.
    """
    nivel = getattr(logging, LOG_LEVEL)

    # Configura o logger principal
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=nivel,
    )

    # Configura loggers específicos
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)


def criar_aplicacao() -> Application:
    """
    Cria e configura a aplicação do bot.

    Returns:
        Aplicação configurada e pronta para uso.
    """
    global _application

    # Configura logging
    configurar_logging()

    # Verifica token
    if not TOKEN_BOT:
        logger.error(
            'Token do bot não configurado. Configure TOKEN_BOT no arquivo .env'
        )
        sys.exit(1)

    # Cria aplicação
    try:
        application = Application.builder().token(TOKEN_BOT).build()
    except Exception as e:
        logger.error(f'Erro ao criar aplicação: {str(e)}')
        sys.exit(1)

    _application = application

    # Registra o handler de erros
    application.add_error_handler(error_handler)

    # Comandos básicos
    application.add_handler(CommandHandler('start', start.start_command))
    application.add_handler(CommandHandler('help', start.help_command))

    # Comandos de busca
    application.add_handler(CommandHandler('buscar', busca.buscar_command))
    application.add_handler(CommandHandler('id', busca.buscar_por_id_command))
    application.add_handler(
        CommandHandler('cep', busca.buscar_por_cep_command)
    )
    application.add_handler(
        CommandHandler('cidade', busca.buscar_por_cidade_command)
    )
    application.add_handler(CommandHandler('uf', busca.buscar_por_uf_command))
    application.add_handler(
        CommandHandler('operadora', busca.buscar_por_operadora_command)
    )
    application.add_handler(
        CommandHandler('localizacao', busca.buscar_por_localizacao_command)
    )

    # Handler para receber localização compartilhada
    application.add_handler(
        MessageHandler(filters.LOCATION, busca.receber_localizacao)
    )

    # Conversa de sugestão
    application.add_handler(sugestao.get_sugestao_conversation())

    # Conversa de anotação
    application.add_handler(anotacao.get_anotacao_conversation())

    # Comando para listar anotações
    application.add_handler(
        CommandHandler('anotacoes', anotacao.listar_anotacoes_command)
    )

    # Callbacks de botões inline
    # Callbacks de botões inline
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Mensagem para comandos desconhecidos
    application.add_handler(
        MessageHandler(filters.COMMAND, comando_desconhecido)
    )

    return application


async def comando_desconhecido(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handler para comandos desconhecidos.
    """
    await update.message.reply_text(
        'Comando não reconhecido. Use /help para ver os comandos disponíveis.'
    )


async def iniciar_bot() -> None:
    """
    Inicia o bot usando polling ou webhook.
    """
    # Cria e configura a aplicação
    application = criar_aplicacao()

    try:
        # Inicia o bot
        if USE_WEBHOOK:
            logger.info(f'Iniciando bot usando webhook: {WEBHOOK_URL}')

            # Verifica a URL do webhook
            if not WEBHOOK_URL:
                logger.error(
                    'URL do webhook não configurada. Configure WEBHOOK_URL no'
                    ' arquivo .env'
                )
                sys.exit(1)

            # Inicia usando webhook
            webhook_path = TOKEN_BOT
            webhook_url = f'{WEBHOOK_URL}/{webhook_path}'

            # Para webhook, run_webhook é bloqueante e gerencia seu próprio
            #  loop.
            # No entanto, se FastAPI/Uvicorn já está rodando, o ideal é
            # configurar o webhook externamente e apenas processar updates.
            # Esta abordagem aqui é mais para um bot standalone com webhook.
            await application.initialize()
            await application.start()
            await application.updater.start_webhook(
                listen='0.0.0.0',
                port=WEBHOOK_PORT,
                url_path=webhook_path,
                webhook_url=webhook_url,
                secret_token=SECRET_TOKEN,
            )
            # run_webhook é bloqueante, então não precisamos de mais nada aqui
            # se o objetivo é rodar o bot como um processo separado.
            # Se integrado ao FastAPI, o webhook é configurado no FastAPI e
            # os updates são passados para application.update_queue.
        else:
            logger.info('Iniciando bot usando polling')
            await (
                application.initialize()
            )  # Adicionado para inicialização explícita
            await (
                application.start()
            )  # Inicia o polling de forma não-bloqueante
            # application.run_polling(allowed_updates=Update.ALL_TYPES)

    except TelegramError as e:
        logger.error(f'Erro do Telegram ao iniciar bot: {str(e)}')
        sys.exit(1)
    except Exception as e:
        logger.error(f'Erro ao iniciar bot: {str(e)}')
        sys.exit(1)


if __name__ == '__main__':
    iniciar_bot()


def obter_aplicacao() -> Optional[Application]:
    """Retorna a instância da aplicação do bot, se inicializada."""
    return _application
