"""
Módulo para integração com serviços de IA (OpenAI/Gemini).
Este módulo contém funções para envio de prompts e recebimento de respostas
dos serviços de IA para formatar mensagens humanizadas.
"""
import logging
import json
from typing import Dict, Any, Optional, List

import httpx

from ..settings import Settings

settings = Settings()
logger = logging.getLogger(__name__)

# Configurações padrão para os modelos de IA
DEFAULT_MODEL = "gpt-3.5-turbo"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 300
DEFAULT_TIMEOUT = 30.0  # segundos


class AIServiceError(Exception):
    """Exceção para erros relacionados ao serviço de IA"""
    pass


async def format_endereco_resposta(endereco: Dict[str, Any]) -> str:
    """
    Utiliza IA para formatar uma resposta humanizada para um endereço encontrado.
    
    Args:
        endereco: Dicionário com dados do endereço
        
    Returns:
        str: Texto formatado de forma humanizada
    """
    # Constrói um prompt baseado no endereço
    prompt = f"""
    Formate o seguinte endereço de forma humanizada e amigável, 
    como se estivesse ajudando alguém a encontrar este local:
    
    Logradouro: {endereco.get('logradouro', 'Não informado')}
    Número: {endereco.get('numero', 'Não informado')}
    Bairro: {endereco.get('bairro', 'Não informado')}
    Cidade: {endereco.get('municipio', 'Não informado')}
    UF: {endereco.get('uf', 'Não informado')}
    CEP: {endereco.get('cep', 'Não informado')}
    
    Inclua informações sobre como esse endereço está registrado em nosso sistema.
    Seja conciso mas amigável, como se estivesse conversando por WhatsApp.
    """
    
    # Se existir coordenadas, adicione ao prompt
    if endereco.get('latitude') and endereco.get('longitude'):
        prompt += f"\nObservação: Este endereço tem coordenadas geográficas registradas: {endereco.get('latitude')}, {endereco.get('longitude')}."
    
    # Use o serviço de IA para formatar a resposta
    try:
        response_text = await query_openai(prompt)
        return response_text
    except AIServiceError as e:
        logger.warning(f"Falha ao usar IA para formatar resposta: {e}")
        
        # Fallback para resposta formatada manualmente
        return (
            f"🏠 *Endereço encontrado*\n\n"
            f"*Logradouro:* {endereco.get('logradouro', 'Não informado')}, "
            f"{endereco.get('numero', 'S/N')}\n"
            f"*Bairro:* {endereco.get('bairro', 'Não informado')}\n"
            f"*Cidade:* {endereco.get('municipio', 'Não informado')}\n"
            f"*UF:* {endereco.get('uf', 'Não informado')}\n"
            f"*CEP:* {endereco.get('cep', 'Não informado')}\n\n"
            f"Para sugerir alterações neste endereço, use o comando 'sugerir'."
        )


async def format_sugestao_resposta(sugestao: Dict[str, Any]) -> str:
    """
    Utiliza IA para formatar uma resposta humanizada para confirmar o recebimento de uma sugestão.
    
    Args:
        sugestao: Dicionário com dados da sugestão
        
    Returns:
        str: Texto formatado de forma humanizada
    """
    # Constrói um prompt baseado na sugestão
    prompt = f"""
    Formate uma mensagem amigável confirmando o recebimento da sugestão abaixo.
    Agradeça ao usuário pela contribuição e explique que a sugestão será analisada.
    
    Tipo de sugestão: {sugestao.get('tipo_sugestao', 'Não informado')}
    Detalhes: {sugestao.get('detalhe', 'Não informado')}
    
    Seja conciso mas amigável, como se estivesse conversando por WhatsApp.
    """
    
    # Use o serviço de IA para formatar a resposta
    try:
        response_text = await query_openai(prompt)
        return response_text
    except AIServiceError as e:
        logger.warning(f"Falha ao usar IA para formatar resposta: {e}")
        
        # Fallback para resposta formatada manualmente
        return (
            f"✅ *Sugestão registrada com sucesso!*\n\n"
            f"Sua sugestão será analisada por nossa equipe e você receberá uma notificação "
            f"quando for processada.\n\n"
            f"*Conteúdo da sugestão:*\n{sugestao.get('detalhe', 'Não informado')}\n\n"
            f"Agradecemos sua contribuição para mantermos nossa base de dados atualizada!"
        )


async def query_openai(
    prompt: str, 
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS
) -> str:
    """
    Envia uma consulta para a API da OpenAI e retorna a resposta.
    
    Args:
        prompt: O texto do prompt a ser enviado
        model: O modelo da OpenAI a ser usado
        temperature: Controle de aleatoriedade (0.0-2.0)
        max_tokens: Número máximo de tokens na resposta
        
    Returns:
        str: Texto da resposta da IA
        
    Raises:
        AIServiceError: Se ocorrer um erro na chamada da API
    """
    # Verifica se a chave da API está configurada
    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        raise AIServiceError("Chave da API da OpenAI não configurada")
        
    # Prepara os dados da requisição
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Você é um assistente útil que formata respostas de forma humanizada e amigável para um sistema de busca de endereços via WhatsApp."},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, 
                headers=headers, 
                json=payload,
                timeout=DEFAULT_TIMEOUT
            )
            response.raise_for_status()
            result = response.json()
            
            # Extrai o texto da resposta
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"].strip()
            else:
                raise AIServiceError("Formato de resposta inválido da OpenAI")
    except httpx.HTTPStatusError as e:
        logger.error(f"Erro de API da OpenAI: {e.response.text}")
        raise AIServiceError(f"Erro da API da OpenAI: {e.response.status_code}")
    except httpx.RequestError as e:
        logger.error(f"Erro de requisição para OpenAI: {str(e)}")
        raise AIServiceError(f"Erro de conexão com a API da OpenAI: {str(e)}")
    except Exception as e:
        logger.error(f"Erro inesperado ao chamar a API da OpenAI: {str(e)}")
        raise AIServiceError(f"Erro ao processar resposta da OpenAI: {str(e)}")


async def query_gemini(
    prompt: str,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS
) -> str:
    """
    Envia uma consulta para a API do Gemini (Google) e retorna a resposta.
    Implementação alternativa que pode ser usada em vez da OpenAI.
    
    Args:
        prompt: O texto do prompt a ser enviado
        temperature: Controle de aleatoriedade (0.0-1.0)
        max_tokens: Número máximo de tokens na resposta
        
    Returns:
        str: Texto da resposta da IA
        
    Raises:
        AIServiceError: Se ocorrer um erro na chamada da API
    """
    # Verifica se a chave da API está configurada
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        raise AIServiceError("Chave da API do Gemini não configurada")
        
    # API do Gemini
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={api_key}"
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "topP": 0.95,
            "topK": 40
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, 
                headers=headers, 
                json=payload,
                timeout=DEFAULT_TIMEOUT
            )
            response.raise_for_status()
            result = response.json()
            
            # Extrai o texto da resposta (formato específico do Gemini)
            if "candidates" in result and len(result["candidates"]) > 0:
                candidate = result["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if parts and "text" in parts[0]:
                        return parts[0]["text"].strip()
                        
            # Se chegou aqui, não conseguiu extrair a resposta
            raise AIServiceError("Formato de resposta inválido do Gemini")
    except httpx.HTTPStatusError as e:
        logger.error(f"Erro de API do Gemini: {e.response.text}")
        raise AIServiceError(f"Erro da API do Gemini: {e.response.status_code}")
    except httpx.RequestError as e:
        logger.error(f"Erro de requisição para Gemini: {str(e)}")
        raise AIServiceError(f"Erro de conexão com a API do Gemini: {str(e)}")
    except Exception as e:
        logger.error(f"Erro inesperado ao chamar a API do Gemini: {str(e)}")
        raise AIServiceError(f"Erro ao processar resposta do Gemini: {str(e)}")