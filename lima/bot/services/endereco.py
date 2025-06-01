"""
Serviço para gerenciamento de endereços.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ...cache import cached, get_query_cache  # Alterado e corrigido
from ..api_client import fazer_requisicao_get, fazer_requisicao_post

logger = logging.getLogger(__name__)

# Instanciar o cache de queries para uso com o decorador @cached ou diretamente
query_cache = get_query_cache()  # Alterado e corrigido


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


@cached(query_cache)  # Adicionado decorador
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
        endereco = await fazer_requisicao_get(
            f'enderecos/admin/{id_endereco}',
            params={'load_relations': True},  # Carrega relacionamentos
            user_id=user_id,
        )
        return [endereco] if endereco else []
    else:
        # Busca geral com filtros
        return await fazer_requisicao_get(
            'enderecos/', params, user_id=user_id
        )


async def registrar_busca(
    id_usuario: int,
    id_endereco: int,
    info_adicional: Optional[str] = None,
    user_id: Optional[int] = None,
    # Adicionado user_id para consistência, embora a chamada POST possa não
    #  usá-lo diretamente para auth se o token já estiver no header
) -> Dict[str, Any]:
    """
    Registra uma busca no histórico.
    Esta função realiza uma operação de escrita (POST), então não deve ser
    cacheada.

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


@cached(query_cache)  # Adicionado decorador
async def buscar_por_coordenadas(
    latitude: float,
    longitude: float,
    raio: Optional[float] = None,
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

    return await fazer_requisicao_get(
        'enderecos/busca/coordenadas', params, user_id=user_id
    )


@cached(query_cache)  # Adicionado decorador
async def obter_detentoras(
    user_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    # Adicionado user_id
    """
    Obtém a lista de detentoras cadastradas.

    Args:
        user_id: ID do usuário do Telegram (opcional) para autenticação.

    Returns:
        Lista de detentoras.
    """
    return await fazer_requisicao_get('detentoras/', user_id=user_id)


@cached(query_cache)  # Adicionado decorador
async def obter_operadoras(
    user_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    # Adicionado user_id
    """
    Obtém a lista de operadoras cadastradas.

    Args:
        user_id: ID do usuário do Telegram (opcional) para autenticação.

    Returns:
        Lista de operadoras.
    """
    return await fazer_requisicao_get('operadoras/', user_id=user_id)


@cached(query_cache)  # Adicionado decorador
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


async def buscar_endereco_por_codigo(
    codigo: str,
    tipo_codigo: str,
    usuario_id: Optional[int] = None,
    user_id_telegram: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Busca endereços por diferentes tipos de código.

    Args:
        codigo: O código a ser buscado
        tipo_codigo: Tipo do código (
        'cod_operadora', 'cod_detentora', 'id_sistema')
        usuario_id: ID do usuário no sistema interno (opcional)
        user_id_telegram: ID do usuário do Telegram para autenticação

    Returns:
        Lista de endereços encontrados
    """
    try:
        if tipo_codigo == 'cod_operadora':
            # Usar o endpoint específico para busca por operadora
            return await buscar_por_operadora(
                codigo_operadora=codigo,
                limite=50,
                # Permitir mais resultados para códigos com múltiplos matches
                skip=0,
                user_id=user_id_telegram,
            )

        elif tipo_codigo == 'cod_detentora':
            # Busca por código de detentora usando query geral com filtro
            filtros = FiltrosEndereco(query=codigo, limite=50)
            resultados = await buscar_endereco(
                filtros, user_id=user_id_telegram
            )

            # Filtrar resultados que realmente correspondem
            #  ao código da detentora
            # (isso pode precisar ser ajustado dependendo
            #  da estrutura de dados)
            return [
                r
                for r in resultados
                if r.get('detentora_codigo') == codigo
                or r.get('codigo_detentora') == codigo
                or codigo.lower() in str(r.get('detentora_nome', '')).lower()
            ]

        elif tipo_codigo == 'id_sistema':
            # Busca por ID do sistema usando endpoint específico
            try:
                id_endereco = int(codigo)
                return await buscar_endereco(
                    FiltrosEndereco(limite=1),
                    id_endereco=id_endereco,
                    user_id=user_id_telegram,
                )
            except ValueError:
                logger.warning(
                    f'ID do sistema inválido (não é um número): {codigo}'
                )
                return []

        else:
            logger.error(f'Tipo de código não suportado: {tipo_codigo}')
            return []

    except Exception as e:
        logger.error(
            f'Erro ao buscar endereço por código {codigo} (tipo: {
                tipo_codigo
            }): {str(e)}'
        )
        return []
