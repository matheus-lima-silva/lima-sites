"""
Configurações do Bot Telegram.
Este módulo contém as configurações necessárias para o funcionamento do bot.
"""

import os

from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env, se existir
load_dotenv()

# Configurações do Bot
TOKEN_BOT = os.getenv('TELEGRAM_BOT_TOKEN', '')
WEBHOOK_URL = os.getenv('TELEGRAM_WEBHOOK_URL', '')
SECRET_TOKEN = os.getenv('TELEGRAM_SECRET_TOKEN', '')
USE_WEBHOOK = os.getenv('USE_WEBHOOK', 'False').lower() == 'true'
WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', '8443'))
# ID do bot no Telegram para autenticação na API
BOT_TELEGRAM_ID = int(os.getenv('BOT_TELEGRAM_ID', '0'))

# Configurações da API
API_URL = os.getenv('API_URL', 'http://localhost:8000')
API_TIMEOUT = int(os.getenv('API_TIMEOUT', '30'))  # Timeout em segundos

# Token de acesso para a API
# Pode ser definido diretamente ou obtido via autenticação
API_ACCESS_TOKEN = os.getenv('BOT_API_ACCESS_TOKEN', '')

# Configurações de log
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Configurações de paginação
ITENS_POR_PAGINA = int(os.getenv('ITENS_POR_PAGINA', '5'))
