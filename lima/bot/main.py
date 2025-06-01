"""
Módulo principal do bot Telegram.
Este módulo contém a inicialização e configuração do bot.
"""

import asyncio
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

try:
    from ..settings import Settings  # Importação relativa para uso como módulo
except ImportError:
    from lima.settings import Settings  # Importação absoluta

from .config import (
    LOG_LEVEL,
    SECRET_TOKEN,
    TOKEN_BOT,
    USE_WEBHOOK,
    WEBHOOK_PORT,
    WEBHOOK_URL,
)

# Novos handlers V2
from .handlers import (
    anotacao,
    busca,
    busca_codigo,
    explorar_base,
    menu,
    sugestao,
)
from .handlers.busca_codigo import (
    selecionar_resultado_multiplo_callback,
)
from .handlers.callback import handle_callback
from .handlers.endereco_visualizacao import (
    paginacao_multiplos_callback,
    show_endereco_callback,
    ver_todas_anotacoes_callback,
)

logger = logging.getLogger(__name__)


# Classe para gerenciar a instância da aplicação
class BotManager:
    """Gerenciador da aplicação do bot."""

    def __init__(self):
        self._application: Optional[Application] = None

    def set_application(self, application: Application) -> None:
        """Define a instância da aplicação."""
        self._application = application

    def get_application(self) -> Optional[Application]:
        """Retorna a instância da aplicação."""
        return self._application


# Instância global do gerenciador
_bot_manager = BotManager()


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
    # Adicionar esta linha para ler as configurações
    settings = Settings()
    # Modificar esta linha para usar settings.DEBUG
    nivel_log = (
        logging.DEBUG if settings.DEBUG else getattr(logging, LOG_LEVEL)
    )

    # Configura o logger principal
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        # Modificar esta linha
        level=nivel_log,
    )

    # Configura loggers específicos
    logging.getLogger('httpx').setLevel(logging.WARNING)
    # Adicionado para httpcore
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    # Adicionado para SQLAlchemy
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )  # Alterado para INFO em DEBUG
    logging.getLogger('ptb.dispatcher').setLevel(
        logging.DEBUG if settings.DEBUG else logging.INFO
    )  # Adicionado para logs do dispatcher
    logging.getLogger('telegram.ext.ConversationHandler').setLevel(
        logging.DEBUG if settings.DEBUG else logging.INFO
    )

    # Configurar o logger para lima.bot.handlers
    logging.getLogger('lima.bot.handlers').setLevel(
        logging.DEBUG if settings.DEBUG else logging.INFO
    )


def criar_aplicacao() -> Application:
    """
    Cria e configura a aplicação do bot.

    Returns:
        Aplicação configurada e pronta para uso.
    """
    # Configura logging
    configurar_logging()

    # Verifica token
    if not TOKEN_BOT:
        logger.error(
            'Token do bot não configurado. Configure TOKEN_BOT no arquivo .env'
        )
        sys.exit(1)

    # Cria aplicação sem persistência
    try:
        application = (
            Application.builder()
            .token(TOKEN_BOT)
            .build()
        )
    except Exception as e:
        logger.error(f'Erro ao criar aplicação: {str(e)}')
        sys.exit(1)

    # Armazenar funções para quebrar ciclos de importação
    application.bot_data['exibir_menu_principal_func'] = (
        menu.exibir_menu_principal
    )
    application.bot_data['iniciar_exploracao_func'] = (
        explorar_base.iniciar_exploracao
    )
    # Adicionada iniciar_exploracao_func para consistência, caso menu.py
    # precise dela no futuro ou para outros handlers.

    # Registra o handler de erros
    application.add_error_handler(error_handler)

    # === HANDLERS V2 - BUSCA RÁPIDA POR CÓDIGO ===
    # ConversationHandler para busca rápida por código (deve vir antes do menu)
    application.add_handler(busca_codigo.handler_busca_rapida)

    # === HANDLERS V2 - MENU PRINCIPAL ===
    # Registrar handlers do menu principal
    # (inclui /start, /help, /listar, /cancelar)
    for handler in menu.get_menu_handlers():
        application.add_handler(handler)

    # Comandos diretos de busca por código
    for handler in busca_codigo.get_busca_codigo_handlers():
        application.add_handler(handler)

    # === HANDLERS V2 - EXPLORAÇÃO DA BASE ===
    # ConversationHandler para exploração com filtros
    application.add_handler(
        explorar_base.criar_conversation_handler_exploracao()
    )

    # === HANDLERS DE SUGESTÃO E ANOTAÇÃO
    #  (sempre antes do CallbackQueryHandler genérico) ===
    application.add_handler(sugestao.get_sugestao_conversation())
    application.add_handler(anotacao.get_anotacao_conversation())

    # === CALLBACKQUERYHANDLER DE EXPLORAÇÃO
    #  (se necessário, antes do genérico) ===
    application.add_handler(
        CallbackQueryHandler(
            explorar_base.handle_explorar_callback,
            pattern=r'^(explorar_|voltar_filtros|voltar_resultados|'
            r'executar_busca|limpar_filtros|refazer_busca|'
            r'ver_endereco_|anotar_|filtro_)',
        )
    )

    # === HANDLER PARA VER TODAS AS ANOTAÇÕES DE UM ENDEREÇO ===
    application.add_handler(
        CallbackQueryHandler(
            ver_todas_anotacoes_callback,
            # Usar a função importada diretamente
            pattern=r'^ver_anotacoes_endereco_id_\d+$',
        )
    )

    # === HANDLER PARA VOLTAR AO ENDEREÇO COMPLETO ===
    application.add_handler(
        CallbackQueryHandler(
            show_endereco_callback,  # Usar a função importada diretamente
            pattern=r'^show_endereco_\d+$',
        )
    )

    # === HANDLER GLOBAL PARA CANCELAR BUSCA REMOVIDO ===
    # O cancelar_busca já é tratado pelo ConversationHandler de busca_codigo
    # Remover handler duplicado para evitar conflitos

    # === HANDLER PARA PAGINAÇÃO DE MÚLTIPLOS RESULTADOS ===
    application.add_handler(
        CallbackQueryHandler(
            paginacao_multiplos_callback,
            pattern=r'^multiplos_pagina_(\d+|info)$',
        )
    )

    # === HANDLER PARA SELEÇÃO DE RESULTADO MÚLTIPLO ===
    application.add_handler(
        CallbackQueryHandler(
            selecionar_resultado_multiplo_callback, pattern=r'^select_multi_'
        )
    )

    # === HANDLER GERAL DE CALLBACKS (sempre por último!) ===
    application.add_handler(CallbackQueryHandler(handle_callback))

    # === OUTROS HANDLERS ===
    application.add_handler(
        CommandHandler('anotacoes', anotacao.listar_anotacoes_command)
    )
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
    application.add_handler(
        MessageHandler(filters.LOCATION, busca.receber_localizacao)
    )
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
    _bot_manager.set_application(application)

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

            try:
                # application.run_polling(allowed_updates=Update.ALL_TYPES)
                pass  # Placeholder - polling será iniciado externamente
            finally:
                pass  # Limpeza será feita pela própria persistência

    except TelegramError as e:
        logger.error(f'Erro do Telegram ao iniciar bot: {str(e)}')
        sys.exit(1)
    except Exception as e:
        logger.error(f'Erro ao iniciar bot: {str(e)}')
        sys.exit(1)


if __name__ == '__main__':
    import asyncio

    asyncio.run(iniciar_bot())


def obter_aplicacao() -> Optional[Application]:
    """Retorna a instância da aplicação do bot, se inicializada."""
    return _bot_manager.get_application()
