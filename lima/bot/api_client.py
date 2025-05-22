"""
Cliente HTTP para a API FastAPI.
Este módulo contém funções para fazer requisições à API.
"""

import logging
from typing import Any, Dict, Optional

import httpx

from .config import API_TIMEOUT, API_URL
from .services.auth import get_auth_headers

# Constantes para códigos HTTP
HTTP_OK = 200
HTTP_NO_CONTENT = 204
HTTP_UNAUTHORIZED = 401
HTTP_NOT_FOUND = 404
HTTP_UNPROCESSABLE_ENTITY = 422

logger = logging.getLogger(__name__)


async def fazer_requisicao_get(
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None,  # Adicionado user_id
) -> Any:
    """
    Faz uma requisição GET para a API FastAPI.

    Args:
        endpoint: Caminho do endpoint, sem a URL base.
        params: Parâmetros de query string.
        user_id: ID do usuário do Telegram (opcional).

    Returns:
        Resposta da API em formato JSON.

    Raises:
        Exception: Erro na requisição ou processamento.
    """
    request_url_for_logging = f"{API_URL}/{endpoint}"
    # Para logs de erro antes da requisição real
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            url = f'{API_URL}/{endpoint}'
            request_url_for_logging = url
            # Obtém os headers de autenticação, passando o user_id
            headers = await get_auth_headers(bot_id=user_id)
            # Atualiza com a URL completa
            logger.debug(f'GET {url} com params: {params}')

            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        actual_url_attempted = str(e.request.url)
        response_text = e.response.text
        if e.response.status_code == HTTP_NOT_FOUND:
            logger.warning(
                f"Recurso não encontrado ({HTTP_NOT_FOUND}) na API. URL: {
                    actual_url_attempted}, "
                f"Endpoint: {endpoint}, Params: {params}. Response: {
                    response_text}"
            )
            return None  # Mantém o comportamento original
        elif e.response.status_code == HTTP_UNAUTHORIZED:
            logger.error(
                f"Acesso não autorizado ({HTTP_UNAUTHORIZED}) na API. URL: {
                    actual_url_attempted}, "
                f"Endpoint: {endpoint}. Response: {response_text}"
            )
            # Mantendo PermissionError para consistência com
            #  o código original, se aplicável.
            raise PermissionError(f"Acesso não autorizado para {
                actual_url_attempted}")
        else:
            logger.error(
                f"Erro HTTP {e.response.status_code} na API. URL: {
                    actual_url_attempted}, "
                f"Endpoint: {endpoint}. Response: {response_text}"
            )
            raise  # Re-levanta a exceção original para manter o rastreamento
    except httpx.RequestError as e:
        # e.request.url pode não estar disponível se a
        #  requisição falhou muito cedo
        url_info = str(e.request.url) if hasattr(
            e, 'request') and hasattr(
                e.request, 'url') else request_url_for_logging
        logger.error(
            f"Erro de requisição (ex: conexão, timeout) ao tentar GET. "
            f"URL/Endpoint: {url_info}. Erro: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado durante GET para {
            request_url_for_logging}. Erro: {str(e)}")
        raise


async def fazer_requisicao_post(
    endpoint: str, data: Dict[str, Any], user_id: Optional[int] = None
        # Adicionado user_id
) -> Any:
    """
    Faz uma requisição POST para a API FastAPI.

    Args:
        endpoint: Caminho do endpoint, sem a URL base.
        data: Dados a serem enviados no corpo da requisição.
        user_id: ID do usuário do Telegram (opcional).

    Returns:
        Resposta da API em formato JSON.

    Raises:
        Exception: Erro na requisição ou processamento.
    """
    request_url_for_logging = f"{API_URL}/{endpoint}"
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            url = f'{API_URL}/{endpoint}'
            request_url_for_logging = url
            # Obtém os headers de autenticação, passando o user_id
            headers = await get_auth_headers(bot_id=user_id)
            logger.debug(f'POST {url} com dados: {data} e headers: {headers}')
            response = await client.post(url, json=data, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        actual_url_attempted = str(e.request.url)
        response_text = e.response.text
        logger.error(
            f"Erro HTTP {e.response.status_code} na API durante POST. URL: {
                actual_url_attempted}, "
            f"Endpoint: {endpoint}. Data: {data}. Response: {response_text}"
        )
        # Tratar códigos específicos como 401, 404, 422 se necessário
        if e.response.status_code == HTTP_UNPROCESSABLE_ENTITY:
            logger.error(
                f"Erro de validação ({HTTP_UNPROCESSABLE_ENTITY}) POST para "
                f"{actual_url_attempted}. Detalhes: {response_text}"
            )
        raise
    except httpx.RequestError as e:
        url_info = str(e.request.url) if hasattr(e, 'request') and hasattr(
            e.request, 'url') else request_url_for_logging
        logger.error(
            f"Erro de requisição (ex: conexão, timeout) ao tentar POST. "
            f"URL/Endpoint: {url_info}. Data: {data}. Erro: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado durante POST para {
            request_url_for_logging}. Data: {data}. Erro: {str(e)}")
        raise


async def fazer_requisicao_put(
    endpoint: str, data: Dict[str, Any], user_id: Optional[int] = None
        # Adicionado user_id
) -> Any:
    """
    Faz uma requisição PUT para a API FastAPI.

    Args:
        endpoint: Caminho do endpoint, sem a URL base.
        data: Dados a serem enviados no corpo da requisição.
        user_id: ID do usuário do Telegram (opcional).

    Returns:
        Resposta da API em formato JSON.

    Raises:
        Exception: Erro na requisição ou processamento.
    """
    request_url_for_logging = f"{API_URL}/{endpoint}"
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            url = f'{API_URL}/{endpoint}'
            request_url_for_logging = url
            # Obtém os headers de autenticação, passando o user_id
            headers = await get_auth_headers(bot_id=user_id)
            logger.debug(f'PUT {url} com dados: {data} e headers: {headers}')
            response = await client.put(url, json=data, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        actual_url_attempted = str(e.request.url)
        response_text = e.response.text
        logger.error(
            f"Erro HTTP {e.response.status_code} na API durante PUT. URL: {
                actual_url_attempted}, "
            f"Endpoint: {endpoint}. Data: {data}. Response: {response_text}"
        )
        if e.response.status_code == HTTP_UNPROCESSABLE_ENTITY:
            logger.error(
                f"Erro de validação ({HTTP_UNPROCESSABLE_ENTITY}) PUT para {
                    actual_url_attempted}. Detalhes: {response_text}"
            )
        raise
    except httpx.RequestError as e:
        url_info = str(e.request.url) if hasattr(e, 'request') and hasattr(
            e.request, 'url') else request_url_for_logging
        logger.error(
            f"Erro de requisição (ex:conexão, timeout) ao tentar PUT."
            f" URL/Endpoint: {url_info}. Data: {data}. Erro: {str(e)}"
        )
        raise
    except Exception as e:
        logger.error(
            f"Erro inesperado durante PUT para {request_url_for_logging}. "
            f"Data: {data}. Erro: {str(e)}"
        )
        raise


async def fazer_requisicao_delete(
    endpoint: str, user_id: Optional[int] = None  # Adicionado user_id
) -> Any:
    """
    Faz uma requisição DELETE para a API FastAPI.

    Args:
        endpoint: Caminho do endpoint, sem a URL base.
        user_id: ID do usuário do Telegram (opcional).

    Returns:
        Resposta da API em formato JSON, se houver.

    Raises:
        Exception: Erro na requisição ou processamento.
    """
    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        try:
            url = f'{API_URL}/{endpoint}'
            # Obtém os headers de autenticação, passando o user_id
            headers = await get_auth_headers(bot_id=user_id)
            logger.debug(f'DELETE {url} com headers: {headers}')

            response = await client.delete(url, headers=headers)
            response.raise_for_status()

            if response.status_code == HTTP_NO_CONTENT:  # No content
                return None
            return response.json()
        except httpx.HTTPStatusError as e:
            # Tratamento específico por código de status
            if e.response.status_code == HTTP_NOT_FOUND:
                logger.warning(f'Recurso não encontrado: {endpoint}')
                return None
            elif e.response.status_code == HTTP_UNAUTHORIZED:
                logger.error(f'Acesso não autorizado: {endpoint}')
                raise PermissionError('Acesso não autorizado')
            else:
                logger.error(
                    f'Erro HTTP {e.response.status_code}: {str(e)}'
                )
                raise Exception(f'Erro na API: {str(e)}')
        except Exception as e:
            logger.error(f'Erro desconhecido: {str(e)}')
            raise Exception(f'Erro desconhecido: {str(e)}')
