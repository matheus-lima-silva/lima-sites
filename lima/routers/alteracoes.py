from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_async_session
from ..models import Alteracao, NivelAcesso, Usuario
from ..schemas import AlteracaoCreate, AlteracaoRead
from ..security import get_current_user, require_intermediario

router = APIRouter(prefix="/alteracoes", tags=["Alterações"])

AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


@router.post("/", response_model=AlteracaoRead, status_code=status.HTTP_201_CREATED)
async def criar_alteracao(
    alteracao: AlteracaoCreate,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(require_intermediario),  # Requer nível intermediário ou superior
):
    """
    Registra uma alteração no sistema
    
    * Requer nível de acesso intermediário ou superior
    * A alteração será associada ao usuário logado
    """
    # Cria a nova alteração associando ao usuário atual
    db_alteracao = Alteracao(
        id_endereco=alteracao.id_endereco,
        id_usuario=current_user.id,  # Usa ID do usuário logado
        tipo_alteracao=alteracao.tipo_alteracao,
        detalhe=alteracao.detalhe,
    )
    
    session.add(db_alteracao)
    await session.commit()
    await session.refresh(db_alteracao)
    
    return db_alteracao


@router.get("/{alteracao_id}", response_model=AlteracaoRead)
async def obter_alteracao(
    alteracao_id: int,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(get_current_user),
):
    """
    Retorna os detalhes de uma alteração específica
    
    * Requer autenticação
    * Usuários básicos só podem acessar suas próprias alterações
    * Usuários intermediários e super_usuários podem ver todas as alterações
    """
    stmt = (
        select(Alteracao)
        .where(Alteracao.id == alteracao_id)
        .options(
            selectinload(Alteracao.usuario),
            selectinload(Alteracao.endereco),
        )
    )
    
    result = await session.execute(stmt)
    alteracao = result.scalar_one_or_none()
    
    if alteracao is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alteração não encontrada",
        )
    
    # Verifica permissão: usuários básicos só podem ver suas próprias alterações
    if (current_user.nivel_acesso == NivelAcesso.basico and 
            alteracao.id_usuario != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para acessar esta alteração",
        )
    
    return alteracao


@router.get("/", response_model=List[AlteracaoRead])
async def listar_alteracoes(
    session: AsyncSessionDep,
    skip: int = 0, 
    limit: int = 100,
    current_user: Usuario = Depends(get_current_user),
):
    """
    Lista todas as alterações com paginação
    
    * Requer autenticação
    * Usuários básicos só veem suas próprias alterações
    * Usuários intermediários e super_usuários veem todas as alterações
    """
    # Base query
    query = select(Alteracao).options(
        selectinload(Alteracao.usuario),
        selectinload(Alteracao.endereco),
    )
    
    # Restrição para usuários básicos
    if current_user.nivel_acesso == NivelAcesso.basico:
        query = query.where(Alteracao.id_usuario == current_user.id)
    
    # Aplica paginação
    query = query.offset(skip).limit(limit)
    
    result = await session.execute(query)
    alteracoes = result.scalars().all()
    
    return alteracoes


@router.delete("/{alteracao_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_alteracao(
    alteracao_id: int,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(get_current_user),
):
    """
    Remove uma alteração do sistema
    
    * Usuários básicos não podem remover alterações
    * Usuários intermediários podem remover apenas suas próprias alterações
    * Super-usuários podem remover qualquer alteração
    """
    # Verifica nível de acesso básico
    if current_user.nivel_acesso == NivelAcesso.basico:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuários básicos não podem remover alterações",
        )
    
    # Busca a alteração
    stmt = select(Alteracao).where(Alteracao.id == alteracao_id)
    result = await session.execute(stmt)
    alteracao = result.scalar_one_or_none()
    
    if alteracao is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alteração não encontrada",
        )
    
    # Verifica permissão para usuários intermediários
    if (current_user.nivel_acesso == NivelAcesso.intermediario and 
            alteracao.id_usuario != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuários intermediários só podem remover suas próprias alterações",
        )
    
    # Remove a alteração
    await session.delete(alteracao)
    await session.commit()
    
    return None
