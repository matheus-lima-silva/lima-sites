from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_async_session
from ..models import Busca, NivelAcesso
from ..schemas import BuscaCreate, BuscaRead
from ..security import Usuario, get_current_user

router = APIRouter(prefix="/buscas", tags=["Buscas"])

AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


@router.post("/", response_model=BuscaRead, status_code=status.HTTP_201_CREATED)
async def registrar_busca(
    busca: BuscaCreate,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(get_current_user),
):
    """
    Registra uma nova busca feita pelo usuário
    
    * Requer autenticação
    * A busca será associada ao usuário logado
    """
    # Cria a nova busca associando-a ao usuário atual
    db_busca = Busca(
        id_endereco=busca.id_endereco,
        id_usuario=current_user.id,  # Usa ID do usuário logado
        info_adicional=busca.info_adicional,
    )

    session.add(db_busca)
    await session.commit()
    await session.refresh(db_busca)

    return db_busca


@router.get("/{busca_id}", response_model=BuscaRead)
async def obter_busca(
    busca_id: int,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(get_current_user),
):
    """
    Recupera detalhes de uma busca específica
    
    * Requer autenticação
    * Usuários básicos só podem acessar suas próprias buscas
    * Usuários intermediários e super_usuários podem ver todas as buscas
    """
    stmt = (
        select(Busca)
        .where(Busca.id == busca_id)
        .options(
            selectinload(Busca.usuario),
            selectinload(Busca.endereco),
        )
    )

    result = await session.execute(stmt)
    busca = result.scalar_one_or_none()

    if not busca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Busca não encontrada",
        )

    # Verifica permissão: usuários básicos só podem ver suas próprias buscas
    if (current_user.nivel_acesso == NivelAcesso.basico and
            busca.id_usuario != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para acessar esta busca",
        )

    return busca


@router.get("/", response_model=List[BuscaRead])
async def listar_buscas(
    session: AsyncSessionDep,
    skip: int = 0,
    limit: int = 100,
    current_user: Usuario = Depends(get_current_user),
):
    """
    Lista buscas com paginação
    
    * Requer autenticação
    * Usuários básicos só veem suas próprias buscas
    * Usuários intermediários e super_usuários veem todas as buscas
    """
    # Base query
    query = select(Busca).options(
        selectinload(Busca.usuario),
        selectinload(Busca.endereco),
    )

    # Restrição para usuários básicos
    if current_user.nivel_acesso == NivelAcesso.basico:
        query = query.where(Busca.id_usuario == current_user.id)

    # Aplica paginação
    query = query.offset(skip).limit(limit)

    result = await session.execute(query)
    buscas = result.scalars().all()

    return buscas


@router.delete("/{busca_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_busca(
    busca_id: int,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(get_current_user),
):
    """
    Remove uma busca do histórico
    
    * Usuários básicos só podem deletar suas próprias buscas
    * Usuários intermediários não podem deletar buscas
    * Super-usuários podem deletar qualquer busca
    """
    # Localiza a busca
    stmt = select(Busca).where(Busca.id == busca_id)
    result = await session.execute(stmt)
    busca = result.scalar_one_or_none()

    if not busca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Busca não encontrada",
        )

    # Verifica permissão
    if current_user.nivel_acesso == NivelAcesso.basico:
        if busca.id_usuario != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sem permissão para deletar esta busca",
            )
    elif current_user.nivel_acesso == NivelAcesso.intermediario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuários de nível intermediário não podem deletar buscas",
        )
    # Super-usuários podem deletar qualquer busca

    # Remove a busca
    await session.delete(busca)
    await session.commit()
