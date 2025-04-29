"""
Estatísticas relacionadas a endereços.
"""

from typing import Annotated, Dict

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_async_session
from ...models import (
    Endereco,
    EnderecoOperadora,
    Operadora,
    Usuario,
)
from ...security import get_current_user

router = APIRouter()

# Definições de dependências usando Annotated
AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]
CurrentUserDep = Annotated[Usuario, Depends(get_current_user)]


@router.get('/estatisticas', response_model=Dict[str, int])
async def estatisticas_enderecos(
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
):
    """
    Retorna estatísticas sobre os endereços cadastrados

    * Requer autenticação
    * Todos os usuários podem acessar as estatísticas
    * Inclui contagens de endereços por estado, tipo, etc.
    """
    # Total de endereços
    total = await session.scalar(select(func.count()).select_from(Endereco))

    # Contagem por UF
    stmt_uf = select(Endereco.uf, func.count().label('total')).group_by(
        Endereco.uf
    )
    result_uf = await session.execute(stmt_uf)
    por_uf = {row.uf: row.total for row in result_uf}

    # Contagem por tipo
    stmt_tipo = select(Endereco.tipo, func.count().label('total')).group_by(
        Endereco.tipo
    )
    result_tipo = await session.execute(stmt_tipo)
    por_tipo = {row.tipo.value: row.total for row in result_tipo}

    # Contagem de endereços compartilhados
    total_compartilhados = await session.scalar(
        select(func.count())
        .select_from(Endereco)
        .where(Endereco.compartilhado)
    )

    # Contagem por operadora
    stmt_operadora = (
        select(Operadora.nome, func.count().label('total'))
        .join(EnderecoOperadora)
        .join(Endereco)
        .group_by(Operadora.nome)
    )
    result_operadora = await session.execute(stmt_operadora)
    por_operadora = {row.nome: row.total for row in result_operadora}

    return {
        'total': total,
        'por_uf': por_uf,
        'por_tipo': por_tipo,
        'compartilhados': total_compartilhados,
        'por_operadora': por_operadora,
    }
