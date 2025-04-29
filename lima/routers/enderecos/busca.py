"""
Operações para buscar endereços por código, operadora ou detentora.
"""

from typing import Annotated, List, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...database import get_async_session
from ...models import (
    BuscaLog,
    Detentora,
    Endereco,
    EnderecoOperadora,
    Operadora,
    TipoBusca,
    Usuario,
)
from ...schemas import EnderecoRead, EnderecoReadComplete
from ...security import get_current_user
from .utils import endereco_to_schema, filtrar_anotacoes_por_acesso

router = APIRouter()

# Definições de dependências usando Annotated
AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]
CurrentUserDep = Annotated[Usuario, Depends(get_current_user)]


def load_relations_query(load_relations: bool = Query(False,
                                 description='Carregar dados relacionados')):
    return load_relations


LoadRelationsDep = Annotated[bool, Depends(load_relations_query)]


@router.get('/por-codigo/{codigo_endereco}')
async def buscar_por_codigo(
    codigo_endereco: str,
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
    load_relations: LoadRelationsDep,
) -> Union[EnderecoRead, EnderecoReadComplete]:
    """
    Busca um endereço pelo código único
    
    * Requer autenticação
    * O código do endereço é um identificador único por endereço
    * Opcionalmente carrega dados relacionados como operadoras e detentora
    * Registra a busca para fins de auditoria
    * Retorna EnderecoReadComplete quando load_relations=True, caso contrário EnderecoRead
    """
    if load_relations:
        stmt = (
            select(Endereco)
            .where(Endereco.codigo_endereco == codigo_endereco)
            .options(
                selectinload(Endereco.operadoras).selectinload(
                    EnderecoOperadora.operadora
                ),
                selectinload(Endereco.detentora),
                selectinload(Endereco.alteracoes),
                selectinload(Endereco.anotacoes),
            )
        )
    else:
        stmt = select(Endereco).where(
            Endereco.codigo_endereco == codigo_endereco
        )

    endereco = await session.scalar(stmt)

    if not endereco:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endereço com código '{codigo_endereco}' não encontrado",
        )

    # Registrar a busca para auditoria
    busca_log = BuscaLog(
        usuario_id=current_user.id,
        endpoint='/enderecos/codigo/{codigo}',
        parametros=f'codigo={codigo_endereco}',
        tipo_busca=TipoBusca.por_id,
    )
    session.add(busca_log)

    # Filtra e processa anotações
    anotacoes_resumidas = []
    if load_relations:
        anotacoes_resumidas = await filtrar_anotacoes_por_acesso(
            endereco, current_user, session
        )

    await session.commit()

    # Retorna o endereço com base no parâmetro include_relations
    if load_relations:
        return endereco_to_schema(
            endereco,
            include_relations=True,
            anotacoes_resumidas=anotacoes_resumidas,
        )

    return endereco_to_schema(endereco, include_relations=False)


@router.get(
    '/por-operadora/{codigo_operadora}', response_model=List[EnderecoRead]
)
async def buscar_por_operadora(
    codigo_operadora: str,
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
):
    """
    Lista endereços de uma operadora específica

    * Requer autenticação
    * Busca pelo código da operadora
    * Os resultados são paginados
    * Registra a busca para fins de auditoria
    """
    stmt = (
        select(Endereco)
        .join(EnderecoOperadora)
        .join(Operadora)
        .where(EnderecoOperadora.codigo_operadora == codigo_operadora)
        .offset(skip)
        .limit(limit)
        .options(
            selectinload(Endereco.operadoras).selectinload(
                EnderecoOperadora.operadora
            ),
            selectinload(Endereco.detentora),
        )
    )

    result = await session.scalars(stmt)
    enderecos = list(result)

    # Registrar a busca para auditoria
    busca_log = BuscaLog(
        usuario_id=current_user.id,
        endpoint='/enderecos/operadora/{codigo}',
        parametros=f'codigo={codigo_operadora}',
        tipo_busca=TipoBusca.por_operadora,
    )
    session.add(busca_log)
    await session.commit()

    return enderecos


@router.get(
    '/por-detentora/{codigo_detentora}', response_model=List[EnderecoRead]
)
async def buscar_por_detentora(
    codigo_detentora: str,
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
):
    """
    Lista endereços de uma detentora específica

    * Requer autenticação
    * Busca pelo código da detentora
    * Os resultados são paginados
    * Registra a busca para fins de auditoria
    """
    stmt = (
        select(Endereco)
        .join(Detentora)
        .where(Detentora.codigo == codigo_detentora)
        .offset(skip)
        .limit(limit)
        .options(
            selectinload(Endereco.operadoras).selectinload(
                EnderecoOperadora.operadora
            ),
            selectinload(Endereco.detentora),
        )
    )

    result = await session.scalars(stmt)
    enderecos = list(result)

    # Registrar a busca para auditoria
    busca_log = BuscaLog(
        usuario_id=current_user.id,
        endpoint='/enderecos/detentora/{codigo}',
        parametros=f'codigo={codigo_detentora}',
        tipo_busca=TipoBusca.por_detentora,
    )
    session.add(busca_log)
    await session.commit()

    return enderecos
