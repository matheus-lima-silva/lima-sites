from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..schemas import BuscaCreate, BuscaRead

router = APIRouter(prefix="/buscas", tags=["Buscas"])

AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


@router.post("/", response_model=BuscaRead)
async def registrar_busca(
    busca: BuscaCreate,
    session: AsyncSessionDep,
):
    # Implementação de registro de busca
    raise NotImplementedError


@router.get("/{busca_id}", response_model=BuscaRead)
async def obter_busca(
    busca_id: int,
    session: AsyncSessionDep,
):
    # Implementação de busca de registro de busca
    raise NotImplementedError
