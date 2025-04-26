from typing import Annotated, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from ..database import get_async_session
from ..models import Anotacao, Endereco, NivelAcesso, Usuario
from ..schemas import AnotacaoCreate, AnotacaoRead, AnotacaoUpdate
from ..security import get_current_user

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
    async with session.begin():  # Usando transação explícita
        # Verifica se o endereço existe usando método get otimizado
        endereco = await session.get(Endereco, anotacao.id_endereco)
        
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
    
    # Carrega a anotação com as relações para retorno
    await session.refresh(db_anotacao, ["endereco", "usuario"])
    return db_anotacao


# Rotas específicas devem vir antes das genéricas com parâmetros
@router.get("/usuario/minhas", response_model=List[AnotacaoRead])
async def listar_minhas_anotacoes(
    session: AsyncSessionDep,
    order_by: str = Query("data_criacao", description="Campo para ordenação (data_criacao, data_atualizacao)"),
    desc: bool = Query(True, description="Ordenação decrescente"),
    skip: int = 0,
    limit: int = 100,
    current_user: Usuario = Depends(get_current_user),
):
    """
    Lista todas as anotações feitas pelo usuário atual
    
    * Requer autenticação
    * Suporta paginação e ordenação
    """
    # Construir ordenação conforme parâmetros
    if order_by == "data_atualizacao":
        order_field = Anotacao.data_atualizacao
    else:
        order_field = Anotacao.data_criacao
    
    # Aplicar direção da ordenação
    if desc:
        order_clause = order_field.desc()
    else:
        order_clause = order_field.asc()
    
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


@router.get("/endereco/{endereco_id}", response_model=List[AnotacaoRead])
async def listar_anotacoes_do_endereco(
    endereco_id: int,
    session: AsyncSessionDep,
    order_by: str = Query("data_criacao", description="Campo para ordenação"),
    desc: bool = Query(True, description="Ordenação decrescente"),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Lista todas as anotações de um endereço específico
    
    * Requer autenticação
    * Usuários básicos só veem suas próprias anotações
    * Usuários intermediários e super_usuários veem todas as anotações
    """
    # Verifica se o endereço existe usando método get otimizado
    endereco = await session.get(Endereco, endereco_id)
    
    if not endereco:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endereço não encontrado",
        )
    
    # Construir ordenação
    if order_by == "data_atualizacao":
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
                    Anotacao.id_usuario == current_user.id
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


@router.get("/busca", response_model=List[AnotacaoRead])
async def buscar_anotacoes(
    query: str,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(get_current_user),
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
                    Anotacao.texto.ilike(f"%{query}%")
                )
            )
            .order_by(Anotacao.data_atualizacao.desc())
            .limit(50)
        )
    else:
        # Usando busca mais avançada para usuários privilegiados com recursos do PostgreSQL
        stmt = (
            select(Anotacao)
            .options(joinedload(Anotacao.endereco), joinedload(Anotacao.usuario))
            .where(Anotacao.texto.ilike(f"%{query}%"))
            .order_by(Anotacao.data_atualizacao.desc())
            .limit(50)
        )
    
    anotacoes = await session.scalars(stmt)
    return list(anotacoes)


# As rotas com parâmetros genéricos devem vir após as rotas específicas
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
    """
    # Carregando a anotação com suas relações em uma única consulta eficiente
    stmt = (
        select(Anotacao)
        .options(joinedload(Anotacao.endereco), joinedload(Anotacao.usuario))
        .where(Anotacao.id == anotacao_id)
    )
    anotacao = await session.scalar(stmt)
    
    if not anotacao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anotação não encontrada",
        )

    # Usuários básicos só podem acessar suas próprias anotações
    if current_user.nivel_acesso == NivelAcesso.basico and anotacao.id_usuario != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Não autorizado a acessar esta anotação",
        )

    return anotacao


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
    async with session.begin():
        # Obtenção da anotação com lock para atualização
        stmt = (
            select(Anotacao)
            .where(Anotacao.id == anotacao_id)
            .with_for_update()  # Lock otimista para concorrência
        )
        anotacao = await session.scalar(stmt)
        
        if not anotacao:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Anotação não encontrada",
            )

        # Verifica permissões: usuários básicos só podem atualizar suas próprias anotações
        if current_user.nivel_acesso == NivelAcesso.basico and anotacao.id_usuario != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Não autorizado a atualizar esta anotação",
            )

        # Atualiza os campos da anotação
        anotacao.texto = anotacao_update.texto
        anotacao.data_atualizacao = datetime.now(timezone.utc)
    
    # Carrega a anotação com as relações para retorno
    await session.refresh(anotacao, ["endereco", "usuario"])
    return anotacao


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
    async with session.begin():
        # Obtenção da anotação com lock para exclusão
        stmt = (
            select(Anotacao)
            .where(Anotacao.id == anotacao_id)
            .with_for_update()  # Lock para evitar condições de corrida
        )
        anotacao = await session.scalar(stmt)
        
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
    
    # O commit está implícito pelo contexto do begin()
