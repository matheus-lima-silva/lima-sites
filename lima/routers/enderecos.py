from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_async_session
from ..models import Endereco, Usuario, TipoEndereco
from ..schemas import EnderecoCreate, EnderecoRead
from ..security import get_current_user, require_intermediario, require_super_usuario

router = APIRouter(prefix="/enderecos", tags=["Endereços"])

AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


@router.post("/", response_model=EnderecoRead, status_code=status.HTTP_201_CREATED)
async def criar_endereco(
    endereco: EnderecoCreate,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(require_intermediario),
):
    """
    Cria um novo endereço
    
    * Requer nível de acesso intermediário ou superior
    """
    # Verifica se o código do endereço já existe
    existing = await session.scalar(
        select(Endereco).where(Endereco.codigo_endereco == endereco.codigo_endereco)
    )
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Endereço com código '{endereco.codigo_endereco}' já existe",
        )
    
    # Cria o novo endereço
    db_endereco = Endereco(
        codigo_endereco=endereco.codigo_endereco,
        uf=endereco.uf,
        municipio=endereco.municipio,
        bairro=endereco.bairro,
        logradouro=endereco.logradouro,
        tipo=endereco.tipo,
        iddetentora=endereco.iddetentora,
        numero=endereco.numero,
        complemento=endereco.complemento,
        cep=endereco.cep,
        latitude=endereco.latitude,
        longitude=endereco.longitude,
    )
    
    session.add(db_endereco)
    await session.commit()
    await session.refresh(db_endereco)
    
    return db_endereco


@router.get("/{endereco_id}", response_model=EnderecoRead)
async def obter_endereco(
    endereco_id: int,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(get_current_user),
    load_relations: bool = Query(False, description="Carregar dados relacionados"),
):
    """
    Recupera detalhes de um endereço específico
    
    * Requer autenticação
    * Todos os usuários podem consultar endereços
    * Permite carregar dados relacionados (anotações, alterações)
    """
    if load_relations:
        stmt = (
            select(Endereco)
            .where(Endereco.id == endereco_id)
            .options(
                selectinload(Endereco.anotacoes),
                selectinload(Endereco.alteracoes)
            )
        )
    else:
        stmt = select(Endereco).where(Endereco.id == endereco_id)
    
    endereco = await session.scalar(stmt)
    
    if not endereco:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endereço não encontrado",
        )
    
    return endereco


@router.get("/codigo/{codigo_endereco}", response_model=EnderecoRead)
async def obter_endereco_por_codigo(
    codigo_endereco: str,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(get_current_user),
):
    """
    Recupera um endereço pelo seu código alfanumérico
    
    * Requer autenticação
    * Todos os usuários podem consultar endereços
    """
    endereco = await session.scalar(
        select(Endereco).where(Endereco.codigo_endereco == codigo_endereco)
    )
    
    if not endereco:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endereço com código '{codigo_endereco}' não encontrado",
        )
    
    return endereco


@router.get("/", response_model=List[EnderecoRead])
async def listar_enderecos(
    session: AsyncSessionDep,
    uf: Optional[str] = None,
    municipio: Optional[str] = None,
    bairro: Optional[str] = None,
    tipo: Optional[TipoEndereco] = None,
    query: Optional[str] = None,
    skip: int = 0, 
    limit: int = 100,
    current_user: Usuario = Depends(get_current_user),
):
    """
    Lista endereços com paginação e filtros
    
    * Requer autenticação
    * Todos os usuários podem consultar a lista de endereços
    * Suporta filtros por UF, município, bairro e tipo
    * Suporta busca textual em múltiplos campos
    """
    # Construir filtros dinamicamente
    filters = []
    
    if uf:
        filters.append(Endereco.uf == uf)
    
    if municipio:
        filters.append(Endereco.municipio.ilike(f'%{municipio}%'))
    
    if bairro:
        filters.append(Endereco.bairro.ilike(f'%{bairro}%'))
    
    if tipo:
        filters.append(Endereco.tipo == tipo)
    
    # Busca textual (usando recursos de full text search do PostgreSQL)
    if query:
        text_search = or_(
            Endereco.logradouro.ilike(f'%{query}%'),
            Endereco.bairro.ilike(f'%{query}%'),
            Endereco.municipio.ilike(f'%{query}%'),
            Endereco.codigo_endereco.ilike(f'%{query}%')
        )
        filters.append(text_search)
    
    # Aplicar filtros à consulta
    stmt = select(Endereco)
    if filters:
        stmt = stmt.where(and_(*filters))
    
    # Adicionar paginação
    stmt = stmt.offset(skip).limit(limit)
    
    # Ordenar por município e logradouro
    stmt = stmt.order_by(Endereco.uf, Endereco.municipio, Endereco.logradouro)
    
    result = await session.scalars(stmt)
    return list(result)


@router.get("/estatisticas/contagem", response_model=dict)
async def estatisticas_enderecos(
    session: AsyncSessionDep,
    current_user: Usuario = Depends(get_current_user),
):
    """
    Retorna estatísticas sobre os endereços cadastrados
    
    * Requer autenticação
    * Aproveita as capacidades do PostgreSQL para estatísticas e agregações
    """
    # Total de endereços
    total = await session.scalar(select(func.count()).select_from(Endereco))
    
    # Contagem por UF
    stmt_uf = select(
        Endereco.uf, 
        func.count().label('total')
    ).group_by(Endereco.uf)
    result_uf = await session.execute(stmt_uf)
    por_uf = {row.uf: row.total for row in result_uf}
    
    # Contagem por tipo
    stmt_tipo = select(
        Endereco.tipo, 
        func.count().label('total')
    ).group_by(Endereco.tipo)
    result_tipo = await session.execute(stmt_tipo)
    por_tipo = {row.tipo.value: row.total for row in result_tipo}
    
    return {
        "total": total,
        "por_uf": por_uf,
        "por_tipo": por_tipo,
    }


@router.put("/{endereco_id}", response_model=EnderecoRead)
async def atualizar_endereco(
    endereco_id: int,
    endereco_update: EnderecoCreate,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(require_intermediario),
):
    """
    Atualiza um endereço existente
    
    * Requer nível de acesso intermediário ou superior
    """
    async with session.begin_nested():  # Usando savepoint para operações complexas
        # Verifica se o endereço existe
        db_endereco = await session.scalar(
            select(Endereco).where(Endereco.id == endereco_id)
        )
        
        if not db_endereco:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Endereço não encontrado",
            )
        
        # Verifica se o novo código de endereço já está em uso por outro endereço
        if endereco_update.codigo_endereco != db_endereco.codigo_endereco:
            existing = await session.scalar(
                select(Endereco).where(
                    and_(
                        Endereco.codigo_endereco == endereco_update.codigo_endereco,
                        Endereco.id != endereco_id
                    )
                )
            )
            
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Código de endereço '{endereco_update.codigo_endereco}' já está em uso",
                )
        
        # Atualiza os campos do endereço
        for field, value in endereco_update.dict().items():
            setattr(db_endereco, field, value)
    
    # Commit fora do bloco begin_nested para aplicar as alterações
    await session.commit()
    await session.refresh(db_endereco)
    
    return db_endereco


@router.delete("/{endereco_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_endereco(
    endereco_id: int,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(require_super_usuario),
):
    """
    Remove um endereço do sistema
    
    * Requer nível de acesso super_usuario
    * Verifica e impede exclusão se houver dependências
    """
    async with session.begin():
        # Verificar dependências antes de excluir
        endereco = await session.get(Endereco, endereco_id)
        
        if not endereco:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Endereço não encontrado",
            )
        
        # Verificar dependências (usando recursos avançados do PostgreSQL)
        has_dependencies = await session.scalar(
            text("""
            SELECT EXISTS(
                SELECT 1 FROM buscas WHERE id_endereco = :id
                UNION ALL
                SELECT 1 FROM alteracoes WHERE id_endereco = :id
                UNION ALL
                SELECT 1 FROM anotacoes WHERE id_endereco = :id
                LIMIT 1
            )
            """),
            {"id": endereco_id}
        )
        
        if has_dependencies:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Não é possível remover este endereço pois ele possui registros dependentes",
            )
        
        await session.delete(endereco)

    # O commit está implícito pelo contexto do begin()
