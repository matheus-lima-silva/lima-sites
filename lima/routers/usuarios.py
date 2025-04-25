from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..schemas import UsuarioCreate, UsuarioRead

router = APIRouter(prefix="/usuarios", tags=["Usuários"])

AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


@router.post("/", response_model=UsuarioRead)
async def criar_usuario(
    usuario: UsuarioCreate,
    session: AsyncSessionDep,
):
    # Implementação de criação de usuário
    raise NotImplementedError


@router.get("/{usuario_id}", response_model=UsuarioRead)
async def obter_usuario(
    usuario_id: int,
    session: AsyncSessionDep,
):
    # Implementação de busca de usuário
    raise NotImplementedError
