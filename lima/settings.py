"""
Módulo de configurações do sistema.

Este módulo carrega e disponibiliza todas as configurações
necessárias para a aplicação.
As configurações são carregadas das variáveis de ambiente
definidas no arquivo .env.
"""

from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Classe de configurações para uso com FastAPI e outros componentes.

    Esta classe centraliza todas as configurações da aplicação, carregando-as
    automaticamente de variáveis de ambiente e/ou de um arquivo .env.
    """

    # Configurações de Banco de Dados
    DATABASE_URL: str = (
        'postgresql+asyncpg://postgres:postgres@localhost:5432/lima_db'
    )

    # Configurações de Segurança
    SECRET_KEY: str = 'changeme'
    DEBUG: bool = False
    ACCESS_TOKEN_EXPIRE_DAYS: int = 30

    # Configurações do WhatsApp
    WHATSAPP_API_VERSION: str = 'v17.0'
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_BUSINESS_ACCOUNT_ID: Optional[str] = None
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    WHATSAPP_VERIFY_TOKEN: str = 'lima-whatsapp-token'
    WHATSAPP_APP_SECRET: Optional[str] = None
    WHATSAPP_WEBHOOK_URL: Optional[str] = None

    # Configurações de IA
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = 'gpt-3.5-turbo'
    GEMINI_API_KEY: Optional[str] = None
    AI_SERVICE: Literal['openai', 'gemini', 'none'] = 'none'

    model_config = SettingsConfigDict(
        env_file='.env',  # Especifica o arquivo .env a ser carregado
        env_file_encoding='utf-8',
        # Ignora variáveis de ambiente extras não definidas na classe
        extra='ignore',
    )

    @property
    def whatsapp_configured(self) -> bool:
        """
        Verifica se todas as configurações obrigatórias do WhatsApp
        foram definidas.

        Returns:
            bool: True se todas as configurações obrigatórias do WhatsApp
                  estiverem definidas.
        """
        return all([self.WHATSAPP_PHONE_NUMBER_ID, self.WHATSAPP_ACCESS_TOKEN])

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
        if self.AI_SERVICE == 'openai':
            return self.openai_configured
        elif self.AI_SERVICE == 'gemini':
            return self.gemini_configured
        return False


# Instância única das configurações para ser usada na aplicação
settings = Settings()
