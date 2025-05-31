"""
Persistência via API usando o cliente HTTP existente.

Implementação simples que delega toda persistência para a API REST,
reutilizando o cliente HTTP já existente.
"""

import json
import logging
from typing import Any, Dict, Optional, Tuple

from telegram.ext import BasePersistence, PersistenceInput

from ..api_client import (
    fazer_requisicao_delete,
    fazer_requisicao_get,
    fazer_requisicao_post,
    fazer_requisicao_put,
)

logger = logging.getLogger(__name__)


async def _safe_api_call(func, *args, **kwargs):
    """
    Executa uma chamada de API com tratamento seguro de erros.

    Retorna dados vazios em caso de erro para manter o bot funcionando.
    """
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        logger.warning(f'Erro na API (continuando com dados vazios): {e}')
        return None


class ApiPersistence(BasePersistence):
    """
    Persistência baseada em API REST usando cliente HTTP existente.

    Delega toda persistência para endpoints REST da API FastAPI.
    """

    def __init__(self, store_data: Optional[PersistenceInput] = None):
        """Inicializa persistência via API."""
        super().__init__(store_data=store_data)

    @staticmethod
    async def get_user_data() -> Dict[int, Dict[str, Any]]:
        """Carrega dados de todos os usuários via API."""
        response = await _safe_api_call(
            fazer_requisicao_get,
            endpoint='bot/conversations/',
            params={'conversation_name': 'user_data'},
            user_id=1000000,  # ID único para o bot (não 0)
            user_name='LimaBot',
        )

        user_data = {}
        if response:
            for state in response:
                if state.get('user_id') and state.get('data'):
                    try:
                        user_data[state['user_id']] = json.loads(state['data'])
                    except json.JSONDecodeError:
                        user_data[state['user_id']] = {}

        return user_data

    @staticmethod
    async def get_chat_data() -> Dict[int, Dict[str, Any]]:
        """Carrega dados de todos os chats via API."""
        response = await _safe_api_call(
            fazer_requisicao_get,
            endpoint='bot/conversations/',
            params={'conversation_name': 'chat_data'},
            user_id=1000000,  # ID único para o bot (não 0)
            user_name='LimaBot',
        )

        chat_data = {}
        if response:
            for state in response:
                if state.get('chat_id') and state.get('data'):
                    try:
                        chat_data[state['chat_id']] = json.loads(state['data'])
                    except json.JSONDecodeError:
                        chat_data[state['chat_id']] = {}

        return chat_data

    @staticmethod
    async def get_bot_data() -> Dict[str, Any]:
        """Carrega dados globais do bot via API."""
        response = await _safe_api_call(
            fazer_requisicao_get,
            endpoint='bot/conversations/by-conversation/',
            params={
                'user_id': 0,
                'chat_id': 0,
                'conversation_name': 'bot_data',
            },
            user_id=1000000,  # ID único para o bot (não 0)
            user_name='LimaBot',
        )

        if response and response.get('data'):
            try:
                return json.loads(response['data'])
            except json.JSONDecodeError:
                logger.warning('Erro ao decodificar JSON dos dados do bot')
        return {}

    @staticmethod
    async def get_callback_data() -> Optional[Tuple[Any, ...]]:
        """Carrega dados de callback (não implementado)."""
        return None

    @staticmethod
    async def get_conversations(name: str) -> Dict[str, Any]:
        """Carrega conversações ativas via API."""
        response = await _safe_api_call(
            fazer_requisicao_get,
            endpoint='bot/conversations/',
            params={'conversation_name': f'conversation_{name}'},
            user_id=1000000,  # ID único para o bot (não 0)
            user_name='LimaBot',
        )

        conversations = {}
        if response:
            for state in response:
                key = f'({state["chat_id"]}, {state["user_id"]})'
                try:
                    conversations[key] = (
                        int(state['state']) if state['state'] else None
                    )
                except (ValueError, TypeError):
                    conversations[key] = state['state']

        return conversations

    async def update_user_data(
        self, user_id: int, data: Dict[str, Any]
    ) -> None:
        """Atualiza dados do usuário via API."""
        await self._save_state(
            conversation_data={
                'user_id': user_id,
                'chat_id': user_id,
                'conversation_name': 'user_data',
                'data': data,
            },
            auth_params={
                'auth_user_id': user_id,
                'auth_user_name': f'User {user_id}',
            },
        )

    async def update_chat_data(
        self, chat_id: int, data: Dict[str, Any]
    ) -> None:
        """Atualiza dados do chat via API."""
        await self._save_state(
            conversation_data={
                'user_id': 0,
                'chat_id': chat_id,
                'conversation_name': 'chat_data',
                'data': data,
            },
            auth_params={
                'auth_user_id': 1000000,
                'auth_user_name': 'LimaBot',
            },
        )

    async def update_bot_data(self, data: Dict[str, Any]) -> None:
        """Atualiza dados globais do bot via API."""
        await self._save_state(
            conversation_data={
                'user_id': 0,
                'chat_id': 0,
                'conversation_name': 'bot_data',
                'data': data,
            },
            auth_params={
                'auth_user_id': 1000000,
                'auth_user_name': 'LimaBot',
            },
        )

    async def update_callback_data(self, data: object) -> None:
        """Atualiza dados de callback (não implementado)."""
        pass

    async def update_conversation(
        self, name: str, key: Tuple[int, int], new_state: Optional[object]
    ) -> None:
        """Atualiza conversação específica via API."""
        chat_id, user_id = key

        if new_state is None:
            # Deletar conversação
            try:
                await fazer_requisicao_delete(
                    endpoint=f'bot/conversations/by-conversation/?'
                    f'user_id={user_id}&chat_id={chat_id}&'
                    f'conversation_name=conversation_{name}',
                    user_id=user_id if user_id > 0 else 1000000,
                    user_name=f'User {user_id}' if user_id > 0 else 'LimaBot',
                )
            except Exception as e:
                logger.error(f'Erro ao deletar conversação {name}: {e}')
        else:
            # Salvar novo estado
            await self._save_state(
                conversation_data={
                    'user_id': user_id,
                    'chat_id': chat_id,
                    'conversation_name': f'conversation_{name}',
                    'state': new_state,
                },
                auth_params={
                    'auth_user_id': user_id if user_id > 0 else 1000000,
                    'auth_user_name': (
                        f'User {user_id}' if user_id > 0 else 'LimaBot'
                    ),
                },
            )

    @staticmethod
    async def _save_state(
        conversation_data: Dict[str, Any],
        auth_params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Método auxiliar para salvar estado via API."""
        user_id, chat_id, conversation_name, state, data = (
            ApiPersistence._extract_conversation_fields(conversation_data)
        )
        request_user_id, request_user_name = ApiPersistence._resolve_auth(
            auth_params, user_id
        )

        existing_id = await ApiPersistence._get_existing_state_id(
            user_id,
            chat_id,
            conversation_name,
            request_user_id,
            request_user_name,
        )

        data_json_str = json.dumps(data if data is not None else {})

        # Criar dicionários com informações agrupadas
        context_info = {
            'user_id': user_id,
            'chat_id': chat_id,
            'conversation_name': conversation_name,
        }
        auth_info = {
            'request_user_id': request_user_id,
            'request_user_name': request_user_name,
        }

        if existing_id:
            await ApiPersistence._update_state(
                existing_id, state, data_json_str, auth_info, context_info
            )
        else:
            await ApiPersistence._create_state(
                state, data_json_str, auth_info, context_info
            )

    @staticmethod
    def _extract_conversation_fields(conversation_data: Dict[str, Any]):
        user_id = conversation_data['user_id']
        chat_id = conversation_data['chat_id']
        conversation_name = conversation_data['conversation_name']
        state = conversation_data.get('state')
        data = conversation_data.get('data')
        return user_id, chat_id, conversation_name, state, data

    @staticmethod
    def _resolve_auth(auth_params: Optional[Dict[str, Any]], user_id: int):
        auth_params = auth_params or {}
        auth_user_id = auth_params.get('auth_user_id')
        auth_user_name = auth_params.get('auth_user_name')
        request_user_id = auth_user_id or (user_id if user_id > 0 else 1000000)
        request_user_name = auth_user_name or f'User {request_user_id}'
        return request_user_id, request_user_name

    @staticmethod
    async def _get_existing_state_id(
        user_id: int,
        chat_id: int,
        conversation_name: str,
        request_user_id: int,
        request_user_name: str,
    ):
        try:
            existing_state = await fazer_requisicao_get(
                endpoint='bot/conversations/by-conversation/',
                params={
                    'user_id': user_id,
                    'chat_id': chat_id,
                    'conversation_name': conversation_name,
                },
                user_id=request_user_id,
                user_name=request_user_name,
            )
            return existing_state.get('id') if existing_state else None
        except Exception:
            return None

    @staticmethod
    async def _update_state(
        existing_id: int,
        state: Any,
        data_json_str: str,
        auth_info: Dict[str, Any],
        context_info: Dict[str, Any],
    ):
        """
        Atualiza um estado de conversação existente.

        Args:
            existing_id: ID do estado existente
            state: Estado da conversação
            data_json_str: Dados JSON serializados
            auth_info: Informações de autenticação
                (request_user_id, request_user_name)
            context_info: Informações de contexto
                (user_id, chat_id, conversation_name)
        """
        update_payload = {
            'state': str(state) if state is not None else None,
            'data': data_json_str,
            'data_type': 'json',
        }
        try:
            await fazer_requisicao_put(
                endpoint=f'bot/conversations/{existing_id}',
                data=update_payload,
                user_id=auth_info['request_user_id'],
                user_name=auth_info['request_user_name'],
            )
        except Exception as e:
            logger.error(
                f'Erro ao atualizar estado (PUT) '
                f'(id={existing_id}, user_id={context_info["user_id"]}, '
                f'chat_id={context_info["chat_id"]}, '
                f'conversation_name={context_info["conversation_name"]}): {e}'
            )

    @staticmethod
    async def _create_state(
        state: Any,
        data_json_str: str,
        auth_info: Dict[str, Any],
        context_info: Dict[str, Any],
    ):
        """
        Cria um novo estado de conversação.

        Args:
            state: Estado da conversação
            data_json_str: Dados JSON serializados
            auth_info: Informações de autenticação
            context_info: Informações de contexto
        """
        user_id = context_info['user_id']
        chat_id = context_info['chat_id']
        conversation_name = context_info['conversation_name']

        payload = {
            'user_id': user_id,
            'chat_id': chat_id,
            'conversation_name': conversation_name,
            'state': str(state) if state is not None else None,
            'data': data_json_str,
            'data_type': 'json',
        }

        logger.info(f'API_PERSISTENCE: Payload para POST: {payload}')

        try:
            await fazer_requisicao_post(
                endpoint='bot/conversations/',
                data=payload,
                user_id=auth_info['request_user_id'],
                user_name=auth_info['request_user_name'],
            )
        except Exception as e:
            logger.error(
                f'Erro ao salvar novo estado (POST) '
                f'(user_id={user_id}, chat_id={chat_id}, '
                f'conversation_name={conversation_name}): {e}'
            )

    @staticmethod
    async def drop_chat_data(chat_id: int) -> None:
        """Remove dados do chat via API."""
        try:
            await fazer_requisicao_delete(
                endpoint=f'bot/conversations/by-conversation/?'
                f'user_id=0&chat_id={chat_id}&'
                f'conversation_name=chat_data',
                user_id=1000000,
                user_name='LimaBot',
            )
        except Exception as e:
            logger.error(f'Erro ao remover chat_data para {chat_id}: {e}')

    @staticmethod
    async def drop_user_data(user_id: int) -> None:
        """Remove dados do usuário via API."""
        try:
            await fazer_requisicao_delete(
                endpoint=f'bot/conversations/by-conversation/?'
                f'user_id={user_id}&chat_id={user_id}&'
                f'conversation_name=user_data',
                user_id=user_id if user_id > 0 else 1000000,
                user_name=f'User {user_id}' if user_id > 0 else 'LimaBot',
            )
        except Exception as e:
            logger.error(f'Erro ao remover user_data para {user_id}: {e}')

    async def refresh_user_data(
        self, user_id: int, user_data: Dict[str, Any]
    ) -> None:
        """Atualiza dados do usuário (alias)."""
        await self.update_user_data(user_id, user_data)

    async def refresh_chat_data(
        self, chat_id: int, chat_data: Dict[str, Any]
    ) -> None:
        """Atualiza dados do chat (alias)."""
        await self.update_chat_data(chat_id, chat_data)

    async def refresh_bot_data(self, bot_data: Dict[str, Any]) -> None:
        """Atualiza dados do bot (alias)."""
        await self.update_bot_data(bot_data)

    @staticmethod
    async def flush() -> None:
        """Força persistência (não necessário para API stateless)."""
        logger.debug('Flush executado (API stateless)')
