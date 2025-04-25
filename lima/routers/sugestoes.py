from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_async_session
from ..models import Sugestao, NivelAcesso
from ..schemas import SugestaoCreate, SugestaoRead
from ..security import get_current_user, require_intermediario, Usuario

router = APIRouter(prefix="/sugestoes", tags=["Sugestões"])

AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


@router.post("/", response_model=SugestaoRead, status_code=status.HTTP_201_CREATED)
async def criar_sugestao(
    sugestao: SugestaoCreate,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(get_current_user),
):
    """
    Cria uma nova sugestão de alteração ou adição de endereço
    
    * Requer autenticação
    * A sugestão será associada ao usuário logado
    """
    # Cria a nova sugestão associando ao usuário atual
    db_sugestao = Sugestao(
        id_endereco=sugestao.id_endereco,
        id_usuario=current_user.id,  # Usa ID do usuário logado
        tipo_sugestao=sugestao.tipo_sugestao,
        detalhe=sugestao.detalhe,
    )
    
    session.add(db_sugestao)
    await session.commit()
    await session.refresh(db_sugestao)
    
    return db_sugestao


@router.get("/{sugestao_id}", response_model=SugestaoRead)
async def obter_sugestao(
    sugestao_id: int,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(get_current_user),
):
    """
    Recupera detalhes de uma sugestão específica
    
    * Requer autenticação
    * Usuários básicos só podem acessar suas próprias sugestões
    * Usuários intermediários e super_usuários podem ver todas as sugestões
    """
    stmt = (
        select(Sugestao)
        .where(Sugestao.id == sugestao_id)
        .options(
            selectinload(Sugestao.usuario),
            selectinload(Sugestao.endereco),
        )
    )
    
    result = await session.execute(stmt)
    sugestao = result.scalar_one_or_none()
    
    if not sugestao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sugestão não encontrada",
        )
    
    # Verifica permissão: usuários básicos só podem ver suas próprias sugestões
    if (current_user.nivel_acesso == NivelAcesso.basico and 
            sugestao.id_usuario != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para acessar esta sugestão",
        )
    
    return sugestao


@router.get("/", response_model=List[SugestaoRead])
async def listar_sugestoes(
    session: AsyncSessionDep,
    skip: int = 0, 
    limit: int = 100,
    current_user: Usuario = Depends(get_current_user),
):
    """
    Lista sugestões com paginação
    
    * Requer autenticação
    * Usuários básicos só veem suas próprias sugestões
    * Usuários intermediários e super_usuários veem todas as sugestões
    """
    # Base query
    query = select(Sugestao).options(
        selectinload(Sugestao.usuario),
        selectinload(Sugestao.endereco),
    )
    
    # Restrição para usuários básicos
    if current_user.nivel_acesso == NivelAcesso.basico:
        query = query.where(Sugestao.id_usuario == current_user.id)
    
    # Aplica paginação
    query = query.offset(skip).limit(limit)
    
    result = await session.execute(query)
    sugestoes = result.scalars().all()
    
    return sugestoes


@router.put("/{sugestao_id}/aprovar", response_model=SugestaoRead)
async def aprovar_sugestao(
    sugestao_id: int,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(require_intermediario),  # Requer nível intermediário ou superior
):
    """
    Aprova uma sugestão de alteração
    
    * Requer nível de acesso intermediário ou superior
    """
    stmt = select(Sugestao).where(Sugestao.id == sugestao_id)
    result = await session.execute(stmt)
    sugestao = result.scalar_one_or_none()
    
    if not sugestao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sugestão não encontrada",
        )
    
    # Altera o status para aprovado
    from ..models import StatusSugestao
    sugestao.status = StatusSugestao.aprovado
    
    # Aqui você pode implementar a lógica para aplicar a sugestão
    # Exemplo: Se for uma sugestão de adição, criar um novo endereço
    
    await session.commit()
    await session.refresh(sugestao)
    
    return sugestao


@router.put("/{sugestao_id}/rejeitar", response_model=SugestaoRead)
async def rejeitar_sugestao(
    sugestao_id: int,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(require_intermediario),  # Requer nível intermediário ou superior
):
    """
    Rejeita uma sugestão de alteração
    
    * Requer nível de acesso intermediário ou superior
    """
    stmt = select(Sugestao).where(Sugestao.id == sugestao_id)
    result = await session.execute(stmt)
    sugestao = result.scalar_one_or_none()
    
    if not sugestao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sugestão não encontrada",
        )
    
    # Altera o status para rejeitado
    from ..models import StatusSugestao
    sugestao.status = StatusSugestao.rejeitado
    
    await session.commit()
    await session.refresh(sugestao)
    
    return sugestao


@router.delete("/{sugestao_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_sugestao(
    sugestao_id: int,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(get_current_user),
):
    """
    Remove uma sugestão
    
    * Usuários básicos só podem deletar suas próprias sugestões pendentes
    * Usuários intermediários podem deletar qualquer sugestão pendente
    * Super-usuários podem deletar qualquer sugestão
    """
    # Localiza a sugestão
    stmt = select(Sugestao).where(Sugestao.id == sugestao_id)
    result = await session.execute(stmt)
    sugestao = result.scalar_one_or_none()
    
    if not sugestao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sugestão não encontrada",
        )
    
    # Verifica permissão
    from ..models import StatusSugestao
    
    if current_user.nivel_acesso == NivelAcesso.basico:
        if sugestao.id_usuario != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sem permissão para deletar esta sugestão",
            )
        if sugestao.status != StatusSugestao.pendente:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Não é possível deletar sugestões que já foram processadas",
            )
    elif current_user.nivel_acesso == NivelAcesso.intermediario:
        if sugestao.status != StatusSugestao.pendente:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuários intermediários só podem deletar sugestões pendentes",
            )
    # Super-usuários podem deletar qualquer sugestão
    
    # Remove a sugestão
    await session.delete(sugestao)
    await session.commit()
    
    return None
