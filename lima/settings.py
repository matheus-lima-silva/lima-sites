"""
Módulo de configurações do sistema.

Este módulo carrega e disponibiliza todas as configurações necessárias para a aplicação.
As configurações são carregadas das variáveis de ambiente definidas no arquivo .env.
"""
import os
from typing import Optional, Literal

from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()

# Configurações do Banco de Dados
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./dev.db")

# Configurações de Segurança
SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Configurações de segurança para tokens JWT
ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", "30"))

# Configurações do WhatsApp Cloud API
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v17.0")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_BUSINESS_ACCOUNT_ID = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "lima-whatsapp-token")
WHATSAPP_APP_SECRET = os.getenv("WHATSAPP_APP_SECRET")
WHATSAPP_WEBHOOK_URL = os.getenv("WHATSAPP_WEBHOOK_URL")

# Configurações de Serviços de IA
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
AI_SERVICE = os.getenv("AI_SERVICE", "none")  # opções: openai, gemini, none


class Settings:
    """
    Classe de configurações para uso com FastAPI e outros componentes.
    
    Esta classe centraliza todas as configurações da aplicação, facilitando
    o acesso a elas por meio de injeção de dependências.
    """
    # Configurações de Banco de Dados
    DATABASE_URL: str = DATABASE_URL
    
    # Configurações de Segurança
    SECRET_KEY: str = SECRET_KEY
    DEBUG: bool = DEBUG
    ACCESS_TOKEN_EXPIRE_DAYS: int = ACCESS_TOKEN_EXPIRE_DAYS
    
    # Configurações do WhatsApp
    WHATSAPP_API_VERSION: str = WHATSAPP_API_VERSION
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = WHATSAPP_PHONE_NUMBER_ID
    WHATSAPP_BUSINESS_ACCOUNT_ID: Optional[str] = WHATSAPP_BUSINESS_ACCOUNT_ID
    WHATSAPP_ACCESS_TOKEN: Optional[str] = WHATSAPP_ACCESS_TOKEN
    WHATSAPP_VERIFY_TOKEN: str = WHATSAPP_VERIFY_TOKEN
    WHATSAPP_APP_SECRET: Optional[str] = WHATSAPP_APP_SECRET
    WHATSAPP_WEBHOOK_URL: Optional[str] = WHATSAPP_WEBHOOK_URL
    
    # Configurações de IA
    OPENAI_API_KEY: Optional[str] = OPENAI_API_KEY
    OPENAI_MODEL: str = OPENAI_MODEL
    GEMINI_API_KEY: Optional[str] = GEMINI_API_KEY
    AI_SERVICE: str = AI_SERVICE
    
    @property
    def whatsapp_configured(self) -> bool:
        """
        Verifica se todas as configurações obrigatórias do WhatsApp foram definidas.
        
        Returns:
            bool: True se todas as configurações obrigatórias do WhatsApp estiverem definidas.
        """
        return all([
            self.WHATSAPP_PHONE_NUMBER_ID,
            self.WHATSAPP_ACCESS_TOKEN
        ])
    
    @property
    def openai_configured(self) -> bool:
        """
        Verifica se a API da OpenAI está configurada.
        
        Returns:
            bool: True se a API da OpenAI estiver configurada.
        """
        return bool(self.OPENAI_API_KEY)
    
    @property
    def gemini_configured(self) -> bool:
        """
        Verifica se a API do Gemini está configurada.
        
        Returns:
            bool: True se a API do Gemini estiver configurada.
        """
        return bool(self.GEMINI_API_KEY)
    
    @property
    def ai_service_enabled(self) -> bool:
        """
        Verifica se algum serviço de IA está habilitado e configurado.
        
        Returns:
            bool: True se algum serviço de IA estiver habilitado e configurado.
        """
        if self.AI_SERVICE.lower() == "openai":
            return self.openai_configured
        elif self.AI_SERVICE.lower() == "gemini":
            return self.gemini_configured
        return False
