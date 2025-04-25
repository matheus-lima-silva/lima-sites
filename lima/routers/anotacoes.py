from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_async_session
from ..models import Anotacao, Endereco, NivelAcesso, Usuario
from ..schemas import AnotacaoCreate, AnotacaoRead, AnotacaoUpdate
from ..security import get_current_user, require_intermediario, require_super_usuario

router = APIRouter(prefix="/anotacoes", tags=["Anotações"])

AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


@router.post("/", response_model=AnotacaoRead, status_code=status.HTTP_201_CREATED)
async def criar_anotacao(
    anotacao: AnotacaoCreate,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(get_current_user),
):
    """
    Cria uma nova anotação para um endereço
    
    * Requer autenticação
    * Qualquer usuário pode adicionar anotações
    * O id_usuario será automaticamente atribuído ao usuário atual
    """
    # Verifica se o endereço existe
    stmt = select(Endereco).where(Endereco.id == anotacao.id_endereco)
    result = await session.execute(stmt)
    endereco = result.scalar_one_or_none()
    
    if not endereco:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endereço não encontrado",
        )
    
    # Sobrescreve o id_usuario com o ID do usuário autenticado
    db_anotacao = Anotacao(
        id_endereco=anotacao.id_endereco,
        id_usuario=current_user.id,
        texto=anotacao.texto,
    )
    
    session.add(db_anotacao)
    await session.commit()
    await session.refresh(db_anotacao)
    
    return db_anotacao


@router.get("/{anotacao_id}", response_model=AnotacaoRead)
async def obter_anotacao(
    anotacao_id: int,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(get_current_user),
):
    """
    Recupera detalhes de uma anotação específica
    
    * Requer autenticação
    * Usuários básicos só podem ver suas próprias anotações
    * Usuários intermediários e super_usuários podem ver todas as anotações
    """
    stmt = select(Anotacao).where(Anotacao.id == anotacao_id)
    result = await session.execute(stmt)
    anotacao = result.scalar_one_or_none()
    
    if not anotacao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anotação não encontrada",
        )
    
    # Verifica permissões: usuários básicos só podem ver suas próprias anotações
    if current_user.nivel_acesso == NivelAcesso.basico and anotacao.id_usuario != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Não autorizado a ver esta anotação",
        )
    
    return anotacao


@router.get("/endereco/{endereco_id}", response_model=List[AnotacaoRead])
async def listar_anotacoes_do_endereco(
    endereco_id: int,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(get_current_user),
):
    """
    Lista todas as anotações de um endereço específico
    
    * Requer autenticação
    * Usuários básicos só veem suas próprias anotações
    * Usuários intermediários e super_usuários veem todas as anotações
    """
    # Verifica se o endereço existe
    stmt_endereco = select(Endereco).where(Endereco.id == endereco_id)
    result_endereco = await session.execute(stmt_endereco)
    endereco = result_endereco.scalar_one_or_none()
    
    if not endereco:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endereço não encontrado",
        )
    
    # Filtra anotações com base no nível de acesso
    if current_user.nivel_acesso == NivelAcesso.basico:
        # Usuários básicos só veem suas próprias anotações
        stmt = (
            select(Anotacao)
            .where(Anotacao.id_endereco == endereco_id, Anotacao.id_usuario == current_user.id)
        )
    else:
        # Usuários com maior privilégio veem todas as anotações
        stmt = select(Anotacao).where(Anotacao.id_endereco == endereco_id)
    
    result = await session.execute(stmt)
    anotacoes = result.scalars().all()
    
    return anotacoes


@router.get("/usuario/minhas", response_model=List[AnotacaoRead])
async def listar_minhas_anotacoes(
    session: AsyncSessionDep,
    current_user: Usuario = Depends(get_current_user),
):
    """
    Lista todas as anotações feitas pelo usuário atual
    
    * Requer autenticação
    """
    stmt = select(Anotacao).where(Anotacao.id_usuario == current_user.id)
    result = await session.execute(stmt)
    anotacoes = result.scalars().all()
    
    return anotacoes


@router.put("/{anotacao_id}", response_model=AnotacaoRead)
async def atualizar_anotacao(
    anotacao_id: int,
    anotacao_update: AnotacaoUpdate,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(get_current_user),
):
    """
    Atualiza uma anotação existente
    
    * Requer autenticação
    * Usuários básicos só podem atualizar suas próprias anotações
    * Usuários intermediários e super_usuários podem atualizar qualquer anotação
    """
    stmt = select(Anotacao).where(Anotacao.id == anotacao_id)
    result = await session.execute(stmt)
    db_anotacao = result.scalar_one_or_none()
    
    if not db_anotacao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anotação não encontrada",
        )
    
    # Verifica permissões: usuários básicos só podem atualizar suas próprias anotações
    if current_user.nivel_acesso == NivelAcesso.basico and db_anotacao.id_usuario != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Não autorizado a atualizar esta anotação",
        )
    
    # Atualiza os campos da anotação
    db_anotacao.texto = anotacao_update.texto
    
    await session.commit()
    await session.refresh(db_anotacao)
    
    return db_anotacao


@router.delete("/{anotacao_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_anotacao(
    anotacao_id: int,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(get_current_user),
):
    """
    Remove uma anotação
    
    * Requer autenticação
    * Usuários básicos só podem remover suas próprias anotações
    * Usuários intermediários e super_usuários podem remover qualquer anotação
    """
    stmt = select(Anotacao).where(Anotacao.id == anotacao_id)
    result = await session.execute(stmt)
    anotacao = result.scalar_one_or_none()
    
    if not anotacao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anotação não encontrada",
        )
    
    # Verifica permissões: usuários básicos só podem deletar suas próprias anotações
    if current_user.nivel_acesso == NivelAcesso.basico and anotacao.id_usuario != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Não autorizado a remover esta anotação",
        )
    
    await session.delete(anotacao)
    await session.commit()
    
    return None