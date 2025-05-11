from typing import List

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from ..models import (
    NivelAcesso,
    StatusSugestao,
    Sugestao,
)
from ..schemas import SugestaoCreate, SugestaoRead
from ..utils.dependencies import (
    AsyncSessionDep,
    CurrentUserDep,
    IdPathDep,
    IntermediarioUserDep,
    LimitQueryDep,
    SkipQueryDep,
)
from ..utils.permissions import (
    verificar_permissao_basica,
    verificar_permissao_recurso_processado,
)

router = APIRouter(prefix='/sugestoes', tags=['Sugestões'])


@router.post(
    '/', response_model=SugestaoRead, status_code=status.HTTP_201_CREATED
)
async def criar_sugestao(
    sugestao: SugestaoCreate,
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
):
    """
    Cadastra uma nova sugestão de alteração de endereço

    * Requer autenticação (usuário básico ou superior)
    * A sugestão será associada ao usuário logado
    * Entra no fluxo de aprovação com status inicial 'pendente'
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


@router.get('/{sugestao_id}', response_model=SugestaoRead)
async def obter_sugestao(
    sugestao_id: IdPathDep,
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
):
    """
    Retorna os detalhes de uma sugestão específica

    * Requer autenticação
    * Usuários básicos só podem acessar suas próprias sugestões
    * Usuários intermediários e super_usuários podem ver todas as sugestões
    """
    stmt = (
        select(Sugestao)
        .where(Sugestao.id == sugestao_id)
        .options(
            joinedload(Sugestao.usuario),
            joinedload(Sugestao.endereco),
        )
    )

    result = await session.execute(stmt)
    sugestao = result.scalar_one_or_none()

    if not sugestao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Sugestão não encontrada',
        )

    # Usando função centralizada para verificar permissão
    verificar_permissao_basica(current_user, sugestao.id_usuario, 'sugestão')

    return sugestao


@router.get('/', response_model=List[SugestaoRead])
async def listar_sugestoes(
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
    skip: SkipQueryDep,
    limit: LimitQueryDep,
):
    """
    Lista sugestões com paginação

    * Requer autenticação
    * Usuários básicos só veem suas próprias sugestões
    * Usuários intermediários e super_usuários veem todas as sugestões
    """
    # Base query
    query = select(Sugestao).options(
        joinedload(Sugestao.usuario),
        joinedload(Sugestao.endereco),
    )

    # Restrição para usuários básicos
    if current_user.nivel_acesso == NivelAcesso.basico:
        query = query.where(Sugestao.id_usuario == current_user.id)

    # Aplica paginação
    query = query.offset(skip).limit(limit)

    result = await session.execute(query)
    sugestoes = result.scalars().all()

    return sugestoes


@router.put('/{sugestao_id}/aprovar', response_model=SugestaoRead)
async def aprovar_sugestao(
    sugestao_id: IdPathDep,
    session: AsyncSessionDep,
    current_user: IntermediarioUserDep,
):
    """
    Aprova uma sugestão

    * Requer nível de acesso intermediário ou superior
    * Altera o status da sugestão para 'aprovada'
    * Registra o usuário que realizou a aprovação
    """
    stmt = select(Sugestao).where(Sugestao.id == sugestao_id)
    result = await session.execute(stmt)
    sugestao = result.scalar_one_or_none()

    if not sugestao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Sugestão não encontrada',
        )

    # Altera o status para aprovado
    sugestao.status = StatusSugestao.aprovado

    # Aqui você pode implementar a lógica para aplicar a sugestão
    # Exemplo: Se for uma sugestão de adição, criar um novo endereço

    await session.commit()
    await session.refresh(sugestao)

    return sugestao


@router.put('/{sugestao_id}/rejeitar', response_model=SugestaoRead)
async def rejeitar_sugestao(
    sugestao_id: IdPathDep,
    session: AsyncSessionDep,
    current_user: IntermediarioUserDep,
):
    """
    Rejeita uma sugestão

    * Requer nível de acesso intermediário ou superior
    * Altera o status da sugestão para 'rejeitada'
    * Registra o usuário que realizou a rejeição
    """
    stmt = select(Sugestao).where(Sugestao.id == sugestao_id)
    result = await session.execute(stmt)
    sugestao = result.scalar_one_or_none()

    if not sugestao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Sugestão não encontrada',
        )

    # Altera o status para rejeitado
    sugestao.status = StatusSugestao.rejeitado
    await session.commit()
    await session.refresh(sugestao)

    return sugestao


@router.delete('/{sugestao_id}', status_code=status.HTTP_204_NO_CONTENT)
async def deletar_sugestao(
    sugestao_id: IdPathDep,
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
):
    """
    Remove uma sugestão

    * Usuários básicos só podem remover suas próprias sugestões pendentes
    * Usuários intermediários só podem remover sugestões pendentes
    * Super-usuários podem remover qualquer sugestão
    """
    # Localiza a sugestão
    stmt = select(Sugestao).where(Sugestao.id == sugestao_id)
    result = await session.execute(stmt)
    sugestao = result.scalar_one_or_none()

    if not sugestao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Sugestão não encontrada',
        )

    # Usando função centralizada para verificar permissão básica
    if current_user.nivel_acesso == NivelAcesso.basico:
        verificar_permissao_basica(
            current_user, sugestao.id_usuario, 'sugestão'
        )

        # Usando função centralizada para verificar se o recurso já foi processado  # noqa: E501
        verificar_permissao_recurso_processado(
            current_user, sugestao.status, StatusSugestao.pendente, 'sugestão'
        )
    elif current_user.nivel_acesso == NivelAcesso.intermediario:
        # Usando função centralizada para verificar se o recurso já foi processado  # noqa: E501
        verificar_permissao_recurso_processado(
            current_user, sugestao.status, StatusSugestao.pendente, 'sugestão'
        )
    # Super-usuários podem deletar qualquer sugestão

    # Remove a sugestão
    await session.delete(sugestao)
    await session.commit()
