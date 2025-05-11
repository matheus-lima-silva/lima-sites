"""
Módulo para integração com serviços de IA (OpenAI/Gemini).
Este módulo está temporariamente desativado e retorna respostas padrão.
"""

import logging
from typing import Any, Dict

# Removida a importação que estava causando o erro
# import google.generativeai as genai
from ..settings import Settings

settings = Settings()
logger = logging.getLogger(__name__)

# Configurações padrão para os modelos de IA
DEFAULT_MODEL = 'gpt-3.5-turbo'
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 300
DEFAULT_TIMEOUT = 30.0  # segundos


class AIServiceError(Exception):
    """Exceção para erros relacionados ao serviço de IA"""
    pass


async def format_endereco_resposta(endereco: Dict[str, Any]) -> str:
    """
    Versão simplificada que retorna uma mensagem formatada padrão.

    Args:
        endereco: Dicionário com dados do endereço

    Returns:
        str: Texto formatado de forma padrão
    """
    # Resposta formatada manualmente sem usar IA
    return (
        f'🏠 *Endereço encontrado*\n\n'
        f'*Logradouro:* {endereco.get("logradouro", "Não informado")}, '
        f'{endereco.get("numero", "S/N")}\n'
        f'*Bairro:* {endereco.get("bairro", "Não informado")}\n'
        f'*Cidade:* {endereco.get("municipio", "Não informado")}\n'
        f'*UF:* {endereco.get("uf", "Não informado")}\n'
        f'*CEP:* {endereco.get("cep", "Não informado")}\n\n'
        f"Para sugerir alterações neste endereço, use o comando 'sugerir'."
    )


async def format_sugestao_resposta(sugestao: Dict[str, Any]) -> str:
    """
    Versão simplificada que retorna uma mensagem formatada padrão.

    Args:
        sugestao: Dicionário com dados da sugestão

    Returns:
        str: Texto formatado de forma padrão
    """
    # Resposta formatada manualmente sem usar IA
    return (
        f'✅ *Sugestão registrada com sucesso!*\n\n'
        f'Sua sugestão será analisada por nossa equipe '
        f'e você receberá uma notificação '
        f'quando for processada.\n\n'
        f'*Conteúdo da sugestão:*\n{
        sugestao.get(
        "detalhe", "Não informado")}\n\n'
f'Agradecemos sua contribuição para mantermos nossa base de dados atualizada!'
    )


async def query_openai(
    prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    """
    Versão simplificada que retorna uma mensagem padrão.

    Args:
        prompt: O texto do prompt a ser enviado
        model: O modelo da OpenAI a ser usado
        temperature: Controle de aleatoriedade (0.0-2.0)
        max_tokens: Número máximo de tokens na resposta

    Returns:
        str: Texto padrão informando que o serviço está desativado
    """
    logger.info(
    "Serviço de IA está temporariamente desativado. Usando resposta padrão.")
    return ("O serviço de processamento inteligente está temporariamente"
    " desativado. "
            "Por favor, tente novamente mais tarde.")


async def query_gemini(
    prompt: str,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    """
    Versão simplificada que retorna uma mensagem padrão.

    Args:
        prompt: O texto do prompt a ser enviado
        temperature: Controle de aleatoriedade (0.0-1.0)
        max_tokens: Número máximo de tokens na resposta

    Returns:
        str: Texto padrão informando que o serviço está desativado
    """
    logger.info(
    "Serviço de IA está temporariamente desativado. Usando resposta padrão.")
    return "O serviço de processamento inteligente está temporariamente"
    " desativado. Por favor, tente novamente mais tarde."


async def generate_ai_response(prompt: str) -> str:
    """
    Versão simplificada que retorna uma mensagem padrão.

    Args:
        prompt: O texto do prompt enviado pelo usuário

    Returns:
        str: Texto padrão informando que o serviço está desativado
    """
    logger.info(
    "Serviço de IA está temporariamente desativado. Usando resposta padrão.")
    return (
    "O serviço de processamento inteligente está temporariamente desativado. "
            "Por favor, tente novamente mais tarde.")


async def process_address_request(query: str, user_id: int) -> str:
    """
    Versão simplificada que retorna uma mensagem padrão.

    Args:
        query: A consulta do usuário sobre endereços
        user_id: ID do usuário que fez a solicitação

    Returns:
        str: Texto padrão informando que o serviço está desativado
    """
    logger.info(
    f"Solicitação de endereço recebida do usuário {
        user_id}: '{query}'. Usando resposta padrão.")
    return (
        "Desculpe, o processamento inteligente de solicitações está "
        "temporariamente desativado. "
        "Por favor, tente usar os comandos específicos do sistema para buscar "
        "endereços."
    )
