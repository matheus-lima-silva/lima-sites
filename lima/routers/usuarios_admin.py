import logging
from typing import List

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from ..models import NivelAcesso, Usuario
from ..schemas import UsuarioRead
from ..utils.dependencies import (
    AsyncSessionDep,
    IdPathDep,
    IntermediarioUserDep,
    LimitQueryDep,
    SkipQueryDep,
    SuperUserDep,
)

# Configuração de logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix='/admin/usuarios', tags=['Administração de Usuários']
)

# Mantendo apenas o que não tem no módulo compartilhado
TelefonePathDep = IdPathDep  # Aproveitando a validação existente


# Função utilitária para validação
async def get_usuario_or_404(
    session: AsyncSessionDep, usuario_id: int
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


@router.get('/', response_model=List[UsuarioRead])
async def listar_usuarios(
    session: AsyncSessionDep,
    skip: SkipQueryDep,
    limit: LimitQueryDep,
    current_user: IntermediarioUserDep,
):
    """Lista todos os usuários com paginação (requer nível intermediário)"""
    usuarios = await session.scalars(
        select(Usuario).order_by(Usuario.id).offset(skip).limit(limit)
    )

    resultado = list(usuarios)
    logger.info(
        f'Listagem: {len(resultado)} usuários (skip={skip}, limit={limit}) '
        f'por {current_user.id}'
    )
    return resultado


@router.put('/{usuario_id}/nivel-acesso', response_model=UsuarioRead)
async def atualizar_nivel_acesso(
    nivel_acesso: NivelAcesso,
    session: AsyncSessionDep,
    usuario_id: IdPathDep,
    current_user: SuperUserDep,
):
    """Atualiza nível de acesso (requer super usuário)"""
    usuario = await get_usuario_or_404(session, usuario_id)

    # Proteção contra rebaixamento acidental
    if (
        usuario_id == current_user.id
        and nivel_acesso != NivelAcesso.super_usuario
    ):
        logger.warning(f'Tentativa de rebaixamento próprio: {current_user.id}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Não é possível rebaixar o próprio nível de acesso',
        )

    logger.info(
        f'Mudança de nível: usuário {usuario.id} de {usuario.nivel_acesso} '
        f'para {nivel_acesso} por {current_user.id}'
    )

    usuario.nivel_acesso = nivel_acesso
    await session.commit()
    await session.refresh(usuario)
    return usuario


@router.delete('/{usuario_id}', status_code=status.HTTP_204_NO_CONTENT)
async def remover_usuario(
    session: AsyncSessionDep,
    usuario_id: IdPathDep,
    current_user: SuperUserDep,
):
    """Remove um usuário (requer super usuário)"""
    if usuario_id == current_user.id:
        logger.warning(
            f'Tentativa de remover próprio usuário: {current_user.id}'
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Não é possível remover o próprio usuário',
        )

    usuario = await get_usuario_or_404(session, usuario_id)
    logger.warning(
        f'Removendo usuário: {usuario.id} por super usuário {current_user.id}'
    )

    await session.delete(usuario)
    await session.commit()


@router.get('/por-telefone/{telefone}', response_model=UsuarioRead)
async def buscar_por_telefone(
    session: AsyncSessionDep,
    telefone: str,  # Usando validação de telefone do Path padrão
    current_user: IntermediarioUserDep,
):
    """Busca por telefone (requer nível intermediário)"""
    usuario = await session.scalar(
        select(Usuario).where(Usuario.telefone == telefone)
    )

    if not usuario:
        logger.info(
            f'Telefone não encontrado: {telefone} por {current_user.id}'
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Usuário não encontrado com este telefone',
        )

    return usuario
