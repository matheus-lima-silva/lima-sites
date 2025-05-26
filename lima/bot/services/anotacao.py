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
    id_endereco: int,  # Removido id_usuario daqui
    texto: str,
    user_id: Optional[int] = None,  # Mantido user_id para autenticação
) -> Dict[str, Any]:
    """
    Cria uma nova anotação para um endereço.

    Args:
        id_endereco: ID do endereço relacionado.
        texto: Conteúdo da anotação.
        user_id: ID do usuário do Telegram (opcional) para autenticação.

    Returns:
        Anotação criada.
    """
    data = {
        # 'id_usuario': id_usuario, # Removido id_usuario do payload
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
    endpoint = 'anotacoes/'  # Endpoint padrão

    if id_endereco:
        # Usa o endpoint específico para listar por ID de endereço
        endpoint = f'anotacoes/endereco/{id_endereco}'
        # Nenhum parâmetro de consulta é necessário aqui
    elif id_usuario:
        # Se apenas id_usuario é fornecido.
        if user_id is not None and id_usuario == user_id:
            # Lista anotações do usuário logado
            endpoint = 'anotacoes/usuario/minhas'
        else:
            # Listar anotações de um usuário arbitrário (não logado)
            # via query param. O backend precisaria suportar:
            # GET /anotacoes/?id_usuario=X.
            # Este caso pode precisar de revisão ou um endpoint dedicado.
            params['id_usuario'] = id_usuario
            # Mantém endpoint = 'anotacoes/' e adiciona id_usuario aos params.
    elif user_id is not None:
        # Nenhum filtro específico, mas usuário logado.
        # Lista as anotações do usuário logado.
        endpoint = 'anotacoes/usuario/minhas'
    # else:
        # Se user_id for None e nenhum outro filtro for fornecido,
        # a chamada irá para GET /anotacoes/ sem user_id.
        # Isso pode falhar ou requerer tratamento especial no backend.

    return await fazer_requisicao_get(endpoint, params, user_id=user_id)


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
