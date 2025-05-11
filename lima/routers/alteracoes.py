from typing import List

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..models import Alteracao, NivelAcesso
from ..schemas import AlteracaoCreate, AlteracaoRead
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
    verificar_permissao_intermediaria,
)

router = APIRouter(prefix='/alteracoes', tags=['Alterações'])


@router.post(
    '/', response_model=AlteracaoRead, status_code=status.HTTP_201_CREATED
)
async def registrar_alteracao(
    alteracao: AlteracaoCreate,
    session: AsyncSessionDep,
    current_user: IntermediarioUserDep,
):
    """
    Registra uma alteração realizada em um endereço

    * Requer nível de acesso intermediário ou superior
    * Serve para documentar modificações importantes em dados de endereços
    * A alteração será associada ao usuário logado e ao endereço especificado

    **Exemplo de payload:**
    ```json
    {
      "id_endereco": 29,
      "id_usuario": 1,
      "tipo_alteracao": "atualizacao",
      "detalhe": "Atualização de coordenadas GPS para maior precisão"
    }
    ```

    Os tipos de alteração possíveis são:
    * **criacao**: Quando um novo endereço foi criado
    * **atualizacao**: Quando dados de um endereço foram atualizados
    * **exclusao**: Quando um endereço foi removido
    * **vinculo_operadora**: Quando uma operadora foi associada ao endereço
    * **remocao_operadora**: Quando uma operadora foi desvinculada do endereço
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


@router.get('/{alteracao_id}', response_model=AlteracaoRead)
async def obter_alteracao(
    alteracao_id: IdPathDep,
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
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
            detail='Alteração não encontrada',
        )

    # Usando função centralizada para verificar permissão
    verificar_permissao_basica(current_user, alteracao.id_usuario, 'alteração')

    return alteracao


@router.get('/', response_model=List[AlteracaoRead])
async def listar_alteracoes(
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
    skip: SkipQueryDep,
    limit: LimitQueryDep,
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


@router.delete('/{alteracao_id}', status_code=status.HTTP_204_NO_CONTENT)
async def deletar_alteracao(
    alteracao_id: IdPathDep,
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
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
            detail='Usuários básicos não podem remover alterações',
        )

    # Busca a alteração
    stmt = select(Alteracao).where(Alteracao.id == alteracao_id)
    result = await session.execute(stmt)
    alteracao = result.scalar_one_or_none()

    if alteracao is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Alteração não encontrada',
        )

    # Usando função centralizada para verificar permissão de usuários intermediários  # noqa: E501
    verificar_permissao_intermediaria(
        current_user, alteracao.id_usuario, 'alteração'
    )

    # Remove a alteração
    await session.delete(alteracao)
    await session.commit()
