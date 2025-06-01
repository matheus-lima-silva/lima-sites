"""
Serviço para gerenciamento de tokens de autenticação.
Este módulo centraliza as funções e classes para manipulação de tokens JWT.
"""

import asyncio
import logging
from typing import Optional

import httpx

from ...cache import get_token_cache  # Alterado aqui
from ..config import API_TIMEOUT, API_URL

logger = logging.getLogger(__name__)


class TokenManager:
    """Gerenciador de token de autenticação."""

    def __init__(self):
        """Inicializa o gerenciador de token."""
        self._fetch_lock = asyncio.Lock()
        self._token_cache = get_token_cache()  # Adicionado aqui

    async def set_token(self, token: Optional[str], user_id: int) -> None:
        """Define o token de acesso externamente e no cache."""
        user_id_str = str(user_id)
        if token:
            logger.info(
                f'Token de acesso definido externamente para user_id '
                f'{user_id_str}.'
            )
            # Usa o namespace 'token' e o user_id como identificador
            await self._token_cache.set('token', user_id_str, token)
        else:
            logger.info(
                f'Token de acesso externo removido/limpo para user_id '
                f'{user_id_str}.'
            )
            # Invalida o token específico para o user_id
            await self._token_cache.delete('token', user_id_str)

    async def has_token(self, user_id: int) -> bool:
        """Verifica se um token de acesso já está definido no cache."""
        # Usa o namespace 'token' e o user_id como identificador
        token = await self._token_cache.get('token', str(user_id))
        return token is not None

    async def get_token(self, user_id: int) -> Optional[str]:
        """Obtém o token de acesso do cache."""
        return await self._token_cache.get('token', str(user_id))

    async def _fetch_token_from_api(
        self, telegram_user_id: int, name: Optional[str] = None
    ) -> Optional[str]:
        """Realiza a busca do token na API."""
        user_id_str = str(telegram_user_id)
        access_token: Optional[str] = None
        try:
            async with httpx.AsyncClient(
                base_url=API_URL, timeout=API_TIMEOUT
            ) as client:
                payload = {
                    'telegram_user_id': telegram_user_id,
                    # Corrigido de 'telegram_id' para 'telegram_user_id'
                }
                if name:
                    payload['nome'] = name  # Corrigido de 'name' para 'nome'

                response = await client.post(
                    'auth/telegram/register', json=payload
                )
                response.raise_for_status()
                data = response.json()
                access_token = data.get('access_token')

                if access_token:
                    logger.info(
                        f'Token obtido da API para o usuário {user_id_str}.'
                    )
                    await self.set_token(access_token, telegram_user_id)
                else:
                    logger.warning(
                        f'Nenhum token de acesso retornado pela API para o '
                        f'usuário {user_id_str}.'
                    )
        except httpx.HTTPStatusError as e:
            logger.error(
                f'Erro HTTP ao obter token da API para {user_id_str}: '
                f'{e.response.status_code} - {e.response.text}'
            )
        except httpx.RequestError as e:
            logger.error(
                f'Erro de requisição ao obter token da API para '
                f'{user_id_str}: {e}'
            )
        except Exception as e:
            logger.exception(
                f'Erro inesperado ao obter token da API para '
                f'{user_id_str}: {e}'
            )
        return access_token

    async def obter_token_api(
        self, telegram_user_id: int, name: Optional[str] = None
    ) -> Optional[str]:
        """
        Obtém o token de acesso da API.
        Primeiro verifica o cache, depois busca na API se necessário.
        """
        user_id_str = str(telegram_user_id)
        cached_token = await self.get_token(telegram_user_id)
        if cached_token:
            logger.info(
                f'Token encontrado no cache para o usuário {user_id_str}.'
            )
            return cached_token

        async with self._fetch_lock:  # Garante uma única busca por vez
            # Verifica novamente o cache após adquirir o lock
            cached_token_after_lock = await self.get_token(telegram_user_id)
            if cached_token_after_lock:
                logger.info(
                    f'Token encontrado no cache (após lock) para o usuário '
                    f'{user_id_str}.'
                )
                return cached_token_after_lock

            logger.info(
                f'Nenhum token válido no cache para o usuário {user_id_str}. '
                f'Tentando obter da API...'
            )
            return await self._fetch_token_from_api(telegram_user_id, name)


# Instância única do gerenciador de token
token_manager = TokenManager()
