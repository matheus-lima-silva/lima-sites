from datetime import datetime, timezone
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.orm import joinedload, selectinload

from ..models import Anotacao, Endereco, NivelAcesso
from ..schemas import AnotacaoCreate, AnotacaoRead, AnotacaoUpdate
from ..utils.decorators import (
    handle_not_found,
    log_operation,
    require_permission,
)
from ..utils.dependencies import (
    AsyncSessionDep,
    CurrentUserDep,
    IdPathDep,
    LimitQueryDep,
    OrderDescQueryDep,
    SkipQueryDep,
    create_order_by_dependency,
)
from ..utils.resource_validators import get_resource_or_none

router = APIRouter(prefix='/anotacoes', tags=['Anotações'])

# Usando a função auxiliar para criar uma dependência de ordenação específica para anotações  # noqa: E501
AnotacaoOrderByDep = create_order_by_dependency(
    'data_criacao', ['data_criacao', 'data_atualizacao']
)


class ListagemParams(BaseModel):
    """Parâmetros para listagem de anotações."""

    order_by: str = Field(
        default='data_criacao',
        description='Campo para ordenação (data_criacao, data_atualizacao)',
    )
    desc: bool = Field(default=True, description='Ordenação decrescente')
    skip: int = Field(default=0, description='Número de registros a pular')
    limit: int = Field(default=100, description='Número máximo de registros')


# O restante do código permanece o mesmo, mas podemos usar as novas dependências  # noqa: E501
# nos endpoints existentes.


@router.post(
    '/', response_model=AnotacaoRead, status_code=status.HTTP_201_CREATED
)
async def criar_anotacao(
    anotacao: AnotacaoCreate,
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
):
    """
    Cria uma nova anotação para um endereço

    * Requer autenticação
    * Qualquer usuário pode criar anotações
    * A anotação será associada ao usuário logado e ao endereço especificado

    **Exemplo de payload:**
    ```json
    {
      "id_endereco": 29,
      "id_usuario": 1,
      "texto": "Este endereço foi
        verificado pessoalmente e confirmado como correto."
    }
    ```

    As anotações são úteis para registrar informações
    adicionais sobre um endereço que não fazem parte
    dos dados estruturados, como observações de campo,
    dificuldades de acesso, contatos locais, etc.
    """
    async with session.begin():  # Usando transação explícita
        # Verifica se o endereço existe usando método get otimizado
        endereco = await session.get(Endereco, anotacao.id_endereco)

        if not endereco:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Endereço não encontrado',
            )

        # Sobrescreve o id_usuario com o ID do usuário autenticado
        db_anotacao = Anotacao(
            id_endereco=anotacao.id_endereco,
            id_usuario=current_user.id,
            texto=anotacao.texto,
        )

        session.add(db_anotacao)

    # Carrega a anotação com as relações para retorno
    await session.refresh(db_anotacao, ['endereco', 'usuario'])
    return db_anotacao


# Rotas específicas devem vir antes das genéricas com parâmetros
@router.get('/usuario/minhas', response_model=List[AnotacaoRead])
async def listar_minhas_anotacoes(
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
    query_params: Annotated[
        dict,
        Depends(
            lambda order_by=AnotacaoOrderByDep,
            desc=OrderDescQueryDep,
            skip=SkipQueryDep,
            limit=LimitQueryDep: {
                'order_by': order_by,
                'desc': desc,
                'skip': skip,
                'limit': limit,
            }
        ),
    ],
):
    """
    Lista todas as anotações feitas pelo usuário atual

    * Requer autenticação
    * Suporta paginação e ordenação
    """
    # Extrair parâmetros do dicionário
    order_by = query_params['order_by']
    desc = query_params['desc']
    skip = query_params['skip']
    limit = query_params['limit']

    # Construir ordenação conforme parâmetros
    if order_by == 'data_atualizacao':
        order_field = Anotacao.data_atualizacao
    else:
        order_field = Anotacao.data_criacao

    # Aplicar direção da ordenação
    order_clause = order_field.desc() if desc else order_field.asc()

    # Consulta com eager loading
    stmt = (
        select(Anotacao)
        .options(joinedload(Anotacao.endereco))
        .where(Anotacao.id_usuario == current_user.id)
        .order_by(order_clause)
        .offset(skip)
        .limit(limit)
    )

    anotacoes = await session.scalars(stmt)
    return list(anotacoes)


@router.get('/endereco/{endereco_id}', response_model=List[AnotacaoRead])
async def listar_anotacoes_do_endereco(
    endereco_id: int,
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
    query_params: Annotated[
        dict,
        Depends(
            lambda order_by=AnotacaoOrderByDep, desc=OrderDescQueryDep: {
                'order_by': order_by,
                'desc': desc,
            }
        ),
    ],
):
    """
    Lista todas as anotações de um endereço específico

    * Requer autenticação
    * Usuários básicos só veem suas próprias anotações
    * Usuários intermediários e super_usuários veem todas as anotações
    """
    # Extrair parâmetros do dicionário
    order_by = query_params['order_by']
    desc = query_params['desc']

    # Verifica se o endereço existe usando método get otimizado
    endereco = await session.get(Endereco, endereco_id)

    if not endereco:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Endereço não encontrado',
        )

    # Construir ordenação
    if order_by == 'data_atualizacao':
        order_field = Anotacao.data_atualizacao
    else:
        order_field = Anotacao.data_criacao

    order_clause = order_field.desc() if desc else order_field.asc()

    # Filtra anotações com base no nível de acesso
    if current_user.nivel_acesso == NivelAcesso.basico:
        # Usuários básicos só veem suas próprias anotações
        stmt = (
            select(Anotacao)
            .options(joinedload(Anotacao.usuario))
            .where(
                and_(
                    Anotacao.id_endereco == endereco_id,
                    Anotacao.id_usuario == current_user.id,
                )
            )
            .order_by(order_clause)
        )
    else:
        # Usuários com maior privilégio veem todas as anotações
        stmt = (
            select(Anotacao)
            .options(joinedload(Anotacao.usuario))
            .where(Anotacao.id_endereco == endereco_id)
            .order_by(order_clause)
        )

    anotacoes = await session.scalars(stmt)
    return list(anotacoes)


@router.get('/busca', response_model=List[AnotacaoRead])
async def buscar_anotacoes(
    query: str,
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
):
    """
    Busca anotações por texto

    * Requer autenticação
    * Utiliza recursos de busca textual do PostgreSQL
    * Usuários básicos só veem suas próprias anotações
    """
    # Construir consulta com base no nível de acesso
    if current_user.nivel_acesso == NivelAcesso.basico:
        stmt = (
            select(Anotacao)
            .options(joinedload(Anotacao.endereco))
            .where(
                and_(
                    Anotacao.id_usuario == current_user.id,
                    Anotacao.texto.ilike(f'%{query}%'),
                )
            )
            .order_by(Anotacao.data_atualizacao.desc())
            .limit(50)
        )
    else:
        # Usando busca mais avançada para usuários
        # privilegiados com recursos do PostgreSQL
        stmt = (
            select(Anotacao)
            .options(
                joinedload(Anotacao.endereco), joinedload(Anotacao.usuario)
            )
            .where(Anotacao.texto.ilike(f'%{query}%'))
            .order_by(Anotacao.data_atualizacao.desc())
            .limit(50)
        )

    anotacoes = await session.scalars(stmt)
    return list(anotacoes)


# As rotas com parâmetros genéricos devem vir após as rotas específicas
@router.get('/{anotacao_id}', response_model=AnotacaoRead)
@log_operation('obter_anotacao')
@handle_not_found('anotação')
@require_permission(
    [NivelAcesso.intermediario, NivelAcesso.super_usuario],
    owner_field='id_usuario',
)
async def obter_anotacao(
    anotacao_id: IdPathDep,
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
):
    """
    Recupera detalhes de uma anotação específica

    * Requer autenticação
    * Usuários básicos só podem ver suas próprias anotações
    * Usuários intermediários e super_usuários podem ver todas as anotações
    """
    # Usando a função utilitária para buscar o recurso com relações

    options = [selectinload(Anotacao.endereco), selectinload(Anotacao.usuario)]

    anotacao = await get_resource_or_none(
        session, Anotacao, {'id': anotacao_id}, options
    )

    # O decorator handle_not_found já lida com o caso de anotação não
    # encontrada
    # A verificação de permissão agora é feita pelo
    #  decorator require_permission

    return anotacao


@router.put('/{anotacao_id}', response_model=AnotacaoRead)
@log_operation('atualizar_anotacao')
@handle_not_found('anotação')
@require_permission(
    [NivelAcesso.intermediario, NivelAcesso.super_usuario],
    owner_field='id_usuario',
)
async def atualizar_anotacao(
    anotacao_id: int,
    anotacao_update: AnotacaoUpdate,
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
):
    """
    Atualiza uma anotação existente

    * Requer autenticação
    * Usuários básicos só podem atualizar suas próprias anotações
    * Usuários intermediários e super_usuários
      podem atualizar qualquer anotação
    """
    async with session.begin():
        # Usando a função utilitária para buscar o recurso

        anotacao = await get_resource_or_none(
            session,
            Anotacao,
            {'id': anotacao_id},
            with_for_update=True,  # Lock otimista para concorrência
        )

        # O decorator handle_not_found já lida com o caso de
        #  anotação não encontrada

        # A verificação de permissão agora é
        #  feita pelo decorator require_permission

        # Atualiza os campos da anotação
        anotacao.texto = anotacao_update.texto
        anotacao.data_atualizacao = datetime.now(timezone.utc)

    # Carrega a anotação com as relações para retorno
    await session.refresh(anotacao, ['endereco', 'usuario'])
    return anotacao


@router.delete('/{anotacao_id}', status_code=status.HTTP_204_NO_CONTENT)
@log_operation('deletar_anotacao')
@handle_not_found('anotação')
@require_permission(
    [NivelAcesso.intermediario, NivelAcesso.super_usuario],
    owner_field='id_usuario',
)
async def deletar_anotacao(
    anotacao_id: int,
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
):
    """
    Remove uma anotação

    * Requer autenticação
    * Usuários básicos só podem remover suas próprias anotações
    * Usuários intermediários e super_usuários podem remover qualquer anotação
    """
    async with session.begin():
        # Usando a função utilitária para buscar o recurso

        anotacao = await get_resource_or_none(
            session,
            Anotacao,
            {'id': anotacao_id},
            with_for_update=True,  # Lock para evitar condições de corrida
        )

        # O decorator handle_not_found já lida com o
        #  caso de anotação não encontrada
        # A verificação de permissão agora é
        #  feita pelo decorator require_permission

        await session.delete(anotacao)

    # O commit está implícito pelo contexto do begin()
