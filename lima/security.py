import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import DecodeError, ExpiredSignatureError, decode, encode
from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .core.loading_options import USER_LOAD_OPTIONS_MINIMAL
from .database import get_async_session
from .models import NivelAcesso, Usuario
from .settings import settings

logger = logging.getLogger(__name__)
algorithms = getattr(settings, 'ALGORITHMS', ['HS256'])

RATE_LIMIT_WINDOW = getattr(settings, 'RATE_LIMIT_WINDOW', 300)
MAX_LOGIN_ATTEMPTS = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)
login_attempts = defaultdict(lambda: {'count': 0, 'last_attempt': 0})

bearer_scheme = HTTPBearer()
bearer_scheme_optional = HTTPBearer(auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Cria um token de acesso JWT para o usuário."""
    now = datetime.now(timezone.utc)
    to_encode = {
        'sub': str(data.get('user_id')),  # ID interno do usuário
        'iat': now,
        'exp': now + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS),
        'tid': str(data.get('telegram_user_id')),  # ID do Telegram
        'type': 'telegram_user',
    }
    encoded_jwt = encode(
        to_encode, settings.SECRET_KEY, algorithm=algorithms[0]
    )
    return encoded_jwt


async def _create_new_user_instance(
    telegram_user_id: int,
    name: Optional[str],
    expected_phone: Optional[str],
    current_time: datetime,
    session: AsyncSession,
) -> Usuario:
    """Cria uma nova instância de usuário, mas não faz commit."""
    logger.info(
        f'Usuário com Telegram ID {telegram_user_id} não encontrado. Criando.'
    )
    user = Usuario(
        telegram_user_id=telegram_user_id,
        telefone=expected_phone,
        nome=name,
        nivel_acesso=NivelAcesso.basico,
    )
    user.last_seen = current_time
    session.add(user)
    return user


async def _update_existing_user_fields(
    user: Usuario,
    name: Optional[str],
    expected_phone: Optional[str],
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

    user_last_seen_for_comparison = user.last_seen
    if (
        user_last_seen_for_comparison
        and user_last_seen_for_comparison.tzinfo is None
    ):
        user_last_seen_for_comparison = user_last_seen_for_comparison.replace(
            tzinfo=timezone.utc
        )

    if user_last_seen_for_comparison != current_time:
        user.last_seen = current_time
        updated_fields.append('last_seen')
        needs_commit = True
    return needs_commit, updated_fields


async def _commit_user_changes_and_log(
    session: AsyncSession,
    user: Usuario,
    action: str,
    updated_fields: Optional[list[str]] = None,
):
    """Faz commit das alterações do usuário e registra a operação."""
    user_id_for_logging = user.id
    try:
        await session.commit()
        await session.refresh(user)
        log_message = f'Usuário {action}: {user_id_for_logging}.'
        if updated_fields:
            log_message += f' Campos atualizados: {", ".join(updated_fields)}.'
        logger.info(log_message)
    except Exception as e:
        await session.rollback()
        logger.error(f'Erro ao {action} usuário {user_id_for_logging}: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro interno ao processar usuário: {e}',
        )


async def get_or_create_user_by_telegram_id(
    session: AsyncSession,
    telegram_user_id: int,
    name: Optional[str],
    expected_phone: Optional[str],
) -> Usuario:
    """Obtém ou cria um usuário pelo ID do Telegram."""
    current_time = datetime.now(timezone.utc)
    user = await session.scalar(
        select(Usuario)
        .options(*USER_LOAD_OPTIONS_MINIMAL)
        .where(Usuario.telegram_user_id == telegram_user_id)
    )

    if user:
        needs_commit, updated_fields = await _update_existing_user_fields(
            user, name, expected_phone, current_time
        )
        if needs_commit:
            await _commit_user_changes_and_log(
                session, user, 'atualizado', updated_fields
            )
    else:
        user = await _create_new_user_instance(
            telegram_user_id, name, expected_phone, current_time, session
        )
        await _commit_user_changes_and_log(session, user, 'criado')

    return user


class TelegramUserHeaders(BaseModel):
    x_telegram_user_id: Optional[str] = None
    x_user_name: Optional[str] = None
    x_expected_phone: Optional[str] = None

    @classmethod
    async def from_request(cls, request: Request) -> 'TelegramUserHeaders':
        return cls(
            x_telegram_user_id=request.headers.get('x-telegram-user-id'),
            x_user_name=request.headers.get('x-user-name'),
            x_expected_phone=request.headers.get('x-expected-phone'),
        )


class TokenPayload(BaseModel):
    sub: str  # ID interno do usuário
    tid: str  # ID do Telegram
    type: str
    exp: int
    iat: int


def _decode_token_payload(
    token_credentials: str, ip_address: str, current_timestamp: int
) -> TokenPayload:
    """Decodifica o token e retorna o payload validado."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Não foi possível validar as credenciais',
        headers={'WWW-Authenticate': 'Bearer'},
    )
    try:
        payload_dict = decode(
            token_credentials, settings.SECRET_KEY, algorithms=algorithms
        )
        payload = TokenPayload(**payload_dict)

        if payload.type != 'telegram_user':
            login_attempts[ip_address]['count'] += 1
            login_attempts[ip_address]['last_attempt'] = current_timestamp
            logger.warning(
                'Token inválido: tipo de token incorreto. '
                f'ID Usuário (sub): {payload.sub}, '
                f'ID Telegram (tid): {payload.tid}, Tipo: {payload.type}'
            )
            raise credentials_exception
        return payload

    except ExpiredSignatureError:
        logger.warning('Token expirado.')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token expirado',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    except (DecodeError, ValidationError) as e:
        login_attempts[ip_address]['count'] += 1
        login_attempts[ip_address]['last_attempt'] = current_timestamp
        logger.warning(f'Erro de decodificação/validação do token: {e}')
        raise credentials_exception


async def _fetch_and_update_user(
    session: AsyncSession,
    internal_user_id: int,
    header_telegram_user_id: int,
    custom_headers: TelegramUserHeaders,
    credentials_exception: HTTPException,
) -> Usuario:
    """Busca o usuário pelo ID interno e atualiza seus dados."""
    user = await session.scalar(
        select(Usuario)
        .options(*USER_LOAD_OPTIONS_MINIMAL)
        .where(Usuario.id == internal_user_id)  # Usar o ID interno
    )

    if user is None:
        logger.warning(
            'Usuário não encontrado no banco de dados para o ID interno '
            f'do token: {internal_user_id}'
        )
        raise credentials_exception

    if user.telegram_user_id != header_telegram_user_id:
        logger.error(
            'Discrepância crítica de ID do Telegram: DB '
            f'({user.telegram_user_id}) vs Cabeçalho/Token TID '
            f'({header_telegram_user_id}). Token sub (ID interno): {user.id}.'
        )
        # Isso pode indicar uma adulteração ou um problema sério de
        # consistência.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                'Discrepância entre ID do Telegram no token e no cabeçalho.'
            ),
        )

    needs_commit, updated_fields = await _update_existing_user_fields(
        user,
        custom_headers.x_user_name,
        custom_headers.x_expected_phone,
        datetime.now(timezone.utc),
    )
    if needs_commit:
        await _commit_user_changes_and_log(
            session, user, 'atualizado via token', updated_fields
        )
    return user


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    token: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    custom_headers: TelegramUserHeaders = Depends(
        TelegramUserHeaders.from_request
    ),
) -> Usuario:
    """Obtém o usuário atual com base no token e cabeçalhos."""
    logger.debug(
        f'get_current_user - Cabeçalhos: {custom_headers.model_dump_json()}'
    )
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Não foi possível validar as credenciais',
        headers={'WWW-Authenticate': 'Bearer'},
    )

    ip_address = request.client.host if request.client else 'unknown'
    current_timestamp = int(datetime.now(timezone.utc).timestamp())

    if (
        login_attempts[ip_address]['count'] >= MAX_LOGIN_ATTEMPTS
        and current_timestamp - login_attempts[ip_address]['last_attempt']
        < RATE_LIMIT_WINDOW
    ):
        logger.warning(f'Rate limit excedido para o IP: {ip_address}')
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail='Muitas tentativas de login. Tente novamente mais tarde.',
        )

    payload = _decode_token_payload(
        token.credentials, ip_address, current_timestamp
    )

    # Validar consistência entre token 'tid' e cabeçalho X-Telegram-User-Id
    if not custom_headers.x_telegram_user_id:
        logger.error(
            'Cabeçalho x-telegram-user-id ausente, mas token JWT presente.'
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Cabeçalho x-telegram-user-id ausente.',
        )

    try:
        header_telegram_user_id = int(custom_headers.x_telegram_user_id)
        token_telegram_user_id = int(payload.tid)
        internal_user_id_from_token = int(payload.sub)
    except ValueError:
        logger.error(
            'Valores inválidos para IDs no token ou cabeçalho: '
            f'token_tid={payload.tid}, header_x_id='
            f'{custom_headers.x_telegram_user_id}, token_sub={payload.sub}'
        )
        raise credentials_exception

    if token_telegram_user_id != header_telegram_user_id:
        logger.error(
            'Discrepância de ID do Telegram: Token TID '
            f'({token_telegram_user_id}) vs Cabeçalho '
            f'({header_telegram_user_id}). Token sub: {payload.sub}.'
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                'Discrepância entre ID do Telegram no token e no cabeçalho.'
            ),
        )

    user = await _fetch_and_update_user(
        session,
        internal_user_id_from_token,
        header_telegram_user_id,  # Passando o ID do Telegram validado
        custom_headers,
        credentials_exception,
    )

    login_attempts[ip_address]['count'] = 0  # Resetar tentativas
    logger.info(f'Usuário {user.id} autenticado com sucesso.')
    return user


async def _process_optional_user_with_headers(
    session: AsyncSession, custom_headers: TelegramUserHeaders
) -> Optional[Usuario]:
    """Processa usuário opcional baseado apenas em cabeçalhos."""
    if not custom_headers.x_telegram_user_id:
        logger.debug(
            'get_optional_current_user - Sem token e sem header '
            'X-Telegram-User-Id.'  # noqa: E501
        )
        return None
    try:
        telegram_user_id = int(custom_headers.x_telegram_user_id)
        logger.debug(
            'get_optional_current_user - Sem token, com header '
            f'X-Telegram-User-Id: {telegram_user_id}'
        )
        user = await get_or_create_user_by_telegram_id(
            session=session,
            telegram_user_id=telegram_user_id,
            name=custom_headers.x_user_name,
            expected_phone=custom_headers.x_expected_phone,
        )
        if user:
            logger.info(
                f'Usuário opcional {user.id} identificado via cabeçalhos.'
            )
        return user
    except ValueError:
        logger.warning(
            'Valor inválido para x-telegram-user-id (sem token): '
            f'{custom_headers.x_telegram_user_id}'
        )
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f'Erro ao processar usuário opcional via cabeçalhos: {e}')
    return None


async def _validate_token_payload_and_headers(
    token: HTTPAuthorizationCredentials,
    custom_headers: TelegramUserHeaders,
) -> Optional[tuple[int, int]]:
    """
    Valida o token e os cabeçalhos.
    Retorna uma tupla (internal_user_id, telegram_user_id_from_header)
    se válido.
    """
    try:
        payload = _decode_token_payload(token.credentials, 'optional', 0)

        if not custom_headers.x_telegram_user_id:
            logger.warning(
                'Cabeçalho x-telegram-user-id ausente para usuário opcional '
                'com token.'  # noqa: E501
            )
            return None

        header_telegram_user_id_str = custom_headers.x_telegram_user_id
        token_telegram_user_id_str = payload.tid
        internal_user_id_str = payload.sub

        if token_telegram_user_id_str != header_telegram_user_id_str:
            logger.warning(
                'Discrepância de ID do Telegram (opcional): Token TID '
                f'({token_telegram_user_id_str}) vs Cabeçalho '
                f'({header_telegram_user_id_str}). '
                f'Token sub: {internal_user_id_str}.'
            )  # noqa: E501
            return None

        return int(internal_user_id_str), int(header_telegram_user_id_str)

    except ValueError:
        logger.warning(
            'Valor inválido para ID no token ou cabeçalho (opcional).'
        )
    except HTTPException as e:  # Captura exceções de _decode_token_payload
        logger.info(f'Erro de token para usuário opcional: {e.detail}')
    except Exception as e:  # pylint: disable=broad-except
        logger.error(
            f'Erro inesperado na validação de token/cabeçalhos (opcional): {e}'
        )
    return None


async def _get_and_update_optional_user(
    session: AsyncSession,
    internal_user_id: int,
    header_telegram_user_id: int,  # ID do Telegram validado do cabeçalho
    custom_headers: TelegramUserHeaders,
) -> Optional[Usuario]:
    """Busca ou cria, e atualiza o usuário opcional."""
    try:
        user = await session.scalar(
            select(Usuario)
            .options(*USER_LOAD_OPTIONS_MINIMAL)
            .where(Usuario.id == internal_user_id)  # Usar ID interno
        )

        if user is None:
            logger.error(
                f'Usuário opcional não encontrado no DB pelo ID interno '
                f'{internal_user_id}. Isso pode indicar um token órfão. '
                f'Tentando criar/buscar por ID Telegram do header: '
                f'{header_telegram_user_id}.'
            )  # noqa: E501
            # Se o usuário com ID interno não existe, mas o token e header
            # são consistentes quanto ao telegram_id, podemos tentar
            # buscar/criar por esse telegram_id.
            user = await get_or_create_user_by_telegram_id(
                session=session,
                telegram_user_id=header_telegram_user_id,  # Usar ID do header
                name=custom_headers.x_user_name,
                expected_phone=custom_headers.x_expected_phone,
            )
            if user:
                logger.info(
                    'Usuário opcional recriado/encontrado por Telegram ID '
                    f'{header_telegram_user_id} e associado ao ID interno '
                    f'{user.id} (originalmente esperado {internal_user_id}).'
                )  # noqa: E501
            else:
                logger.error(
                    'Não foi possível criar/encontrar usuário opcional com '
                    f'Telegram ID {header_telegram_user_id}.'
                )  # noqa: E501
                return None  # Falha crítica se não conseguir nem criar

        # Validação adicional: o telegram_user_id do usuário encontrado
        # deve corresponder ao header_telegram_user_id.
        # Isso é especialmente importante se o usuário foi
        # recriado/buscado acima.
        if user.telegram_user_id != header_telegram_user_id:
            logger.warning(
                'Discrepância no _get_and_update_optional_user: '
                f'user.telegram_user_id ({user.telegram_user_id}) '
                f'!= header_telegram_id ({header_telegram_user_id}). '
                f'User ID interno: {user.id}.'
            )
            # Se a discrepância persistir mesmo após a tentativa de
            # get_or_create, é um problema sério.
            return None

        needs_commit, updated_fields = await _update_existing_user_fields(
            user,
            custom_headers.x_user_name,
            custom_headers.x_expected_phone,
            datetime.now(timezone.utc),
        )
        if needs_commit:
            await _commit_user_changes_and_log(
                session, user, 'atualizado opcionalmente', updated_fields
            )
        logger.info(f'Usuário opcional {user.id} processado.')
        return user

    except Exception as e:  # pylint: disable=broad-except
        logger.error(
            f'Erro ao buscar/atualizar usuário opcional (ID interno '
            f'{internal_user_id}): {e}'
        )  # noqa: E501
    return None


async def get_optional_current_user(
    request: Request,  # Adicionado para consistência, não usado diretamente
    session: AsyncSession = Depends(get_async_session),
    token: Optional[HTTPAuthorizationCredentials] = Depends(
        bearer_scheme_optional
    ),
    custom_headers: TelegramUserHeaders = Depends(
        TelegramUserHeaders.from_request
    ),
) -> Optional[Usuario]:
    """
    Obtém o usuário atual se um token JWT válido for fornecido e os cabeçalhos
    forem consistentes, ou se os cabeçalhos X-Telegram-* forem fornecidos
    e um usuário puder ser identificado/criado. Retorna None caso contrário.
    """
    logger.debug(
        'get_optional_current_user - Token: '
        f'{"Presente" if token else "Ausente"}, '
        f'Cabeçalhos: {custom_headers.model_dump_json()}'
    )

    if token and token.credentials:
        validation_result = await _validate_token_payload_and_headers(
            token, custom_headers
        )
        if validation_result:
            internal_user_id, header_telegram_user_id = validation_result
            logger.info(
                'Usuário opcional: Token e cabeçalhos validados. ID interno: '
                f'{internal_user_id}, ID Telegram header: '
                f'{header_telegram_user_id}'
            )  # noqa: E501
            return await _get_and_update_optional_user(
                session,
                internal_user_id,
                header_telegram_user_id,
                custom_headers,
            )
        else:
            logger.warning(
                'Usuário opcional: Token presente, mas inválido ou '
                'inconsistente com cabeçalhos. Tentando via cabeçalhos apenas.'
            )

    return await _process_optional_user_with_headers(session, custom_headers)


# Funções de dependência para diferentes níveis de acesso
async def require_nivel_acesso(
    current_user: Usuario,
    nivel_necessario: NivelAcesso,
    mensagem_erro: str = 'Acesso negado: Nível de permissão insuficiente.',
) -> Usuario:
    """Verifica se o usuário tem o nível de acesso necessário."""
    niveis_permitidos = {
        NivelAcesso.basico: {
            NivelAcesso.basico,
            NivelAcesso.intermediario,
            NivelAcesso.super_usuario,
        },
        NivelAcesso.intermediario: {
            NivelAcesso.intermediario,
            NivelAcesso.super_usuario,
        },
        NivelAcesso.super_usuario: {NivelAcesso.super_usuario},
    }

    if current_user.nivel_acesso not in niveis_permitidos.get(
        nivel_necessario, set()
    ):
        logger.warning(
            f'Acesso não autorizado por {current_user.id} '
            f'(nível {current_user.nivel_acesso}) para recurso de nível '
            f'{nivel_necessario}'
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=mensagem_erro
        )
    return current_user


async def require_intermediario(
    current_user: Usuario = Depends(get_current_user),
) -> Usuario:
    """Exige que o usuário seja intermediário ou superior."""
    return await require_nivel_acesso(
        current_user,
        NivelAcesso.intermediario,
        'Acesso restrito a usuários intermediários ou superiores.',
    )


async def require_super_usuario(
    current_user: Usuario = Depends(get_current_user),
) -> Usuario:
    """Exige que o usuário seja super usuário."""
    return await require_nivel_acesso(
        current_user,
        NivelAcesso.super_usuario,
        'Acesso restrito a super usuários.',
    )


async def _get_user_from_telegram_headers(
    request: Request, session: AsyncSession
) -> Optional[Usuario]:
    """Tenta obter/criar um usuário baseado nos cabeçalhos do Telegram."""
    telegram_user_id_header = request.headers.get('x-telegram-user-id')
    user_name_header = request.headers.get('x-user-name')
    expected_phone_header = request.headers.get('x-expected-phone')

    logger.info(
        'DEBUG: _get_user_from_telegram_headers - '
        f'x-telegram-user-id: {telegram_user_id_header}'
    )
    logger.info(
        'DEBUG: _get_user_from_telegram_headers - '
        f'x-user-name: {user_name_header}'
    )
    logger.info(
        'DEBUG: _get_user_from_telegram_headers - '
        f'x-expected-phone: {expected_phone_header}'
    )

    if not telegram_user_id_header:
        logger.info(
            'DEBUG: _get_user_from_telegram_headers - '
            'Cabeçalho x-telegram-user-id ausente.'
        )
        return None

    try:
        telegram_user_id = int(telegram_user_id_header)
    except ValueError:
        logger.warning(
            'DEBUG: _get_user_from_telegram_headers - '
            'Valor inválido para x-telegram-user-id: '
            f'{telegram_user_id_header}'
        )
        return None

    user = await get_or_create_user_by_telegram_id(
        session=session,
        telegram_user_id=telegram_user_id,
        name=user_name_header,
        expected_phone=expected_phone_header,
    )

    if user:
        logger.info(
            'DEBUG: _get_user_from_telegram_headers - '
            f'Usuário {user.id} obtido/criado via cabeçalhos.'
        )
    else:
        logger.error(
            'DEBUG: _get_user_from_telegram_headers - Falha ao obter ou '
            'criar usuário, get_or_create_user_by_telegram_id retornou '
            'None inesperadamente.'
        )
    return user
