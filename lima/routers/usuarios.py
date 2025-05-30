import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from ..core.loading_options import (
    USER_LOAD_OPTIONS,
    USER_LOAD_OPTIONS_MINIMAL,
)
from ..models import Usuario
from ..schemas import (
    NivelAcesso,
    UsuarioCreate,
    UsuarioPublic,
    UsuarioPublicMinimo,
)
from ..utils.dependencies import (
    AsyncSessionDep,
    CurrentUserDep,
    IdPathDep,
    IntermediarioUserDep,
    ListarUsuariosParamsDep,
)
from ..utils.permissions import verificar_permissao_basica

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/usuarios', tags=['Usuários'])


async def get_usuario_or_404(
    session: AsyncSessionDep, usuario_id: int
) -> Usuario:
    """Busca um usuário pelo ID ou lança 404 se não existir."""
    usuario = await session.scalar(
        select(Usuario)
        .options(
            *USER_LOAD_OPTIONS
            # Aplicando as opções de carregamento centralizadas
        )
        .where(Usuario.id == usuario_id)
    )
    if not usuario:
        logger.info(f'Usuário não encontrado: {usuario_id}')
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Usuário não encontrado',
        )
    return usuario


@router.post(
    '/', response_model=UsuarioPublic, status_code=status.HTTP_201_CREATED
)
async def criar_usuario(
    usuario: UsuarioCreate,
    session: AsyncSessionDep,
    current_user: IntermediarioUserDep,
):
    """Cria um novo usuário no sistema."""
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
    novo_usuario = Usuario(
        telefone=usuario.telefone,
        nome=usuario.nome,
        nivel_acesso=NivelAcesso.basico,
    )
    session.add(novo_usuario)
    await session.commit()
    await session.refresh(novo_usuario, attribute_names=['id'])

    db_usuario = await session.scalar(
        select(Usuario)
        .options(
            *USER_LOAD_OPTIONS
            # Aplicando as opções de carregamento centralizadas
        )
        .where(Usuario.id == novo_usuario.id)
    )

    if not db_usuario:
        logger.error(
            f"""Usuário recém-criado com ID {novo_usuario.id} não encontrado
            após commit."""
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Erro ao recuperar usuário após criação.',
        )

    logger.info(f'Novo usuário: {db_usuario.id} por {current_user.id}')
    return UsuarioPublic.model_validate(db_usuario)


@router.get(
    '/me', response_model=UsuarioPublicMinimo
)  # Alterado para UsuarioPublicMinimo
async def ler_usuario_atual(
    session: AsyncSessionDep, current_user: CurrentUserDep
):
    """Retorna informações do usuário autenticado."""
    # A validação/serialização para UsuarioPublicMinimo ocorrerá
    # automaticamente.
    # A otimização do carregamento de current_user será feita em security.py.
    return current_user


@router.get(
    '/', response_model=list[UsuarioPublicMinimo]
)  # Alterado para list[UsuarioPublicMinimo]
async def listar_usuarios(
    session: AsyncSessionDep,
    current_user: IntermediarioUserDep,
    params: ListarUsuariosParamsDep,  # Usar a dependência agrupada
):
    """Lista todos os usuários do sistema."""
    query = select(Usuario).order_by(Usuario.id)
    if params.nome:  # Acessar via params
        query = query.where(Usuario.nome.ilike(f'%{params.nome}%'))
    if params.telefone:  # Acessar via params
        query = query.where(Usuario.telefone == params.telefone)

    # Aplicar offset e limit depois de todas as condições where
    query = query.offset(params.skip).limit(params.limit)  # Acessar via params

    # Aplicar USER_LOAD_OPTIONS_MINIMAL
    # Alterado para USER_LOAD_OPTIONS_MINIMAL
    query = query.options(*USER_LOAD_OPTIONS_MINIMAL)

    result = await session.execute(query)
    usuarios = result.scalars().all()
    logger.info(f'Listando usuários: {len(usuarios)} por {current_user.id}')
    # Alterado para UsuarioPublicMinimo
    return [UsuarioPublicMinimo.model_validate(u) for u in usuarios]


@router.get('/{usuario_id}', response_model=UsuarioPublic)
async def obter_usuario(
    session: AsyncSessionDep,
    usuario_id: IdPathDep,
    current_user: CurrentUserDep,
    # Alterado para CurrentUserDep para consistência
):
    """Obtém um usuário específico pelo ID."""
    # Verificar permissão: usuário pode ver a si mesmo
    #  ou ser intermediário/super
    verificar_permissao_basica(current_user, usuario_id)

    db_usuario = await get_usuario_or_404(session, usuario_id)
    logger.info(f'Obtendo usuário: {usuario_id} por {current_user.id}')
    return UsuarioPublic.model_validate(db_usuario)


@router.put('/{usuario_id}', response_model=UsuarioPublic)
async def atualizar_usuario(
    usuario_id: IdPathDep,
    usuario_update_data: UsuarioCreate,
    # Usando UsuarioCreate para simplicidade
    session: AsyncSessionDep,
    current_user: IntermediarioUserDep,
    # Apenas intermediários ou superiores podem atualizar
):
    """Atualiza um usuário existente."""
    db_usuario = await get_usuario_or_404(session, usuario_id)

    # Verificar se o telefone está sendo alterado para um já existente
    if (
        usuario_update_data.telefone
        and usuario_update_data.telefone != db_usuario.telefone
    ):
        existing_user = await session.scalar(
            select(Usuario).where(
                Usuario.telefone == usuario_update_data.telefone
            )
        )
        if existing_user and existing_user.id != usuario_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Telefone já cadastrado para outro usuário.',
            )
        db_usuario.telefone = usuario_update_data.telefone

    if usuario_update_data.nome is not None:
        db_usuario.nome = usuario_update_data.nome
    # Nivel de acesso não é atualizado por este endpoint para manter segurança
    # db_usuario.nivel_acesso = usuario_update_data.nivel_acesso

    await session.commit()
    await session.refresh(db_usuario)

    # Re-buscar com load options para garantir que a resposta está completa
    # Isso é importante se UsuarioPublic evoluir para incluir mais relações
    # que não são atualizadas diretamente aqui mas são parte do modelo.
    updated_db_usuario = await get_usuario_or_404(session, db_usuario.id)

    logger.info(f'Usuário atualizado: {usuario_id} por {current_user.id}')
    return UsuarioPublic.model_validate(updated_db_usuario)
