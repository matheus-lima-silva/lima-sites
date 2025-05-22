"""
Serviço para gerenciamento de sugestões.
"""

import logging
from typing import Any, Dict, List, Optional

from ..api_client import (
    fazer_requisicao_get,
    fazer_requisicao_post,
    fazer_requisicao_put,
)

logger = logging.getLogger(__name__)


async def criar_sugestao(
    id_usuario: int,
    tipo_sugestao: str,
    detalhe: str,
    id_endereco: Optional[int] = None,
    user_id: Optional[int] = None,  # Adicionado user_id
) -> Dict[str, Any]:
    """
    Cria uma nova sugestão.

    Args:
        id_usuario: ID do usuário que está fazendo a sugestão.
        tipo_sugestao: Tipo da sugestão (adicao, modificacao, remocao).
        detalhe: Detalhes da sugestão.
        id_endereco: ID do endereço relacionado, se houver.
        user_id: ID do usuário do Telegram (opcional) para autenticação.

    Returns:
        Sugestão criada.
    """
    data = {
        'id_usuario': id_usuario,
        'tipo_sugestao': tipo_sugestao,
        'detalhe': detalhe,
    }

    if id_endereco:
        data['id_endereco'] = id_endereco

    return await fazer_requisicao_post('sugestoes/', data, user_id=user_id)


async def listar_sugestoes(
    id_usuario: Optional[int] = None,
    status: Optional[str] = None,
    id_endereco: Optional[int] = None,
    user_id: Optional[int] = None,  # Adicionado user_id
) -> List[Dict[str, Any]]:
    """
    Lista sugestões com filtros.

    Args:
        id_usuario: Filtro por usuário.
        status: Filtro por status (pendente, aprovado, rejeitado).
        id_endereco: Filtro por endereço.
        user_id: ID do usuário do Telegram (opcional) para autenticação.

    Returns:
        Lista de sugestões.
    """
    params = {}

    if id_usuario:
        params['id_usuario'] = id_usuario
    if status:
        params['status'] = status
    if id_endereco:
        params['id_endereco'] = id_endereco

    return await fazer_requisicao_get('sugestoes/', params, user_id=user_id)


async def obter_sugestao(
    id_sugestao: int, user_id: Optional[int] = None
) -> Optional[Dict[str, Any]]:  # Adicionado user_id
    """
    Obtém os detalhes de uma sugestão específica.

    Args:
        id_sugestao: ID da sugestão.
        user_id: ID do usuário do Telegram (opcional) para autenticação.

    Returns:
        Detalhes da sugestão ou None se não encontrada.
    """
    return await fazer_requisicao_get(
        f'sugestoes/{id_sugestao}', user_id=user_id
    )  # Passa user_id


async def atualizar_status_sugestao(
    id_sugestao: int,
    status: str,
    id_usuario: int,  # Este é o id_usuario que realiza a
     # ação, não necessariamente o dono da sugestão
    justificativa: Optional[str] = None,
    user_id: Optional[
        int
    ] = None,  # Adicionado user_id para autenticação da requisição
) -> Dict[str, Any]:
    """
    Atualiza o status de uma sugestão.

    Args:
        id_sugestao: ID da sugestão.
        status: Novo status (aprovado, rejeitado).
        id_usuario: ID do usuário realizando a operação
          (quem está aprovando/rejeitando).
        justificativa: Justificativa da aprovação/rejeição.
        user_id: ID do usuário do Telegram (opcional) para
          autenticação da requisição PUT.

    Returns:
        Sugestão atualizada.
    """
    data = {
        'status': status,
        'id_usuario': id_usuario,  # ID do usuário que está executando a ação
    }

    if justificativa:
        data['justificativa'] = justificativa

    return await fazer_requisicao_put(
        f'sugestoes/{id_sugestao}', data, user_id=user_id
    )
