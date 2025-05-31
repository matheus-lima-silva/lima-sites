"""
Cliente específico para persistência de estados de conversação via API.

Este módulo implementa um cliente que utiliza os endpoints REST da API
para persistir estados de conversação, substituindo o acesso direto ao banco.
"""

import json
import logging
from typing import Any, Dict, Optional, Tuple

from ..api_client import (
    fazer_requisicao_delete,
    fazer_requisicao_get,
    fazer_requisicao_post,
    fazer_requisicao_put,
)

logger = logging.getLogger(__name__)


class ApiPersistenceClient:
    """
    Cliente para persistência de estados de conversação via API REST.

    Esta classe encapsula todas as operações de persistência delegando
    para os endpoints da API FastAPI, mantendo o bot stateless.
    """

    def __init__(self):
        """Inicializa o cliente de persistência."""
        self.base_endpoint = 'bot/conversations'

    async def get_conversation_state(
        self,
        user_id: int,
        chat_id: int,
        conversation_name: str,
        user_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Recupera um estado de conversação específico.

        Args:
            user_id: ID do usuário no Telegram
            chat_id: ID do chat no Telegram
            conversation_name: Nome da conversação
            user_name: Nome do usuário (opcional)

        Returns:
            Estado da conversação ou None se não encontrado
        """
        try:
            endpoint = f'{self.base_endpoint}/by-conversation/'
            params = {
                'user_id': user_id,
                'chat_id': chat_id,
                'conversation_name': conversation_name,
            }

            response = await fazer_requisicao_get(
                endpoint=endpoint,
                params=params,
                user_id=user_id,
                user_name=user_name,
            )

            return response

        except Exception as e:
            logger.error(
                f'Erro ao buscar estado de conversação '
                f'(user_id={user_id}, chat_id={chat_id}, '
                f'conversation_name={conversation_name}): {e}'
            )
            return None

    async def save_conversation_state(
        self,
        conversation_data: Dict[str, Any],
        user_name: Optional[str] = None,
    ) -> bool:
        """
        Salva um estado de conversação.

        Args:
            conversation_data: Dados da conversação contendo:
                - user_id: ID do usuário no Telegram
                - chat_id: ID do chat no Telegram
                - conversation_name: Nome da conversação
                - state: Estado da conversação (string ou int) - opcional
                - data: Dados adicionais da conversação - opcional
            user_name: Nome do usuário (opcional)

        Returns:
            True se salvou com sucesso, False caso contrário
        """
        try:
            user_id = conversation_data['user_id']
            chat_id = conversation_data['chat_id']
            conversation_name = conversation_data['conversation_name']
            state = conversation_data.get('state')
            data = conversation_data.get('data')
            # Primeiro tenta buscar se já existe
            existing_state = await self.get_conversation_state(
                user_id=user_id,
                chat_id=chat_id,
                conversation_name=conversation_name,
                user_name=user_name,
            )

            # Prepara os dados para envio
            state_data = {
                'user_id': user_id,
                'chat_id': chat_id,
                'conversation_name': conversation_name,
                'state': str(state) if state is not None else None,
                'data': json.dumps(data) if data else None,
            }

            if existing_state:
                # Atualiza estado existente
                endpoint = f'{self.base_endpoint}/by-conversation/'
                params = {
                    'user_id': user_id,
                    'chat_id': chat_id,
                    'conversation_name': conversation_name,
                }

                # Remove campos que não devem ser enviados no update
                update_data = {
                    k: v
                    for k, v in state_data.items()
                    if k not in {'user_id', 'chat_id', 'conversation_name'}
                }

                response = await fazer_requisicao_put(
                    endpoint=endpoint,
                    params=params,
                    data=update_data,
                    user_id=user_id,
                    user_name=user_name,
                )
            else:
                # Cria novo estado
                endpoint = f'{self.base_endpoint}/'
                response = await fazer_requisicao_post(
                    endpoint=endpoint,
                    data=state_data,
                    user_id=user_id,
                    user_name=user_name,
                )

            return response is not None

        except Exception as e:
            logger.error(
                f'Erro ao salvar estado de conversação '
                f'(user_id={user_id}, chat_id={chat_id}, '
                f'conversation_name={conversation_name}): {e}'
            )
            return False

    async def delete_conversation_state(
        self,
        user_id: int,
        chat_id: int,
        conversation_name: str,
        user_name: Optional[str] = None,
    ) -> bool:
        """
        Remove um estado de conversação específico.

        Args:
            user_id: ID do usuário no Telegram
            chat_id: ID do chat no Telegram
            conversation_name: Nome da conversação
            user_name: Nome do usuário (opcional)

        Returns:
            True se removeu com sucesso, False caso contrário
        """
        try:
            endpoint = f'{self.base_endpoint}/by-conversation/'
            params = {
                'user_id': user_id,
                'chat_id': chat_id,
                'conversation_name': conversation_name,
            }

            response = await fazer_requisicao_delete(
                endpoint=endpoint,
                params=params,
                user_id=user_id,
                user_name=user_name,
            )

            return response is not None

        except Exception as e:
            logger.error(
                f'Erro ao deletar estado de conversação '
                f'(user_id={user_id}, chat_id={chat_id}, '
                f'conversation_name={conversation_name}): {e}'
            )
            return False

    async def get_user_data(
        self, user_id: int, user_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recupera dados do usuário.

        Args:
            user_id: ID do usuário no Telegram
            user_name: Nome do usuário (opcional)

        Returns:
            Dados do usuário ou dicionário vazio
        """
        try:
            state = await self.get_conversation_state(
                user_id=user_id,
                chat_id=user_id,  # Para user_data, chat_id = user_id
                conversation_name='user_data',
                user_name=user_name,
            )

            if state and state.get('data'):
                return json.loads(state['data'])

            return {}

        except Exception as e:
            logger.error(
                f'Erro ao buscar user_data para user_id={user_id}: {e}'
            )
            return {}

    async def save_user_data(
        self,
        user_id: int,
        data: Dict[str, Any],
        user_name: Optional[str] = None,
    ) -> bool:
        """
        Salva dados do usuário.

        Args:
            user_id: ID do usuário no Telegram
            data: Dados a serem salvos
            user_name: Nome do usuário (opcional)

        Returns:
            True se salvou com sucesso, False caso contrário
        """
        return await self.save_conversation_state(
            conversation_data={
                'user_id': user_id,
                'chat_id': user_id,  # Para user_data, chat_id = user_id
                'conversation_name': 'user_data',
                'data': data,
            },
            user_name=user_name,
        )

    async def get_chat_data(
        self, chat_id: int, user_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recupera dados do chat.

        Args:
            chat_id: ID do chat no Telegram
            user_name: Nome do usuário (opcional)

        Returns:
            Dados do chat ou dicionário vazio
        """
        try:
            state = await self.get_conversation_state(
                user_id=0,  # Para chat_data, user_id é 0
                chat_id=chat_id,
                conversation_name='chat_data',
                user_name=user_name,
            )

            if state and state.get('data'):
                return json.loads(state['data'])

            return {}

        except Exception as e:
            logger.error(
                f'Erro ao buscar chat_data para chat_id={chat_id}: {e}'
            )
            return {}

    async def save_chat_data(
        self,
        chat_id: int,
        data: Dict[str, Any],
        user_name: Optional[str] = None,
    ) -> bool:
        """
        Salva dados do chat.

        Args:
            chat_id: ID do chat no Telegram
            data: Dados a serem salvos
            user_name: Nome do usuário (opcional)

        Returns:
            True se salvou com sucesso, False caso contrário
        """
        return await self.save_conversation_state(
            conversation_data={
                'user_id': 0,  # Para chat_data, user_id é 0
                'chat_id': chat_id,
                'conversation_name': 'chat_data',
                'data': data,
            },
            user_name=user_name,
        )

    async def get_bot_data(
        self, user_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recupera dados globais do bot.

        Args:
            user_name: Nome do usuário (opcional)

        Returns:
            Dados do bot ou dicionário vazio
        """
        try:
            state = await self.get_conversation_state(
                user_id=0,  # Para bot_data, user_id é 0
                chat_id=0,  # Para bot_data, chat_id é 0
                conversation_name='bot_data',
                user_name=user_name,
            )

            if state and state.get('data'):
                return json.loads(state['data'])

            return {}

        except Exception as e:
            logger.error(f'Erro ao buscar bot_data: {e}')
            return {}

    async def save_bot_data(
        self, data: Dict[str, Any], user_name: Optional[str] = None
    ) -> bool:
        """
        Salva dados globais do bot.

        Args:
            data: Dados a serem salvos
            user_name: Nome do usuário (opcional)

        Returns:
            True se salvou com sucesso, False caso contrário
        """
        return await self.save_conversation_state(
            conversation_data={
                'user_id': 0,  # Para bot_data, user_id é 0
                'chat_id': 0,  # Para bot_data, chat_id é 0
                'conversation_name': 'bot_data',
                'data': data,
            },
            user_name=user_name,
        )

    async def get_conversations_by_name(
        self, name: str, user_name: Optional[str] = None
    ) -> Dict[Tuple[int, int], Any]:
        """
        Recupera todas as conversações de um tipo específico.

        Args:
            name: Nome da conversação (ex: 'busca_codigo')
            user_name: Nome do usuário (opcional)

        Returns:
            Dicionário com as conversações indexadas por (chat_id, user_id)
        """
        try:
            endpoint = f'{self.base_endpoint}/'
            params = {'conversation_name': f'conversation_{name}'}

            response = await fazer_requisicao_get(
                endpoint=endpoint, params=params, user_name=user_name
            )

            conversations = {}
            if response:
                for state in response:
                    key = (state['chat_id'], state['user_id'])
                    try:
                        conversations[key] = (
                            int(state['state']) if state['state'] else None
                        )
                    except (ValueError, TypeError):
                        conversations[key] = state['state']

            return conversations

        except Exception as e:
            logger.error(f'Erro ao buscar conversações {name}: {e}')
            return {}

    async def save_conversation(
        self,
        name: str,
        key: Tuple[int, int],
        new_state: Optional[object],
        user_name: Optional[str] = None,
    ) -> bool:
        """
        Salva uma conversação específica.

        Args:
            name: Nome da conversação
            key: Chave da conversação (chat_id, user_id)
            new_state: Novo estado da conversação
            user_name: Nome do usuário (opcional)

        Returns:
            True se salvou com sucesso, False caso contrário
        """
        chat_id, user_id = key

        if new_state is None:
            # Se new_state é None, deletar a conversação
            return await self.delete_conversation_state(
                user_id=user_id,
                chat_id=chat_id,
                conversation_name=f'conversation_{name}',
                user_name=user_name,
            )
        else:
            # Salvar novo estado
            return await self.save_conversation_state(
                conversation_data={
                    'user_id': user_id,
                    'chat_id': chat_id,
                    'conversation_name': f'conversation_{name}',
                    'state': new_state,
                },
                user_name=user_name,
            )

    @staticmethod
    async def cleanup_old_data(days: int = 30) -> bool:
        """
        Limpa dados antigos (delega para a API se houver endpoint).

        Args:
            days: Número de dias para manter os dados

        Returns:
            True se executou com sucesso
        """
        # Por enquanto, apenas log - pode ser implementado endpoint específico
        logger.info(
            f'Limpeza de dados antigos (>{days} dias) seria executada via API'
        )
        return True


# Instância global do cliente
api_persistence_client = ApiPersistenceClient()
