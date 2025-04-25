from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_async_session
from ..models import Endereco, Usuario
from ..schemas import EnderecoCreate, EnderecoRead
from ..security import get_current_user, require_intermediario, require_super_usuario

router = APIRouter(prefix="/enderecos", tags=["Endereços"])

AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


@router.post("/", response_model=EnderecoRead, status_code=status.HTTP_201_CREATED)
async def criar_endereco(
    endereco: EnderecoCreate,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(require_intermediario),  # Requer nível intermediário ou superior
):
    """
    Cria um novo endereço
    
    * Requer nível de acesso intermediário ou superior
    """
    # Cria o novo endereço
    db_endereco = Endereco(
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
    current_user: Usuario = Depends(get_current_user),  # Qualquer usuário autenticado
):
    """
    Recupera detalhes de um endereço específico
    
    * Requer autenticação
    * Todos os usuários podem consultar endereços
    """
    stmt = (
        select(Endereco)
        .where(Endereco.id == endereco_id)
    )
    
    result = await session.execute(stmt)
    endereco = result.scalar_one_or_none()
    
    if not endereco:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endereço não encontrado",
        )
    
    return endereco


@router.get("/", response_model=List[EnderecoRead])
async def listar_enderecos(
    session: AsyncSessionDep,
    skip: int = 0, 
    limit: int = 100,
    current_user: Usuario = Depends(get_current_user),  # Qualquer usuário autenticado
):
    """
    Lista endereços com paginação
    
    * Requer autenticação
    * Todos os usuários podem consultar a lista de endereços
    """
    query = select(Endereco).offset(skip).limit(limit)
    
    result = await session.execute(query)
    enderecos = result.scalars().all()
    
    return enderecos


@router.put("/{endereco_id}", response_model=EnderecoRead)
async def atualizar_endereco(
    endereco_id: int,
    endereco_update: EnderecoCreate,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(require_intermediario),  # Requer nível intermediário ou superior
):
    """
    Atualiza um endereço existente
    
    * Requer nível de acesso intermediário ou superior
    """
    stmt = select(Endereco).where(Endereco.id == endereco_id)
    result = await session.execute(stmt)
    db_endereco = result.scalar_one_or_none()
    
    if not db_endereco:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endereço não encontrado",
        )
    
    # Atualiza os campos do endereço
    for field, value in endereco_update.dict(exclude_unset=True).items():
        setattr(db_endereco, field, value)
    
    await session.commit()
    await session.refresh(db_endereco)
    
    return db_endereco


@router.delete("/{endereco_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_endereco(
    endereco_id: int,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(require_super_usuario),  # Somente super usuários
):
    """
    Remove um endereço do sistema
    
    * Requer nível de acesso super_usuario
    """
    stmt = select(Endereco).where(Endereco.id == endereco_id)
    result = await session.execute(stmt)
    endereco = result.scalar_one_or_none()
    
    if not endereco:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endereço não encontrado",
        )
    
    # Verifica se há dependências (buscas, alterações, sugestões vinculadas)
    # Em um sistema real, você deveria verificar estas relações ou usar cascade
    # para evitar violações de integridade referencial
    
    await session.delete(endereco)
    await session.commit()
    
    return None
