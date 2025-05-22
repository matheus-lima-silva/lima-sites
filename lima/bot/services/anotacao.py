"""
Serviço para gerenciamento de anotações.
"""

import logging
from typing import Any, Dict, List, Optional

from ..api_client import (  # Corrigido import para múltiplas linhas
    fazer_requisicao_delete,
    fazer_requisicao_get,
    fazer_requisicao_post,
    fazer_requisicao_put,
)

logger = logging.getLogger(__name__)


async def criar_anotacao(
    id_usuario: int,
    id_endereco: int,
    texto: str,
    user_id: Optional[int] = None,  # Adicionado user_id
) -> Dict[str, Any]:
    """
    Cria uma nova anotação para um endereço.

    Args:
        id_usuario: ID do usuário que está criando a anotação.
        id_endereco: ID do endereço relacionado.
        texto: Conteúdo da anotação.
        user_id: ID do usuário do Telegram (opcional) para autenticação.

    Returns:
        Anotação criada.
    """
    data = {
        'id_usuario': id_usuario,
        'id_endereco': id_endereco,
        'texto': texto,
    }

    return await fazer_requisicao_post('anotacoes/', data, user_id=user_id)


async def listar_anotacoes(
    id_endereco: Optional[int] = None,
    id_usuario: Optional[int] = None,
    user_id: Optional[int] = None,  # Adicionado user_id
) -> List[Dict[str, Any]]:
    """
    Lista anotações com filtros.

    Args:
        id_endereco: Filtro por endereço.
        id_usuario: Filtro por usuário.
        user_id: ID do usuário do Telegram (opcional) para autenticação.

    Returns:
        Lista de anotações.
    """
    params = {}

    if id_endereco:
        params['id_endereco'] = id_endereco
    if id_usuario:
        params['id_usuario'] = id_usuario

    return await fazer_requisicao_get('anotacoes/', params, user_id=user_id)


async def obter_anotacao(
    id_anotacao: int,
    user_id: Optional[int] = None,  # Adicionado user_id
) -> Optional[Dict[str, Any]]:
    """
    Obtém os detalhes de uma anotação específica.

    Args:
        id_anotacao: ID da anotação.
        user_id: ID do usuário do Telegram (opcional) para autenticação.

    Returns:
        Detalhes da anotação ou None se não encontrada.
    """
    return await fazer_requisicao_get(
        f'anotacoes/{id_anotacao}', user_id=user_id
    )


async def atualizar_anotacao(
    id_anotacao: int,
    id_usuario: int,
    texto: str,
    user_id: Optional[int] = None,  # Adicionado user_id
) -> Dict[str, Any]:
    """
    Atualiza o conteúdo de uma anotação.

    Args:
        id_anotacao: ID da anotação.
        id_usuario: ID do usuário realizando a atualização.
        texto: Novo conteúdo da anotação.
        user_id: ID do usuário do Telegram (opcional) para autenticação.

    Returns:
        Anotação atualizada.
    """
    data = {'id_usuario': id_usuario, 'texto': texto}

    return await fazer_requisicao_put(
        f'anotacoes/{id_anotacao}', data, user_id=user_id
    )


async def remover_anotacao(
    id_anotacao: int,
    user_id: Optional[int] = None,  # Adicionado user_id
) -> None:
    """
    Remove uma anotação.

    Args:
        id_anotacao: ID da anotação a ser removida.
        user_id: ID do usuário do Telegram (opcional) para autenticação.
    """
    await fazer_requisicao_delete(f'anotacoes/{id_anotacao}', user_id=user_id)
