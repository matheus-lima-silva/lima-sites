from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..schemas import SugestaoCreate, SugestaoRead

router = APIRouter(prefix="/sugestoes", tags=["Sugestões"])

AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


@router.post("/", response_model=SugestaoRead)
async def criar_sugestao(
    sugestao: SugestaoCreate,
    session: AsyncSessionDep,
):
    # Implementação de criação de sugestão
    raise NotImplementedError


@router.get("/{sugestao_id}", response_model=SugestaoRead)
async def obter_sugestao(
    sugestao_id: int,
    session: AsyncSessionDep,
):
    # Implementação de busca de sugestão
    raise NotImplementedError
