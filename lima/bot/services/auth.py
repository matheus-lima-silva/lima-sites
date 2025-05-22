"""
Serviço de autenticação para o Bot.
Este módulo gerencia a autenticação do bot com a API.
"""

import logging
import os
from typing import Dict, Optional

import httpx

from ..config import API_TIMEOUT, API_URL

logger = logging.getLogger(__name__)


class TokenManager:
    """Gerenciador de token de autenticação."""

    def __init__(self):
        """Inicializa o gerenciador de token."""
        self._access_token: Optional[str] = None

    def set_token(self, token: Optional[str]) -> None:
        """Define o token de acesso externamente."""
        self._access_token = token

    async def obter_token_api(
        self, telegram_user_id: int, name: Optional[str] = None
    ) -> Optional[str]:
        """
        Obtém um token de acesso para o bot a partir da API.

        Args:
            telegram_user_id: ID do usuário do Telegram
            name: Nome do usuário (opcional)

        Returns:
            Token de acesso ou None se falhar
        """
        # Se já temos um token, retorna ele (em um sistema real,
        #  verificaríamos a validade)
        if self._access_token:
            return self._access_token

        try:
            # Constrói a URL de registro de usuário do Telegram
            url = f'{API_URL}/auth/telegram/register'

            # Prepara o payload com o ID do Telegram
            payload = {
                'telegram_user_id': telegram_user_id,
                'name': name or f'Bot User {telegram_user_id}',
            }

            # Faz a requisição para obter o token
            async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
                logger.debug(
                    f'Autenticando bot com telegram_user_id: '
                    f'{telegram_user_id}'
                )
                response = await client.post(url, json=payload)
                response.raise_for_status()

                # Extrai o token da resposta
                token_data = response.json()
                if 'access_token' in token_data:
                    self._access_token = token_data['access_token']
                    logger.info('Token de API obtido com sucesso')
                    return self._access_token
                else:
                    logger.error(f'Resposta não contém token: {token_data}')
                    return None

        except httpx.HTTPStatusError as e:
            logger.error(
                f'Erro de API ao obter token: '
                f'{e.response.status_code} - {e.response.text}'
            )
            return None
        except Exception as e:
            logger.error(f'Erro ao obter token de API: {str(e)}')
            return None


# Instância única do gerenciador de token
token_manager = TokenManager()


async def get_auth_headers(bot_id: Optional[int] = None) -> Dict[str, str]:
    """
    Obtém os cabeçalhos de autenticação para requisições à API.

    Args:
        bot_id: ID do bot no Telegram (opcional,
          usa um valor padrão se não informado)

    Returns:
        Cabeçalhos de autenticação
    """
    # Usa o BOT_API_ACCESS_TOKEN se estiver definido no ambiente
    token = os.getenv('BOT_API_ACCESS_TOKEN', '')

    # Se não houver token definido, tenta obter um token da API
    if not token and bot_id:
        token = await token_manager.obter_token_api(telegram_user_id=bot_id)

    # Retorna os cabeçalhos com o token, se disponível
    if token:
        return {'Authorization': f'Bearer {token}'}

    # Se não tiver token, retorna cabeçalhos vazios
    return {}
