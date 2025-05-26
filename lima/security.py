import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import DecodeError, ExpiredSignatureError, decode, encode
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_async_session, utcnow
from .models import NivelAcesso, Usuario
from .settings import Settings

settings = Settings()
logger = logging.getLogger(__name__)
algorithms = getattr(settings, 'ALGORITHMS', ['HS256'])

# Rate limiting
RATE_LIMIT_WINDOW = getattr(settings, 'RATE_LIMIT_WINDOW', 300)
MAX_LOGIN_ATTEMPTS = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)
login_attempts = defaultdict(lambda: {'count': 0, 'last_attempt': 0})

bearer_scheme = HTTPBearer()


def create_access_token(user_id: int) -> str:
    """Cria um token de acesso JWT para o usuário."""
    now = datetime.now(timezone.utc)
    to_encode = {
        'sub': str(user_id),
        'iat': now,
        'exp': now + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS),
        'type': 'telegram_user',
    }
    encoded_jwt = encode(
        to_encode, settings.SECRET_KEY, algorithm=algorithms[0]
    )
    return encoded_jwt


async def _create_new_user_instance(
    telegram_user_id: int,
    name: Optional[str],
    expected_phone: str,
    current_time: datetime,
    # Mantido para possível uso futuro,
    # mas não passado ao construtor diretamente
    session: AsyncSession,
) -> Usuario:
    """Cria uma nova instância de usuário, mas não faz commit."""
    logger.info(
        f'Usuário com Telegram ID {telegram_user_id} não encontrado. '
        'Criando.'
    )
    user = Usuario(
        telegram_user_id=telegram_user_id,
        telefone=expected_phone,
        nome=name,
        nivel_acesso=NivelAcesso.basico,
        # last_seen não é mais passado aqui, pois init=False no modelo
        # e server_default=func.now() deve cuidar da inicialização.
        # Se current_time for diferente de func.now()
        #  e precisar ser definido especificamente,
        # faremos isso após a instanciação: user.last_seen = current_time
    )
    # Se você precisar que last_seen seja EXATAMENTE current_time na criação:
    user.last_seen = current_time
    session.add(user)
    return user


async def _update_existing_user_fields(
    user: Usuario,
    name: Optional[str],
    expected_phone: str,
    current_time: datetime,
) -> tuple[bool, list[str]]:
    """Atualiza os campos de um usuário existente se necessário."""
    needs_commit = False
    updated_fields = []
    if name and user.nome != name:
        user.nome = name
        updated_fields.append('nome')
        needs_commit = True
    if user.telefone != expected_phone:
        user.telefone = expected_phone
        updated_fields.append('telefone')
        needs_commit = True
    if user.last_seen != current_time:  # Compara com o tempo da chamada atual
        user.last_seen = current_time
        updated_fields.append('last_seen')
        needs_commit = True
    return needs_commit, updated_fields


async def _commit_user_changes_and_log(
    user: Usuario,
    session: AsyncSession,
    is_new_user: bool,
    updated_fields: list[str],
    telegram_user_id: int,  # Adicionado para logging em caso de erro
):
    """Faz commit das alterações do usuário e registra o log."""
    try:
        await session.commit()
        await session.refresh(user)
        log_msg_parts = [f'ID={user.id}']
        if is_new_user:
            log_msg_parts.append(f"Nome='{user.nome}'")
            log_msg_parts.append(f"Telefone='{user.telefone}'")
            last_seen_iso = (
                user.last_seen.isoformat() if user.last_seen else 'N/A'
            )
            log_msg_parts.append(f'LastSeen={last_seen_iso}')
            logger.info(f'Novo usuário criado: {", ".join(log_msg_parts)}.')
        elif updated_fields:
            for field_name in updated_fields:  # Renomeado para field_name
                val = getattr(user, field_name)
                if isinstance(val, datetime):
                    val = val.isoformat()
                log_msg_parts.append(f"{field_name}='{val}'")
            logger.info(f'Usuário atualizado: {", ".join(log_msg_parts)}.')
    except Exception as e:
        await session.rollback()
        op_type = 'criação' if is_new_user else 'atualização'
        fields_log = ', '.join(updated_fields) or 'N/A'
        # Garante que user.id seja acessado apenas se user não for None
        user_pk_id_for_log = (
            user.id if user and hasattr(user, 'id') and user.id is not None
            else telegram_user_id
        )
        log_line_1 = (
            f'Erro no commit para usuário (telegram_id={telegram_user_id}, '
            f'pk_id_tentativo={user_pk_id_for_log}) '
        )
        log_line_2 = f'(op: {op_type}, campos: {fields_log}): {e}.'
        # Adicionado exc_info=True
        logger.warning(log_line_1 + log_line_2, exc_info=True)


async def get_or_create_user(
    telegram_user_id: int,
    phone_number: Optional[str],  # Mantido, mas não usado
    name: Optional[str],
    session: AsyncSession,
    create_if_not_exists: bool = True,
) -> Usuario:
    """
    Obtém um usuário pelo telegram_user_id ou cria um novo.
    """
    # Busca pelo campo correto, não pela PK
    result = await session.execute(
        select(Usuario).where(Usuario.telegram_user_id == telegram_user_id)
    )
    user = result.scalar_one_or_none()
    is_new_user = False
    needs_commit = False
    updated_fields: list[str] = []  # Inicializa como lista vazia
    current_time = utcnow()
    expected_phone = f'telegram_{telegram_user_id}'

    if not user and create_if_not_exists:
        try:
            user = await _create_new_user_instance(
                telegram_user_id, name, expected_phone, current_time, session
            )
            needs_commit = True
            is_new_user = True
        except Exception as e:
            await session.rollback()
            log_err_create_1 = (
                f'Erro ao instanciar/adicionar usuário ID '
                f'{telegram_user_id}. Exceção: {e}. '
            )
            # Modificado para incluir exc_info=True para traceback completo
            logger.error(log_err_create_1, exc_info=True)

            # Tentando buscar novamente.
            logger.info(
                f'Tentando buscar usuário ID {telegram_user_id} novamente '
                'após falha na criação.'
            )
            # Busca novamente pelo campo correto
            result = await session.execute(
                select(Usuario).where(
                    Usuario.telegram_user_id == telegram_user_id
                )
            )
            user = result.scalar_one_or_none()
            if not user:
                log_crit_create = f'Falha crítica ao obter/criar usuário ID {
                    telegram_user_id
                }.'
                logger.error(log_crit_create)
                # Adicionando log extra da exceção 'e' original com traceback
                logger.error(
                    f"Exceção original 'e' que levou à falha crítica na "
                    f"criação do usuário {telegram_user_id}: "
                    f"{type(e).__name__}: {str(e)}",
                    exc_info=True
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail='Não foi possível criar ou obter o usuário.',
                ) from e
            log_info_create = f'Usuário ID {
                telegram_user_id
            } encontrado após rollback na criação.'
            logger.info(log_info_create)
            is_new_user = False
            needs_commit = False

    elif not user and not create_if_not_exists:
        log_warn_not_found = f'Usuário ID {
            telegram_user_id
        } não encontrado (criação desabilitada).'
        logger.warning(log_warn_not_found)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Usuário com ID {telegram_user_id} não encontrado.',
        )

    # Se o usuário existe ou foi recuperado após falha na criação
    if user and not is_new_user:
        commit_needed, fields = await _update_existing_user_fields(
            user, name, expected_phone, current_time
        )
        if commit_needed:
            needs_commit = True
            updated_fields = fields

    if needs_commit and user:
        await _commit_user_changes_and_log(
            user, session, is_new_user, updated_fields, telegram_user_id
        )

    if not user:  # Checagem final de segurança
        logger.error(
            f"Crítico: 'user' é None no final de get_or_create_user "
            f'para ID {telegram_user_id} sem exceção prévia.'
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Erro inesperado ao processar dados do usuário.',
        )

    setattr(user, 'is_new', is_new_user)
    return user


async def get_current_user(
    session: AsyncSession = Depends(get_async_session),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        bearer_scheme
    ),
) -> Usuario:
    """
    Obtém o usuário atual baseado no token de autenticação JWT.
    O 'sub' do token JWT é esperado ser o ID do usuário.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Não foi possível validar as credenciais',
        headers={'WWW-Authenticate': 'Bearer'},
    )
    if credentials is None:
        logger.warning('Nenhuma credencial fornecida.')
        raise credentials_exception

    try:
        logger.debug(f'Token recebido: {credentials.credentials[:10]}...')
        payload = decode(
            credentials.credentials, settings.SECRET_KEY, algorithms=algorithms
        )
        user_id_str = payload.get('sub')

        if user_id_str is None:
            logger.warning('Token sem ID de usuário (sub)')
            raise credentials_exception

        try:
            user_id = int(user_id_str)
        except ValueError:
            logger.warning(
                f'ID de usuário (sub) no token não é um inteiro válido: '
                f'{user_id_str}'
            )
            raise credentials_exception

        logger.debug(f'Tentativa de autenticação para user_id: {user_id}')

    except ExpiredSignatureError:
        sub = payload.get('sub') if 'payload' in locals() else 'N/A'
        logger.warning(f'Token expirado para user_id (sub): {sub}')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token expirado. Solicite um novo token de acesso.',
            headers={
                'WWW-Authenticate': (
                    'Bearer error="invalid_token", '
                    'error_description="The access token expired"'
                )
            },
        )
    except DecodeError as e:
        logger.warning(f'Erro ao decodificar token: {str(e)}')
        raise credentials_exception
    except Exception as e:
        logger.error(f'Erro inesperado durante a decodificação do token: {e}')
        raise credentials_exception

    logger.debug(f'Buscando usuário com ID: {user_id}')
    user = await session.get(Usuario, user_id)

    if not user:
        logger.warning(f'Usuário não encontrado para ID: {user_id}')
        raise credentials_exception

    logger.info(
        f'Usuário autenticado: ID={user.id}, Nome={user.nome}, '
        f'Telefone={user.telefone}'
    )

    # A atualização do last_seen foi movida para get_or_create_user
    # e para o endpoint de registro explícito.
    # Manter aqui pode ser útil se o token for usado por um longo período
    # e quisermos rastrear a atividade via API de forma mais granular,
    # mesmo que get_or_create_user não seja chamado.
    # Por ora, comentamos para evitar escritas duplicadas se o fluxo
    # de registro/login sempre passar por get_or_create_user.
    # Se houver outros fluxos de autenticação que não passam por lá,
    # esta lógica pode precisar ser reavaliada.

    # try:
    #     # stmt = (
    #     #     update(Usuario)  # sqlalchemy.update não é mais usado aqui
    #     #     .where(Usuario.id == user.id)
    #     #     .values(last_seen=utcnow())
    #     # )
    #     # await session.execute(stmt)
    #     # await session.commit()
    #     pass # Mantendo o bloco try/except para o caso de reativar no futuro
    # except Exception as e:
    #     logger.warning(
    #         f'Erro ao atualizar last_seen para usuário {user.id} em '
    #         f'get_current_user: {str(e)}'
    #     )
    #     await session.rollback()

    return user


def check_permission(required_level: NivelAcesso):
    """
    Middleware para verificar se o usuário tem o nível de acesso requerido.
    """

    async def permission_checker(
        user: Usuario = Depends(get_current_user), request: Request = None
    ):
        try:
            nivel_acesso = user.nivel_acesso
        except AttributeError:
            try:
                nivel_acesso = user.__dict__.get('nivel_acesso')
            except Exception:
                logger.error(
                    'Não foi possível determinar o nível de acesso para o '
                    f'usuário {user.id}.'
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail='Erro ao verificar permissões do usuário.',
                )

        if nivel_acesso is None:
            logger.warning(
                f'Nível de acesso não definido para o usuário {user.id}.'
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Nível de acesso não configurado para este usuário.',
            )

        if nivel_acesso.value < required_level.value:
            logger.warning(
                f'Acesso negado para usuário {user.id} (nível {nivel_acesso}) '
                f'à rota {request.url.path if request else "desconhecida"} '
                f'(requer nível {required_level}).'
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Você não tem permissão para realizar esta ação.',
            )
        return user

    return permission_checker


def verify_telegram_webhook(
    x_telegram_bot_api_secret_token: Optional[str] = Header(None),
) -> bool:
    """Verifica o token secreto do webhook do Telegram."""
    if not settings.TELEGRAM_WEBHOOK_SECRET:
        logger.warning(
            'TELEGRAM_WEBHOOK_SECRET não está configurado. '
            'A verificação do webhook está desabilitada.'
        )
        return True

    if x_telegram_bot_api_secret_token is None:
        logger.error('Cabeçalho X-Telegram-Bot-Api-Secret-Token ausente.')
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Cabeçalho X-Telegram-Bot-Api-Secret-Token ausente.',
        )

    if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
        logger.error('Token secreto do webhook do Telegram inválido.')
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Token secreto do webhook do Telegram inválido.',
        )
    logger.debug(
        'Token secreto do webhook do Telegram verificado com sucesso.'
    )
    return True


require_intermediario = check_permission(NivelAcesso.intermediario)
require_super_usuario = check_permission(NivelAcesso.super_usuario)
