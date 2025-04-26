"""
Módulo de configurações do sistema (raiz do projeto).

Este módulo importa e disponibiliza as configurações definidas no pacote principal.
As configurações são carregadas das variáveis de ambiente definidas no arquivo .env.
"""
from lima.settings import (
    ACCESS_TOKEN_EXPIRE_DAYS,
    DATABASE_URL,
    DEBUG,
    SECRET_KEY,
    WHATSAPP_ACCESS_TOKEN,
    WHATSAPP_API_VERSION,
    WHATSAPP_APP_SECRET,
    WHATSAPP_BUSINESS_ACCOUNT_ID,
    WHATSAPP_PHONE_NUMBER_ID,
    WHATSAPP_VERIFY_TOKEN,
    WHATSAPP_WEBHOOK_URL,
    Settings,
    load_dotenv,
)

# Classe de configurações para uso com FastAPI, etc.
__all__ = [
    'load_dotenv',
    'DATABASE_URL',
    'SECRET_KEY',
    'DEBUG',
    'ACCESS_TOKEN_EXPIRE_DAYS',
    'WHATSAPP_API_VERSION',
    'WHATSAPP_PHONE_NUMBER_ID',
    'WHATSAPP_BUSINESS_ACCOUNT_ID',
    'WHATSAPP_ACCESS_TOKEN',
    'WHATSAPP_VERIFY_TOKEN',
    'WHATSAPP_APP_SECRET',
    'WHATSAPP_WEBHOOK_URL',
    'Settings'
]
