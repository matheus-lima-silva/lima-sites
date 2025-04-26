from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..models import NivelAcesso, Usuario
from ..schemas import UsuarioCreate, UsuarioRead
from ..security import (
    get_current_user,
    require_intermediario,
    require_super_usuario,
)

router = APIRouter(prefix="/usuarios", tags=["Usuários"])

AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


@router.post("/", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
async def criar_usuario(
    usuario: UsuarioCreate,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(require_intermediario),  # Só intermediário ou super
):
    """
    Cria um novo usuário no sistema
    
    * Requer nível de acesso intermediário ou superior
    * Por padrão, novos usuários criados terão nível básico
    """
    # Verifica se o telefone já está em uso
    existing_user = await session.scalar(
        select(Usuario).where(Usuario.telefone == usuario.telefone)
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Usuário com este telefone já existe",
        )

    # Cria um novo usuário com nível básico
    novo_usuario = Usuario(
        telefone=usuario.telefone,
        nome=usuario.nome,
        nivel_acesso=NivelAcesso.basico,  # Padrão: nível básico
    )

    session.add(novo_usuario)
    await session.commit()
    await session.refresh(novo_usuario)

    return novo_usuario


@router.get("/me", response_model=UsuarioRead)
async def obter_usuario_atual(current_user: Usuario = Depends(get_current_user)):
    """
    Retorna o usuário atualmente autenticado
    """
    return current_user


@router.get("/{usuario_id}", response_model=UsuarioRead)
async def obter_usuario(
    usuario_id: int,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(get_current_user),  # Qualquer usuário autenticado
):
    """
    Retorna informações sobre um usuário específico
    
    * Usuários básicos só podem ver a si mesmos
    * Usuários intermediários e super podem ver qualquer usuário
    """
    # Verificar se o usuário está tentando acessar a si mesmo ou tem permissão para ver outros
    if current_user.nivel_acesso == NivelAcesso.basico and usuario_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso insuficiente para ver outros usuários",
        )

    usuario = await session.scalar(select(Usuario).where(Usuario.id == usuario_id))

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )

    return usuario


@router.get("/", response_model=List[UsuarioRead])
async def listar_usuarios(
    session: AsyncSessionDep,
    skip: int = 0,
    limit: int = 100,
    current_user: Usuario = Depends(require_intermediario),  # Só intermediário ou super
):
    """
    Lista todos os usuários do sistema
    
    * Requer nível de acesso intermediário ou superior
    * Suporta paginação através dos parâmetros skip e limit
    """
    usuarios = await session.scalars(
        select(Usuario).offset(skip).limit(limit)
    )

    return list(usuarios)


@router.put("/{usuario_id}/nivel-acesso", response_model=UsuarioRead)
async def atualizar_nivel_acesso(
    usuario_id: int,
    nivel_acesso: NivelAcesso,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(require_super_usuario),  # Apenas super usuário
):
    """
    Atualiza o nível de acesso de um usuário
    
    * Requer nível de acesso super_usuario
    """
    # Verifica se o usuário existe
    usuario = await session.scalar(select(Usuario).where(Usuario.id == usuario_id))

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )

    # Atualiza o nível de acesso
    usuario.nivel_acesso = nivel_acesso
    await session.commit()
    await session.refresh(usuario)

    return usuario


@router.put("/{usuario_id}/nome", response_model=UsuarioRead)
async def atualizar_nome_usuario(
    usuario_id: int,
    nome: str,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(get_current_user),
):
    """
    Atualiza o nome de um usuário
    
    * Usuários básicos só podem atualizar seu próprio nome
    * Usuários intermediários e super podem atualizar qualquer usuário
    """
    # Verificar permissões
    if current_user.nivel_acesso == NivelAcesso.basico and usuario_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso insuficiente para modificar outros usuários",
        )

    # Verifica se o usuário existe
    usuario = await session.scalar(select(Usuario).where(Usuario.id == usuario_id))

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )

    # Atualiza o nome
    usuario.nome = nome
    await session.commit()
    await session.refresh(usuario)

    return usuario


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_usuario(
    usuario_id: int,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(require_super_usuario),  # Apenas super usuário
):
    """
    Remove um usuário do sistema
    
    * Requer nível de acesso super_usuario
    * Não permite remover o próprio usuário que está fazendo a operação
    """
    # Não permite remover a si mesmo
    if usuario_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível remover o próprio usuário atual",
        )

    # Verifica se o usuário existe
    usuario = await session.scalar(select(Usuario).where(Usuario.id == usuario_id))

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )

    # Remove o usuário
    await session.delete(usuario)
    await session.commit()


@router.get("/telefone/{telefone}", response_model=Optional[UsuarioRead])
async def buscar_usuario_por_telefone(
    telefone: str,
    session: AsyncSessionDep,
    current_user: Usuario = Depends(require_intermediario),  # Só intermediário ou super
):
    """
    Busca um usuário pelo número de telefone
    
    * Requer nível de acesso intermediário ou superior
    """
    usuario = await session.scalar(
        select(Usuario).where(Usuario.telefone == telefone)
    )

    if not usuario:
        return None

    return usuario
