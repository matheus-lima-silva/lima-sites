"""
Cliente HTTP para comunicação com a API do Lima Bot.

Este módulo contém funções para fazer requisições à API.
"""

import logging
from typing import Any, Dict, Optional

import httpx

from .config import API_TIMEOUT, API_URL
from .services.token_service import token_manager

# Constantes para códigos HTTP
HTTP_OK = 200
HTTP_NO_CONTENT = 204
HTTP_UNAUTHORIZED = 401
HTTP_NOT_FOUND = 404
HTTP_UNPROCESSABLE_ENTITY = 422

logger = logging.getLogger(__name__)


async def _obter_token_jwt(
    bot_id: Optional[int] = None, user_name: Optional[str] = None
) -> Optional[str]:
    """
    Obtém um token JWT válido para autenticação com a API.

    Args:
        bot_id: ID do usuário do Telegram
        user_name: Nome do usuário

    Returns:
        Token JWT ou None se não conseguir obter
    """
    if not bot_id:
        logger.warning('Bot ID não fornecido para obter token JWT')
        return None

    try:
        # Tenta obter token JWT da API
        token = await token_manager.obter_token_api(bot_id, user_name)
        if token:
            logger.debug(f'Token JWT obtido com sucesso para bot_id {bot_id}')
            return token
        else:
            logger.warning(f'Falha ao obter token JWT para bot_id {bot_id}')
            return None

    except Exception as e:
        logger.error(f'Erro ao obter token JWT: {e}')
        return None


async def get_auth_headers(
    bot_id: Optional[int] = None,
    user_name: Optional[str] = None,
    expected_phone: Optional[str] = None,
) -> Dict[str, str]:
    """
    Obtém os cabeçalhos de autenticação para requisições à API.

    Args:
        bot_id: ID do bot no Telegram (opcional,
          usa um valor padrão se não informado).
        user_name: Nome do usuário (opcional, para X-User-Name).
        expected_phone: Telefone esperado (opcional, para X-Expected-Phone).

    Returns:
        Cabeçalhos de autenticação.
    """
    logger.info(
        f'DEBUG: get_auth_headers recebeu: bot_id={bot_id}, '
        f'user_name={user_name}, expected_phone={expected_phone}'
    )
    headers = {}

    # Tenta obter token JWT se bot_id for fornecido
    token = await _obter_token_jwt(bot_id, user_name)
    if token:
        headers['Authorization'] = f'Bearer {token}'
    else:
        logger.warning(
            'Nenhum token JWT obtido. Requisição seguirá sem token Bearer, '
            'apenas com headers X-* (se disponíveis).'
        )

    # Garante que os cabeçalhos X-* sejam adicionados se os dados
    #  estiverem disponíveis.
    # X-User-Name usará um placeholder se user_name
    #  não for fornecido mas bot_id sim.
    actual_user_name_for_header = user_name
    if not actual_user_name_for_header and bot_id:
        # Sem acento para evitar problemas de encoding
        actual_user_name_for_header = f'Usuario {bot_id}'
        logger.debug(
            f"user_name não fornecido, usando placeholder: '{
                actual_user_name_for_header
            }'"
        )

    if bot_id:
        headers['X-Telegram-User-Id'] = str(bot_id)
    if actual_user_name_for_header:  # Usa o nome original ou o placeholder
        # Garante que o nome do usuário seja seguro para headers HTTP
        safe_name = actual_user_name_for_header.encode(
            'ascii', errors='ignore'
        ).decode('ascii')
        # Se não sobrou nada após remover caracteres não-ASCII
        if not safe_name.strip():
            safe_name = f'Usuario {bot_id}' if bot_id else 'Usuario'
        headers['X-User-Name'] = safe_name
    if expected_phone:
        headers['X-Expected-Phone'] = expected_phone

    has_bearer = 'Authorization' in headers
    # Verifica se todos os cabeçalhos X-* necessários estão presentes
    has_all_x_headers = (
        'X-Telegram-User-Id' in headers
        and 'X-User-Name' in headers
        and 'X-Expected-Phone' in headers
    )

    if not has_bearer and not has_all_x_headers:
        logger.warning(
            'A requisição não possui token Bearer nem o conjunto completo de '
            'cabeçalhos X- (X-Telegram-User-Id, X-User-Name, '
            'X-Expected-Phone). Isso pode ser problemático para endpoints '
            'que exigem um desses esquemas de autenticação/identificação.'
        )
    elif not has_all_x_headers and _endpoint_requires_x_headers(
        expected_phone
    ):
        logger.warning(
            'A requisição pode ter um token Bearer, mas não o conjunto '
            'completo de cabeçalhos X- (X-Telegram-User-Id, X-User-Name, '
            'X-Expected-Phone), que podem ser necessários para este endpoint.'
        )

    logger.info(f'DEBUG: Cabeçalhos finais gerados: {headers}')
    return headers


def _endpoint_requires_x_headers(expected_phone: Optional[str]) -> bool:
    """
    Heurística para determinar se um endpoint provavelmente requer X-Headers.
    """
    return expected_phone is not None


async def fazer_requisicao_get(
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,  # Adicionado user_name
    expected_phone: Optional[str] = None,  # Adicionado expected_phone
) -> Any:
    """
    Faz uma requisição GET para a API FastAPI.

    Args:
        endpoint: Caminho do endpoint, sem a URL base.
        params: Parâmetros de query string.
        user_id: ID do usuário do Telegram (opcional).
        user_name: Nome do usuário (opcional, para X-User-Name).
        expected_phone: Telefone esperado (opcional, para X-Expected-Phone).

    Returns:
        Resposta da API em formato JSON.

    Raises:
        Exception: Erro na requisição ou processamento.
        PermissionError: Para erros de autorização (401).
        ConnectionError: Para erros de comunicação com a API.
    """
    request_url_for_logging = f'{API_URL}/{endpoint}'
    # Para logs de erro antes da requisição real
    logger.info(
        f'DEBUG: fazer_requisicao_get chamado com: user_id={user_id}, '
        f'user_name={user_name}, expected_phone={expected_phone}'
    )
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            url = f'{API_URL}/{endpoint}'
            # request_url_for_logging = url  # Removido, não usado após aqui
            # Obtém os headers de autenticação, passando o user_id
            headers = await get_auth_headers(
                bot_id=user_id,
                user_name=user_name,
                expected_phone=expected_phone,
            )
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
                f'Recurso não encontrado ({HTTP_NOT_FOUND}) na API. URL: {
                    actual_url_attempted
                }, '
                f'Endpoint: {endpoint}, Params: {params}. Response: {
                    response_text
                }'
            )
            return None  # Mantém o comportamento original
        elif e.response.status_code == HTTP_UNAUTHORIZED:
            logger.error(
                f'Acesso não autorizado ({HTTP_UNAUTHORIZED}) na API. URL: {
                    actual_url_attempted
                }, '
                f'Endpoint: {endpoint}. Response: {response_text}'
            )
            raise PermissionError(
                f'Acesso não autorizado para {actual_url_attempted}'
            )
        else:
            error_detail = response_text  # Default
            try:
                error_json = e.response.json()
                if 'detail' in error_json:
                    error_detail = error_json['detail']
                    if isinstance(error_detail, list):
                        # Se 'detail' é lista (comum em erros Pydantic),
                        # formata para string legível.
                        error_detail = '; '.join(
                            str(item) for item in error_detail
                        )
            except ValueError:  # Não é JSON ou não tem 'detail'
                pass
            logger.error(
                f'Erro HTTP {e.response.status_code} na API. URL: {
                    actual_url_attempted
                }, '
                f'Endpoint: {endpoint}. Detalhe: {error_detail}'
            )
            raise Exception(
                f'Erro da API ({e.response.status_code}): {error_detail}'
            )
    except httpx.RequestError as e:
        # e.request.url pode não estar disponível se a
        #  requisição falhou muito cedo
        url_info = (
            str(e.request.url)
            if hasattr(e, 'request') and hasattr(e.request, 'url')
            else request_url_for_logging
        )
        logger.error(
            f'Erro de requisição (ex: conexão, timeout) ao tentar GET. '
            f'URL/Endpoint: {url_info}. Erro: {str(e)}'
        )
        raise ConnectionError(f'Falha de comunicação com o servidor: {str(e)}')
    except Exception as e:
        logger.error(
            f'Erro inesperado durante GET para {
                request_url_for_logging
            }. Erro: {str(e)}'
        )
        raise


async def fazer_requisicao_post(
    endpoint: str,
    data: Dict[str, Any],
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,  # Adicionado user_name
    expected_phone: Optional[str] = None,  # Adicionado expected_phone
) -> Any:
    """
    Faz uma requisição POST para a API FastAPI.

    Args:
        endpoint: Caminho do endpoint, sem a URL base.
        data: Dados a serem enviados no corpo da requisição.
        user_id: ID do usuário do Telegram (opcional).
        user_name: Nome do usuário (opcional, para X-User-Name).
        expected_phone: Telefone esperado (opcional, para X-Expected-Phone).

    Returns:
        Resposta da API em formato JSON.

    Raises:
        Exception: Erro na requisição ou processamento.
    """
    request_url_for_logging = f'{API_URL}/{endpoint}'
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            url = f'{API_URL}/{endpoint}'
            # request_url_for_logging = url  # Removido
            headers = await get_auth_headers(
                bot_id=user_id,
                user_name=user_name,
                expected_phone=expected_phone,
            )
            logger.debug(f'POST {url} com dados: {data} e headers: {headers}')
            response = await client.post(url, json=data, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        actual_url_attempted = str(e.request.url)
        response_text = e.response.text
        logger.error(
            f'Erro HTTP {e.response.status_code} na API durante POST. URL: {
                actual_url_attempted
            }, '
            f'Endpoint: {endpoint}. Data: {data}. Response: {response_text}'
        )
        # Tratar códigos específicos como 401, 404, 422 se necessário
        if e.response.status_code == HTTP_UNPROCESSABLE_ENTITY:
            logger.error(
                f'Erro de validação ({HTTP_UNPROCESSABLE_ENTITY}) POST para '
                f'{actual_url_attempted}. Detalhes: {response_text}'
            )
        raise
    except httpx.RequestError as e:
        url_info = (
            str(e.request.url)
            if hasattr(e, 'request') and hasattr(e.request, 'url')
            else request_url_for_logging
        )
        logger.error(
            f'Erro de requisição (ex: conexão, timeout) ao tentar POST. '
            f'URL/Endpoint: {url_info}. Data: {data}. Erro: {str(e)}'
        )
        raise
    except Exception as e:
        logger.error(
            f'Erro inesperado durante POST para {
                request_url_for_logging
            }. Data: {data}. Erro: {str(e)}'
        )
        raise


async def fazer_requisicao_put(
    endpoint: str,
    data: Dict[str, Any],
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,  # Adicionado user_name
    expected_phone: Optional[str] = None,  # Adicionado expected_phone
) -> Any:
    """
    Faz uma requisição PUT para a API FastAPI.

    Args:
        endpoint: Caminho do endpoint, sem a URL base.
        data: Dados a serem enviados no corpo da requisição.
        user_id: ID do usuário do Telegram (opcional).
        user_name: Nome do usuário (opcional, para X-User-Name).
        expected_phone: Telefone esperado (opcional, para X-Expected-Phone).

    Returns:
        Resposta da API em formato JSON.

    Raises:
        Exception: Erro na requisição ou processamento.
    """
    request_url_for_logging = f'{API_URL}/{endpoint}'
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            url = f'{API_URL}/{endpoint}'
            # request_url_for_logging = url  # Removido
            headers = await get_auth_headers(
                bot_id=user_id,
                user_name=user_name,
                expected_phone=expected_phone,
            )
            logger.debug(f'PUT {url} com dados: {data} e headers: {headers}')
            response = await client.put(url, json=data, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        actual_url_attempted = str(e.request.url)
        response_text = e.response.text
        logger.error(
            f'Erro HTTP {e.response.status_code} na API durante PUT. URL: {
                actual_url_attempted
            }, '
            f'Endpoint: {endpoint}. Data: {data}. Response: {response_text}'
        )
        if e.response.status_code == HTTP_UNPROCESSABLE_ENTITY:
            logger.error(
                f'Erro de validação ({HTTP_UNPROCESSABLE_ENTITY}) PUT para {
                    actual_url_attempted
                }. Detalhes: {response_text}'
            )
        raise
    except httpx.RequestError as e:
        url_info = (
            str(e.request.url)
            if hasattr(e, 'request') and hasattr(e.request, 'url')
            else request_url_for_logging
        )
        logger.error(
            f'Erro de requisição (ex:conexão, timeout) ao tentar PUT.'
            f' URL/Endpoint: {url_info}. Data: {data}. Erro: {str(e)}'
        )
        raise
    except Exception as e:
        logger.error(
            f'Erro inesperado durante PUT para {request_url_for_logging}. '
            f'Data: {data}. Erro: {str(e)}'
        )
        raise


async def fazer_requisicao_delete(
    endpoint: str,
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,  # Adicionado user_name
    expected_phone: Optional[str] = None,  # Adicionado expected_phone
) -> bool:
    """
    Faz uma requisição DELETE para a API FastAPI.

    Args:
        endpoint: Caminho do endpoint, sem a URL base.
        user_id: ID do usuário do Telegram (opcional).
        user_name: Nome do usuário (opcional, para X-User-Name).
        expected_phone: Telefone esperado (opcional, para X-Expected-Phone).

    Returns:
        Resposta da API em formato JSON, se houver.

    Raises:
        Exception: Erro na requisição ou processamento.
    """
    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        try:
            url = f'{API_URL}/{endpoint}'
            # request_url_for_logging = url  # Removido
            headers = await get_auth_headers(
                bot_id=user_id,
                user_name=user_name,
                expected_phone=expected_phone,
            )
            logger.debug(f'DELETE {url} com headers: {headers}')

            response = await client.delete(url, headers=headers)
            response.raise_for_status()

            if response.status_code == HTTP_NO_CONTENT:  # No content
                return None
            return response.json()
        except httpx.HTTPStatusError as e:
            # Tratamento específico por código de status
            if e.response.status_code == HTTP_NOT_FOUND:
                logger.warning(f'recurso não encontrado: {endpoint}')
                return None
            elif e.response.status_code == HTTP_UNAUTHORIZED:
                logger.error(f'Acesso não autorizado: {endpoint}')
                raise PermissionError('Acesso não autorizado')
            else:
                logger.error(f'Erro HTTP {e.response.status_code}: {str(e)}')
                raise Exception(f'Erro na API: {str(e)}')
        except Exception as e:
            logger.error(f'Erro desconhecido: {str(e)}')
            raise Exception(f'Erro desconhecido: {str(e)}')
