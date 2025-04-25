from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_async_session
from ..models import Alteracao, NivelAcesso, Usuario
from ..schemas import AlteracaoCreate, AlteracaoRead

router = APIRouter(prefix="/alteracoes", tags=["Alterações"])

AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


async def verificar_permissao(session: AsyncSession, id_usuario: int) -> Usuario:
    """Verifica se o usuário tem permissão para acessar as alterações"""
    stmt = select(Usuario).where(Usuario.id == id_usuario)
    result = await session.execute(stmt)
    usuario = result.scalar_one_or_none()
    
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )
    
    if usuario.nivel_acesso not in [NivelAcesso.intermediario, NivelAcesso.super_usuario]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para gerenciar alterações",
        )
    
    return usuario


@router.post("/", response_model=AlteracaoRead, status_code=status.HTTP_201_CREATED)
async def criar_alteracao(
    alteracao: AlteracaoCreate,
    session: AsyncSessionDep,
):
    """
    Registra uma alteração no sistema
    
    - **id_endereco**: ID do endereço afetado
    - **id_usuario**: ID do usuário que está realizando a alteração
    - **tipo_alteracao**: Tipo da alteração (adicao, modificacao, remocao)
    - **detalhe**: Detalhes sobre a alteração (opcional)
    """
    # Verifica se o usuário existe e tem permissão
    await verificar_permissao(session, alteracao.id_usuario)
    
    # Cria a nova alteração
    db_alteracao = Alteracao(
        id_endereco=alteracao.id_endereco,
        id_usuario=alteracao.id_usuario,
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
):
    """
    Retorna os detalhes de uma alteração específica
    
    - **alteracao_id**: ID da alteração a ser consultada
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
    
    return alteracao


@router.get("/", response_model=List[AlteracaoRead])
async def listar_alteracoes(
    session: AsyncSessionDep,
    skip: int = 0, 
    limit: int = 100,
):
    """
    Lista todas as alterações com paginação
    
    - **skip**: Quantidade de registros para pular (padrão: 0)
    - **limit**: Limite de registros para retornar (padrão: 100)
    """
    stmt = (
        select(Alteracao)
        .options(
            selectinload(Alteracao.usuario),
            selectinload(Alteracao.endereco),
        )
        .offset(skip)
        .limit(limit)
    )
    
    result = await session.execute(stmt)
    alteracoes = result.scalars().all()
    
    return alteracoes


@router.delete("/{alteracao_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_alteracao(
    alteracao_id: int,
    id_usuario: int,
    session: AsyncSessionDep,
):
    """
    Remove uma alteração do sistema (apenas super_usuario)
    
    - **alteracao_id**: ID da alteração a ser removida
    - **id_usuario**: ID do usuário que está solicitando a remoção
    """
    # Verifica se é super_usuario
    usuario = await verificar_permissao(session, id_usuario)
    if usuario.nivel_acesso != NivelAcesso.super_usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas super usuários podem remover alterações",
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
    
    # Remove a alteração
    await session.delete(alteracao)
    await session.commit()
    
    return None
