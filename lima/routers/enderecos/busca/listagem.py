"""
Operações para listar endereços com diferentes filtros.
"""

from typing import Annotated, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....models import (
    BuscaLog,
    Endereco,
    EnderecoOperadora,
    TipoBusca,
    TipoEndereco,
    Usuario,
)
from ....schemas import EnderecoRead
from ....utils.dependencies import AsyncSessionDep, CurrentUserDep

router = APIRouter()


class EnderecoFilterParams(BaseModel):
    """Parâmetros de filtro para busca de endereços."""

    uf: str | None = Field(default=None, description='UF (estado)')
    municipio: str | None = Field(default=None, description='Município')
    bairro: str | None = Field(default=None, description='Bairro')
    tipo: TipoEndereco | None = Field(
        default=None, description='Tipo do endereço'
    )
    compartilhado: bool | None = Field(
        default=None, description='Flag para endereços compartilhados'
    )
    query: str | None = Field(
        default=None, description='Texto para busca livre'
    )
    skip: int = Field(default=0, description='Número de registros a pular')
    limit: int = Field(default=100, description='Número máximo de registros')


EnderecoFilterParamsDep = Annotated[
    EnderecoFilterParams, Depends(EnderecoFilterParams)
]


@router.get('/', response_model=List[EnderecoRead])
async def listar_enderecos(
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
    filter_params: EnderecoFilterParamsDep,
):
    """
    Lista endereços com paginação e filtros

    * Requer autenticação
    * Suporta filtros por UF, município, bairro, tipo e texto
    * Registra a busca para fins de auditoria
    """
    # Construir consulta e aplicar filtros
    stmt = await _construir_consulta_filtrada(filter_params)

    # Executar consulta
    result = await session.execute(stmt)
    enderecos = result.scalars().all()

    # Registrar a busca para auditoria
    await _registrar_busca_auditoria(session, current_user, filter_params)

    return enderecos


async def _construir_consulta_filtrada(filter_params: EnderecoFilterParams):
    """
    Constrói a consulta SQL com filtros aplicados.

    Args:
        filter_params: Parâmetros de filtro para a consulta

    Returns:
        Consulta SQLAlchemy pronta para execução
    """
    # Preparar a consulta base
    stmt = select(Endereco)

    # Construir filtros dinamicamente
    filters = _criar_filtros(filter_params)

    # Aplicar filtros à consulta se houver algum
    if filters:
        stmt = stmt.where(and_(*filters))

    # Ordenar por município e logradouro
    stmt = stmt.order_by(Endereco.uf, Endereco.municipio, Endereco.logradouro)

    # Carregar operadoras e detentora
    stmt = stmt.options(
        selectinload(Endereco.operadoras).selectinload(
            EnderecoOperadora.operadora
        ),
        selectinload(Endereco.detentora),
    )

    # Adicionar paginação
    stmt = stmt.offset(filter_params.skip).limit(filter_params.limit)

    return stmt


def _criar_filtros(filter_params: EnderecoFilterParams):
    """
    Cria a lista de filtros baseada nos parâmetros fornecidos.
    Args:
        filter_params: Parâmetros de filtro para a consulta

    Returns:
        Lista de condições de filtro para SQLAlchemy
    """
    filters = []

    if filter_params.uf:
        filters.append(Endereco.uf == filter_params.uf)

    if filter_params.municipio:
        # Usando formato seguro para evitar SQL injection
        filters.append(
            Endereco.municipio.ilike(f'%{filter_params.municipio}%')
        )

    if filter_params.bairro:
        filters.append(Endereco.bairro.ilike(f'%{filter_params.bairro}%'))

    if filter_params.tipo:
        filters.append(Endereco.tipo == filter_params.tipo)

    if filter_params.compartilhado is not None:
        filters.append(Endereco.compartilhado == filter_params.compartilhado)

    # Busca textual
    if filter_params.query:
        text_search = or_(
            Endereco.logradouro.ilike(f'%{filter_params.query}%'),
            Endereco.bairro.ilike(f'%{filter_params.query}%'),
            Endereco.municipio.ilike(f'%{filter_params.query}%'),
        )
        filters.append(text_search)

    return filters


async def _registrar_busca_auditoria(
    session: AsyncSession,
    current_user: Usuario,
    filter_params: EnderecoFilterParams,
):
    """
    Registra a busca para auditoria.

    Args:
        session: Sessão do banco de dados
        current_user: Usuário que realizou a busca
        filter_params: Parâmetros usados na busca
    """
    # Determinar o tipo de busca com base nos filtros utilizados
    tipo_busca = _determinar_tipo_busca(filter_params)

    # Montar string de parâmetros para registro (sem None values)
    parametros_dict = {
        'uf': filter_params.uf or '',
        'municipio': filter_params.municipio or '',
        'bairro': filter_params.bairro or '',
        'query': filter_params.query or '',
    }

    parametros = ','.join(f'{k}={v}' for k, v in parametros_dict.items() if v)

    # Criar e adicionar o log
    busca_log = BuscaLog(
        usuario_id=current_user.id,
        endpoint='/enderecos',
        parametros=parametros,
        tipo_busca=tipo_busca,
    )
    session.add(busca_log)
    await session.commit()


def _determinar_tipo_busca(filter_params: EnderecoFilterParams) -> TipoBusca:
    """
    Determina o tipo de busca com base nos parâmetros utilizados.

    Args:
        filter_params: Parâmetros de filtro usados na busca

    Returns:
        Tipo de busca a ser registrado
    """
    if filter_params.municipio:
        return TipoBusca.por_municipio
    if filter_params.query:
        return TipoBusca.por_logradouro
    return TipoBusca.listagem
