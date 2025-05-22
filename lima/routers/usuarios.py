import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from ..models import NivelAcesso, Usuario
from ..schemas import (
    UsuarioCreate,
    UsuarioPublic,
)  # Alterado de UsuarioRead para UsuarioPublic
from ..utils.dependencies import (
    AsyncSessionDep,
    CurrentUserDep,
    IdPathDep,
    IntermediarioUserDep,
    NomeQueryDep,
)
from ..utils.permissions import verificar_permissao_basica

# Configuração de logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix='/usuarios', tags=['Usuários'])


# Função utilitária para validação
async def get_usuario_or_404(session, usuario_id: int) -> Usuario:
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


@router.post(
    '/',
    response_model=UsuarioPublic,
    status_code=status.HTTP_201_CREATED,  # Alterado de UsuarioRead para UsuarioPublic
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

    return UsuarioPublic.model_validate(
        novo_usuario
    )  # Alterado de UsuarioRead para UsuarioPublic


@router.get(
    '/me', response_model=UsuarioPublic
)  # Alterado de UsuarioRead para UsuarioPublic
async def ler_usuario_atual(
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
):
    """Retorna informações do usuário autenticado"""
    try:
        if not hasattr(current_user, 'id') or current_user.id is None:
            logger.warning(
                f'Objeto current_user sem ID. Tipo: {type(current_user)}'
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Usuário não autenticado corretamente',
            )
        # Retorna o schema Pydantic diretamente
        return UsuarioPublic.model_validate(
            current_user
        )  # Alterado de UsuarioRead para UsuarioPublic
    except Exception as e:
        logger.warning(f'Erro ao acessar current_user: {str(e)}')
        try:
            if hasattr(current_user, 'telefone') and current_user.telefone:
                telefone = current_user.telefone
                logger.info(
                    f'Tentando recuperar usuário pelo telefone: {telefone}'
                )
                stmt = select(Usuario).where(Usuario.telefone == telefone)
                result = await session.execute(stmt)
                usuario = result.scalar_one_or_none()
                if usuario:
                    return UsuarioPublic.model_validate(
                        usuario
                    )  # Alterado de UsuarioRead para UsuarioPublic
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=(
                    'Não foi possível identificar o usuário. '
                    'Por favor, refaça o login.'
                ),
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Erro ao tentar recuperação alternativa: {str(e)}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    'Erro ao processar a requisição. '
                    'Por favor, tente novamente.'
                ),
            )


@router.get(
    '/{usuario_id}',
    response_model=UsuarioPublic,  # Alterado de UsuarioRead para UsuarioPublic
)
async def obter_usuario(
    session: AsyncSessionDep,
    usuario_id: IdPathDep,
    current_user: CurrentUserDep,
):
    """Retorna informações sobre um usuário específico"""
    # Acesso simplificado aos atributos do usuário atual (objeto desvinculado)
    try:
        # Verificação de permissão usando a função centralizada
        verificar_permissao_basica(current_user, usuario_id, 'usuário')

        # Buscar usuário
        stmt = select(Usuario).where(Usuario.id == usuario_id)
        result = await session.execute(stmt)
        usuario = result.scalar_one_or_none()

        if not usuario:
            logger.info(f'Usuário não encontrado: {usuario_id}')
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Usuário não encontrado',
            )

        return UsuarioPublic.model_validate(
            usuario
        )  # Alterado de UsuarioRead para UsuarioPublic

    except AttributeError as e:
        # Caso haja problema ao acessar os atributos
        logger.warning(f'Erro ao acessar atributos de current_user: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Usuário não autenticado corretamente',
        )


@router.put(
    '/{usuario_id}/nome', response_model=UsuarioPublic
)  # Alterado de UsuarioRead para UsuarioPublic
async def atualizar_nome_usuario(
    usuario_id: IdPathDep,
    nome: NomeQueryDep,
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
):
    """Atualiza o nome de um usuário"""
    # Acesso simplificado aos atributos do usuário atual (objeto desvinculado)
    try:
        # Verificação de permissão usando a função centralizada
        verificar_permissao_basica(current_user, usuario_id, 'usuário')

        # Buscar usuário que terá o nome atualizado
        stmt = select(Usuario).where(Usuario.id == usuario_id)
        result = await session.execute(stmt)
        usuario = result.scalar_one_or_none()

        if not usuario:
            logger.info(f'Usuário não encontrado: {usuario_id}')
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Usuário não encontrado',
            )

        # Registra a alteração para fins de auditoria
        logger.info(
            f"Nome alterado: {usuario.id} de '{usuario.nome or 'None'}' "
            f"para '{nome}' por {current_user.id}"
        )

        # Atualiza o nome
        usuario.nome = nome
        await session.commit()
        await session.refresh(usuario)

        return UsuarioPublic.model_validate(
            usuario
        )  # Alterado de UsuarioRead para UsuarioPublic

    except AttributeError as e:
        # Caso haja problema ao acessar os atributos
        logger.warning(f'Erro ao acessar atributos de current_user: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Usuário não autenticado corretamente',
        )


@router.get(
    '/', response_model=UsuarioPublic
)  # Alterado de UsuarioRead para UsuarioPublic
async def obter_usuario_por_telefone(
    telefone: str,
    session: AsyncSessionDep,
    # current_user: CurrentUserDep, # Removido para permitir acesso interno do bot
):
    """Retorna informações do usuário pelo telefone.
    Usado pelo bot Telegram.
    """
    usuario = await session.scalar(
        select(Usuario).where(Usuario.telefone == telefone)
    )
    if not usuario:
        logger.info(f'Usuário não encontrado para telefone: {telefone}')
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Usuário não encontrado',
        )
    return UsuarioPublic.model_validate(
        usuario
    )  # Alterado de UsuarioRead para UsuarioPublic
