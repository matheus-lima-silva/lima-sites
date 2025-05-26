"""
Serviço para gerenciamento de endereços.
"""

import logging
from dataclasses import dataclass  # Removido field, adicionado dataclass
from typing import Any, Dict, List, Optional

from ..api_client import fazer_requisicao_get, fazer_requisicao_post

logger = logging.getLogger(__name__)


@dataclass
class FiltrosEndereco:
    """
    Parâmetros de filtro para busca de endereços.
    """

    query: Optional[str] = None
    municipio: Optional[str] = None
    uf: Optional[str] = None
    cep: Optional[str] = None
    tipo: Optional[str] = None
    detentora_id: Optional[int] = None
    operadora_id: Optional[int] = None
    limite: int = 10


async def buscar_endereco(
    filtros: FiltrosEndereco,
    id_endereco: Optional[int] = None,
    user_id: Optional[int] = None,  # Adicionado user_id
) -> List[Dict[str, Any]]:
    """
    Busca endereços na API com diversos filtros.

    Args:
        filtros: Objeto com os parâmetros de filtro.
        id_endereco: Busca por ID específico.
        user_id: ID do usuário do Telegram (opcional) para autenticação.

    Returns:
        Lista de endereços encontrados.
    """
    params = {}

    if filtros.query:
        params['q'] = filtros.query
    if filtros.municipio:
        params['municipio'] = filtros.municipio
    if filtros.uf:
        params['uf'] = filtros.uf
    if filtros.cep:
        params['cep'] = filtros.cep
    if filtros.tipo:
        params['tipo'] = filtros.tipo
    if filtros.detentora_id:
        params['detentora_id'] = filtros.detentora_id
    if filtros.operadora_id:
        params['operadora_id'] = filtros.operadora_id
    # limite é int, sempre terá valor (padrão 10), não precisa de if None
    params['limite'] = filtros.limite

    if id_endereco:
        # Se busca por ID, usa endpoint específico
        endereco = await fazer_requisicao_get(f'enderecos/admin/{id_endereco}',
        # Modificado aqui
         user_id=user_id)
        return [endereco] if endereco else []
    else:
        # Busca geral com filtros
        return await fazer_requisicao_get(
            'enderecos/', params, user_id=user_id)


async def registrar_busca(
    id_usuario: int, id_endereco: int, info_adicional: Optional[str] = None,
    user_id: Optional[int] = None,
      # Adicionado user_id para consistência, embora a chamada POST possa não
      #  usá-lo diretamente para auth se o token já estiver no header
) -> Dict[str, Any]:
    """
    Registra uma busca no histórico.

    Args:
        id_usuario: ID do usuário que realizou a busca.
        id_endereco: ID do endereço consultado.
        info_adicional: Informações adicionais sobre a busca.
        user_id: ID do usuário do Telegram (opcional)
          para autenticação da requisição POST.

    Returns:
        Registro da busca criado.
    """
    data = {'id_usuario': id_usuario, 'id_endereco': id_endereco}

    if info_adicional:
        data['info_adicional'] = info_adicional

    return await fazer_requisicao_post('buscas/', data, user_id=user_id)


async def buscar_por_coordenadas(
    latitude: float, longitude: float, raio: Optional[float] = None,
    user_id: Optional[int] = None,  # Adicionado user_id
) -> List[Dict[str, Any]]:
    """
    Busca endereços próximos às coordenadas informadas.

    Args:
        latitude: Latitude da posição.
        longitude: Longitude da posição.
        raio: Raio de busca em quilômetros (opcional).
        user_id: ID do usuário do Telegram (opcional) para autenticação.

    Returns:
        Lista de endereços encontrados.
    """
    params = {'latitude': latitude, 'longitude': longitude}

    if raio:
        params['raio'] = raio

    return await fazer_requisicao_get('enderecos/busca/coordenadas', params,
         user_id=user_id)


async def obter_detentoras(user_id: Optional[int] = None) -> List[Dict[
    str, Any]]:
    # Adicionado user_id
    """
    Obtém a lista de detentoras cadastradas.

    Args:
        user_id: ID do usuário do Telegram (opcional) para autenticação.

    Returns:
        Lista de detentoras.
    """
    return await fazer_requisicao_get('detentoras/', user_id=user_id)


async def obter_operadoras(user_id: Optional[int] = None) -> List[
    Dict[str, Any]]:
    # Adicionado user_id
    """
    Obtém a lista de operadoras cadastradas.

    Args:
        user_id: ID do usuário do Telegram (opcional) para autenticação.

    Returns:
        Lista de operadoras.
    """
    return await fazer_requisicao_get('operadoras/', user_id=user_id)


async def buscar_por_operadora(
    codigo_operadora: str,
    limite: int = 10,
    skip: int = 0,
    user_id: Optional[int] = None,  # Adicionado user_id
) -> list[dict]:
    """
    Busca endereços por código de operadora, compatível com o endpoint
    /enderecos/busca/por-operadora/{codigo_operadora}

    Args:
        codigo_operadora: Código da operadora.
        limite: Limite de resultados.
        skip: Quantidade de resultados a pular (para paginação).
        user_id: ID do usuário do Telegram (opcional) para autenticação.
    """
    endpoint = f'enderecos/busca/por-operadora/{codigo_operadora}'
    params = {'limit': limite, 'skip': skip}
    return await fazer_requisicao_get(endpoint, params, user_id=user_id)
