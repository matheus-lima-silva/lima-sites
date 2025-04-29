import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..models import NivelAcesso, Usuario
from ..schemas import UsuarioCreate, UsuarioRead
from ..security import get_current_user, require_intermediario

# Configuração de logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix='/usuarios', tags=['Usuários'])

# Definições de dependências usando Annotated
AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]
CurrentUserDep = Annotated[Usuario, Depends(get_current_user)]
IntermediarioUserDep = Annotated[Usuario, Depends(require_intermediario)]
UsuarioPathDep = Annotated[int, Path(..., ge=1)]
NomeQueryDep = Annotated[str, Query(..., min_length=2, max_length=100)]


# Função utilitária para validação
async def get_usuario_or_404(
    session: AsyncSession, usuario_id: int
) -> Usuario:
    """Busca um usuário pelo ID ou lança 404 se não existir"""
    usuario = await session.scalar(
        select(Usuario).where(Usuario.id == usuario_id)
    )
    if not usuario:
        logger.info(f'Usuário não encontrado: {usuario_id}')
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Usuário não encontrado',
        )
    return usuario


def verificar_permissao_modificar_usuario(
    current_user: Usuario, usuario_id: int
) -> None:
    """Verifica se o usuário tem permissão para modificar outro usuário"""
    if (
        current_user.nivel_acesso == NivelAcesso.basico
        and usuario_id != current_user.id
    ):
        logger.warning(
            f'Tentativa de acesso não autorizado: Usuário {current_user.id} '
            f'tentou acessar o usuário {usuario_id}'
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Acesso insuficiente para modificar outros usuários',
        )


@router.post(
    '/', response_model=UsuarioRead, status_code=status.HTTP_201_CREATED
)
async def criar_usuario(
    usuario: UsuarioCreate,
    session: AsyncSessionDep,
    current_user: IntermediarioUserDep,
):
    """Cria um novo usuário no sistema"""
    # Verifica se o telefone já está em uso
    existing_user = await session.scalar(
        select(Usuario).where(Usuario.telefone == usuario.telefone)
    )

    if existing_user:
        logger.warning(
            f'Telefone já existente: {usuario.telefone} por {current_user.id}'
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Usuário com este telefone já existe',
        )

    # Cria um novo usuário com nível básico
    novo_usuario = Usuario(
        telefone=usuario.telefone,
        nome=usuario.nome,
        nivel_acesso=NivelAcesso.basico,
    )

    session.add(novo_usuario)
    await session.commit()
    await session.refresh(novo_usuario)

    logger.info(f'Novo usuário: {novo_usuario.id} por {current_user.id}')

    return novo_usuario


@router.get('/me', response_model=UsuarioRead)
async def ler_usuario_atual(current_user: CurrentUserDep):
    """Retorna informações do usuário autenticado"""
    return current_user


@router.get('/{usuario_id}', response_model=UsuarioRead)
async def obter_usuario(
    session: AsyncSessionDep,
    usuario_id: UsuarioPathDep,
    current_user: CurrentUserDep,
):
    """Retorna informações sobre um usuário específico"""
    # Verificar permissões
    verificar_permissao_modificar_usuario(current_user, usuario_id)
    # Buscar usuário
    usuario = await get_usuario_or_404(session, usuario_id)

    return usuario


@router.put('/{usuario_id}/nome', response_model=UsuarioRead)
async def atualizar_nome_usuario(
    usuario_id: UsuarioPathDep,
    nome: NomeQueryDep,
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
):
    """Atualiza o nome de um usuário"""
    verificar_permissao_modificar_usuario(current_user, usuario_id)

    usuario = await get_usuario_or_404(session, usuario_id)

    # Registra a alteração para fins de auditoria
    logger.info(
        f"Nome alterado: {usuario.id} de '{usuario.nome or 'None'}' "
        f"para '{nome}' por {current_user.id}"
    )

    # Atualiza o nome
    usuario.nome = nome
    await session.commit()
    await session.refresh(usuario)

    return usuario
