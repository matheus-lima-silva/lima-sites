"""
Operações auxiliares relacionadas a endereços,
 como listar operadoras e detentoras.
"""

from typing import Annotated, List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....database import get_async_session
from ....models import (
    Detentora,
    Operadora,
    Usuario,
)
from ....schemas import DetentoraRead, OperadoraRead
from ....security import get_current_user

router = APIRouter()

# Definição de dependências com Annotated
AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]
CurrentUserDep = Annotated[Usuario, Depends(get_current_user)]


@router.get('/operadoras/listar', response_model=List[OperadoraRead])
async def listar_operadoras(
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
):
    """
    Lista todas as operadoras cadastradas

    * Requer autenticação
    * Todos os usuários podem consultar a lista de operadoras
    """
    stmt = select(Operadora)
    result = await session.scalars(stmt)
    return list(result)


@router.get('/detentoras/listar', response_model=List[DetentoraRead])
async def listar_detentoras(
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
):
    """
    Lista todas as detentoras cadastradas

    * Requer autenticação
    * Todos os usuários podem consultar a lista de detentoras
    """
    stmt = select(Detentora)
    result = await session.scalars(stmt)
    return list(result)
