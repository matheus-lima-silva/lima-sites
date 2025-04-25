from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..schemas import EnderecoCreate, EnderecoRead

router = APIRouter(prefix="/enderecos", tags=["Endereços"])

AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


@router.post("/", response_model=EnderecoRead)
async def criar_endereco(
    endereco: EnderecoCreate,
    session: AsyncSessionDep,
):
    # Implementação de criação de endereço
    raise NotImplementedError


@router.get("/{endereco_id}", response_model=EnderecoRead)
async def obter_endereco(
    endereco_id: int,
    session: AsyncSessionDep,
):
    # Implementação de busca de endereço
    raise NotImplementedError
