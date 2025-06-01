"""
Operações auxiliares relacionadas a endereços,
 como listar operadoras e detentoras.
"""

from typing import List

from fastapi import APIRouter
from sqlalchemy import select

from ....models import (
    Detentora,
    Operadora,
)
from ....schemas import DetentoraRead, OperadoraRead
from ....utils.dependencies import AsyncSessionDep, CurrentUserDep

router = APIRouter()


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
