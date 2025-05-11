import hashlib
import hmac
import json
import logging
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from typing import NamedTuple, Optional, Tuple

from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import (
    DecodeError,
    ExpiredSignatureError,
    decode,
    encode,
)
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_async_session, utcnow
from .models import NivelAcesso, Usuario
from .settings import Settings

settings = Settings()
logger = logging.getLogger(__name__)
algorithms = getattr(settings, 'ALGORITHMS', ['HS256'])

# Regex para validar números de telefone no formato internacional
PHONE_REGEX = re.compile(r'^\+[1-9]\d{1,14}$')

# Rate limiting para prevenir ataques de força bruta
# Carrega as configurações das variáveis de ambiente
RATE_LIMIT_WINDOW = getattr(settings, 'RATE_LIMIT_WINDOW', 300)
# 5 minutos
MAX_LOGIN_ATTEMPTS = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)
# Máximo de tentativas

# Armazena tentativas de login por IP e por número de telefone
login_attempts = defaultdict(lambda: {'count': 0, 'last_attempt': 0})
failed_logins = defaultdict(int)

# Tempo de espera após muitas tentativas (em segundos)


def is_rate_limited(identifier: str) -> Tuple[bool, int]:
    """
    Verifica se um identificador (IP ou telefone) está bloqueado por tentativas
      excessivas
    Retorna (está_bloqueado, tempo_restante_bloqueio)
    """
    now = time.time()
    attempts = login_attempts[identifier]

    # Se nunca tentou antes, não está bloqueado
    if attempts['count'] == 0:
        return False, 0

    # Verifica se já passou o tempo de bloqueio
    time_passed = now - attempts['last_attempt']
    if (
        attempts['count'] >= MAX_LOGIN_ATTEMPTS
        and time_passed < RATE_LIMIT_WINDOW
    ):
        # Ainda está bloqueado
        return True, int(RATE_LIMIT_WINDOW - time_passed)

    # Se passou o tempo do bloqueio, reinicia as tentativas
    if time_passed > RATE_LIMIT_WINDOW:
        attempts['count'] = 0

    return False, 0


def record_login_attempt(identifier: str, success: bool) -> None:
    """Registra uma tentativa de login para fins de rate limiting"""
    now = time.time()
    attempts = login_attempts[identifier]

    # Atualiza o último momento da tentativa
    attempts['last_attempt'] = now

    # Se foi bem sucedido, reinicia a contagem
    if success:
        attempts['count'] = 0
        return

    # Incrementa a contagem de tentativas falhas
    attempts['count'] += 1


# Validação de webhook para WhatsApp e Telegram
def validate_webhook_signature(
    body: bytes, signature: str, secret: str
) -> bool:
    """
    Valida a assinatura de um webhook

    Args:
        body: O corpo da requisição em bytes
        signature: A assinatura fornecida pelo webhook
        secret: O segredo compartilhado para verificar a assinatura

    Returns:
        bool: True se a assinatura for válida, False caso contrário
    """
    if not signature or not secret:
        return False

    # Formato: sha256=hex_digest
    if signature.startswith('sha256='):
        signature = signature.replace('sha256=', '')

    # Calcula o HMAC com SHA-256
    expected_sig = hmac.new(
        secret.encode(), msg=body, digestmod=hashlib.sha256
    ).hexdigest()

    # Compara usando um método seguro de comparação de tempo constante
    return hmac.compare_digest(expected_sig, signature)


def create_whatsapp_token(phone_number: str):
    """Cria um token de acesso baseado no número do WhatsApp"""
    now = datetime.now(timezone.utc)
    to_encode = {
        'sub': phone_number,
        'iat': now,
        'exp': now + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS),
    }
    encoded_jwt = encode(to_encode, settings.SECRET_KEY, algorithm='HS256')
    return encoded_jwt


def validate_phone_number(phone_number: str) -> bool:
    """Valida se o número de telefone está em formato internacional válido"""
    return bool(PHONE_REGEX.match(phone_number))


async def verify_whatsapp_origin(
    phone_number: str,
    whatsapp_id: str = None,
    request: Request = None,
    signature: str = None,
) -> bool:
    """
    Verifica se a solicitação veio realmente do WhatsApp.

    Args:
        phone_number: Número de telefone do remetente
        whatsapp_id: ID da conta do WhatsApp Business
        request: Objeto da requisição para verificações adicionais
        signature: Assinatura HMAC do webhook

    Returns:
        bool: True se a origem for válida, False caso contrário
    """
    # Validação básica do número de telefone
    if not phone_number or not validate_phone_number(phone_number):
        logger.warning(f'Número de telefone inválido: {phone_number}')
        return False

    # Verificações de segurança em ambiente de produção
    # Reorganizadas para reduzir o número de returns

    # 1. Verificar ID do WhatsApp Business
    if settings.VERIFY_WHATSAPP_ID:
        if not whatsapp_id:
            logger.warning('ID do WhatsApp não fornecido')
            return False

        if whatsapp_id not in settings.ALLOWED_WHATSAPP_IDS:
            logger.warning(f'ID do WhatsApp não autorizado: {whatsapp_id}')
            return False

    # 2. Verificar assinatura HMAC (se fornecida)
    if settings.VERIFY_WHATSAPP_SIGNATURE and request and signature:
        valid_signature = await _verify_signature(request, signature)
        if not valid_signature:
            return False

    # 3. Verificar timestamp da mensagem para evitar replay attacks
    if settings.VERIFY_WHATSAPP_TIMESTAMP and request:
        valid_timestamp = await _verify_timestamp(request)
        if not valid_timestamp:
            return False

    # Se passou por todas as verificações aplicáveis
    return True


async def _verify_signature(request: Request, signature: str) -> bool:
    """Auxiliar para verificar assinatura do webhook"""
    try:
        # Recupera o corpo da requisição
        body = await request.body()

        # Verifica a assinatura com nosso segredo compartilhado
        if not validate_webhook_signature(
            body, signature, settings.WHATSAPP_WEBHOOK_SECRET
        ):
            logger.warning('Assinatura de webhook inválida')
            return False
    except Exception as e:
        logger.error(f'Erro ao verificar assinatura: {e}')
        return False

    return True


async def _verify_timestamp(request: Request) -> bool:
    """Auxiliar para verificar timestamp do webhook"""
    try:
        body = await request.json()
        timestamp = body.get('entry', [{}])[0].get('time')

        if not timestamp:
            logger.warning('Timestamp não encontrado na requisição')
            return False

        # Converte para datetime
        msg_time = datetime.fromtimestamp(
            timestamp / 1000, tz=timezone.utc
        )
        now = datetime.now(timezone.utc)

        # Definimos uma constante para o tempo máximo aceitável
        MAX_TIMESTAMP_DIFF_SECONDS = (
            settings.MAX_TIMESTAMP_DIFF_SECONDS
            if hasattr(settings, 'MAX_TIMESTAMP_DIFF_SECONDS')
            else 300
        )

        # Rejeita mensagens antigas ou futuras
        if (
            abs((now - msg_time).total_seconds())
            > MAX_TIMESTAMP_DIFF_SECONDS
        ):
            logger.warning(
                f'Timestamp inválido: {msg_time} (agora: {now})'
            )
            return False
    except Exception as e:
        logger.error(f'Erro ao verificar timestamp: {e}')
        # Em produção, você pode decidir se falha aberta ou fechada
        return False

    return True


# Esquema de segurança personalizado para WhatsApp
class WhatsAppBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(
        self, request: Request, x_whatsapp_phone: str = Header(None)
    ) -> HTTPAuthorizationCredentials:
        credentials = await super().__call__(request)

        if credentials:
            # Se o cabeçalho x_whatsapp_phone está presente, valida a origem
            # do WhatsApp
            if x_whatsapp_phone:
                is_valid = await verify_whatsapp_origin(x_whatsapp_phone)
                if not is_valid:
                    raise HTTPException(
                        status_code=HTTPStatus.UNAUTHORIZED,
                        detail='Origem do WhatsApp inválida',
                    )
            return credentials

        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail='Credenciais inválidas',
        )


whatsapp_scheme = WhatsAppBearer()


async def get_auto_user_by_phone(
    phone_number: str,
    session: AsyncSession,
    create_if_not_exists: bool = True,
):
    """
    Obtém usuário pelo número do telefone ou cria automaticamente
    se não existir e a flag create_if_not_exists for True
    """
    # Primeira tentativa de localizar o usuário
    stmt = select(Usuario).where(Usuario.telefone == phone_number)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    is_new_user = False  # Flag para indicar se é um usuário novo

    if not user and create_if_not_exists:
        try:
            # Certifique-se de que o campo `id` não seja passado ao criar o
            #  objeto `Usuario`
            user = Usuario(
                telefone=phone_number, nivel_acesso=NivelAcesso.basico
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            is_new_user = True  # Marca como usuário novo
        except Exception:
            # Em caso de erro (possível violação de unicidade
            # se outro processo criou o mesmo usuário)
            await session.rollback()

            # Tenta buscar novamente após falha na criação
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            # Se ainda não encontrou, propaga o erro
            if not user:
                # Em produção, adicione logging aqui
                raise

    # Adiciona a propriedade is_new ao objeto do usuário
    if user and is_new_user:
        setattr(user, 'is_new', True)
    else:
        setattr(user, 'is_new', False)

    return user


async def get_current_user(
    session: AsyncSession = Depends(get_async_session),
    credentials: HTTPAuthorizationCredentials = Depends(whatsapp_scheme),
):
    """
    Obtém o usuário atual baseado no token de autenticação do WhatsApp
    """
    credentials_exception = HTTPException(
        status_code=HTTPStatus.UNAUTHORIZED,
        detail='Não foi possível validar as credenciais',
        headers={'WWW-Authenticate': 'Bearer'},
    )

    try:
        # Log para debug - mostrar o token para depuração
        logger.info(f'Token recebido: {credentials.credentials[:10]}...')

        payload = decode(
            credentials.credentials, settings.SECRET_KEY, algorithms=['HS256']
        )
        phone_number = payload.get('sub')

        if not phone_number:
            logger.warning('Token sem número de telefone (sub)')
            raise credentials_exception

        # Log para debug
        logger.info(f'Tentativa de autenticação para telefone: {phone_number}')

    except DecodeError as e:
        logger.warning(f'Erro ao decodificar token: {str(e)}')
        raise credentials_exception

    except ExpiredSignatureError:
        # Token expirado, verificar se deve renovar automaticamente
        try:
            # Decodificar sem verificar a expiração para obter o número
            #  do telefone
            payload = decode(
                credentials.credentials,
                settings.SECRET_KEY,
                algorithms,
                options={'verify_exp': False},
            )
            phone_number = payload.get('sub')

            if not phone_number:
                logger.warning('Token expirado sem número de telefone (sub)')
                raise credentials_exception

            logger.warning(f'Token expirado para telefone: {phone_number}')

            # Retorna exceção de token expirado com informação adicional
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail='Token expirado. Solicite um novo token de acesso.',
                headers={
                    'WWW-Authenticate': 'Bearer',
                    'X-Token-Expired': 'true',
                },
            )

        except Exception as e:
            logger.warning(f'Erro ao processar token expirado: {str(e)}')
            # Se houver qualquer erro ao tentar renovar, retorna a exceção
            #  padrão
            raise credentials_exception

    # Consulta usuário - log explícito para debug
    logger.info(f'Buscando usuário com telefone: {phone_number}')

    # Consulta apenas os campos do usuário, sem relacionamentos
    stmt = select(
        Usuario.id,
        Usuario.telefone,
        Usuario.nivel_acesso,
        Usuario.nome,
        Usuario.created_at,
        Usuario.last_seen,
    ).where(Usuario.telefone == phone_number)

    result = await session.execute(stmt)
    user_data = result.one_or_none()

    if not user_data:
        logger.warning(f'Usuário não encontrado para telefone: {phone_number}')

        # Verificar se existem usuários no sistema
        check_stmt = select(Usuario.id, Usuario.telefone).limit(5)
        result = await session.execute(check_stmt)
        users = result.all()
        if users:
            logger.info(f'Usuários existentes no sistema: {users}')

        raise credentials_exception

    # Criar objeto Usuario apenas com os dados que precisamos
    # Isso evita tentar carregar os relacionamentos
    user = Usuario(
        telefone=user_data.telefone,
        nivel_acesso=user_data.nivel_acesso,
        nome=user_data.nome,
    )
    # Atribuir os valores que não são aceitos no construtor
    user.id = user_data.id
    user.created_at = user_data.created_at
    user.last_seen = user_data.last_seen

    logger.info(f'Usuário autenticado: ID={user.id}, Telefone={user.telefone}')

    try:
        # Atualizar last_seen usando a função utcnow corrigida
        # Atualizar diretamente no banco, sem tentar carregar o objeto completo
        stmt = (
            update(Usuario)
            .where(Usuario.id == user.id)
            .values(last_seen=utcnow())  # Usando utcnow() da database
        )
        await session.execute(stmt)
        await session.commit()
    except Exception as e:
        logger.warning(f'Erro ao atualizar last_seen: {str(e)}')
        await session.rollback()
        # Não bloqueia o acesso se falhar a atualização do last_seen

    # Retorna o objeto do banco de dados diretamente
    return user


async def get_user_by_phone(
    phone_number: str,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Endpoint para o Webhook do WhatsApp - autenticação automática pelo número
    """
    if not validate_phone_number(phone_number):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='Número de telefone inválido',
        )

    # Obtém ou cria usuário automaticamente
    user = await get_auto_user_by_phone(phone_number, session)

    if not user:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Usuário não encontrado e não foi possível criar',
        )

    return user


# Dependência para verificar níveis de acesso
def check_permission(required_level: NivelAcesso):
    """
    Middleware para verificar se o usuário tem o nível de acesso requerido.

    Esta função verifica de maneira robusta o nível de acesso do usuário,
    tentando várias abordagens para acessar o atributo nivel_acesso.
    Registra tentativas de acesso não autorizado para fins de auditoria.

    Args:
        required_level: Nível de acesso mínimo necessário para a operação

    Returns:
        Uma função de dependência que pode ser usada em rotas FastAPI
    """

    async def permission_checker(
        user: Usuario = Depends(get_current_user), request: Request = None
    ):
        # Tentativa robusta de obter o nível de acesso
        try:
            nivel_acesso = user.nivel_acesso
        except Exception:
            try:
                nivel_acesso = user.__dict__.get('nivel_acesso')
            except Exception:
                nivel_acesso = getattr(user, 'nivel_acesso', None)

        if nivel_acesso is None:
            logger.warning(
                f'Nível de acesso não encontrado. Objeto type: {type(user)}'
            )
            logger.warning(f'Objeto dir: {dir(user)}')

            # Registro mais detalhado para auditoria de segurança
            log_security_event(
                SecurityEvent(
                    event_type='access_denied',
                    user_id=getattr(user, 'id', None),
                    user_phone=getattr(user, 'telefone', None),
                    details='Não foi possível determinar o nível de acesso',
                    ip_address=get_client_ip(request) if request else None,
                    endpoint=request.url.path if request else None,
                )
            )

            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail='Não foi possível determinar '
                'o nível de acesso do usuário',
            )

        # Se o nível for insuficiente
        if nivel_acesso.value < required_level.value:
            detail_message = (
                f'Acesso insuficiente. Nível necessário: {required_level.name}'
            )

            # Registro detalhado da tentativa não autorizada
            log_security_event(
                SecurityEvent(
                    event_type='insufficient_permission',
                    user_id=user.id,
                    user_phone=user.telefone,
                    details=(
                        f'Tentativa de acesso com nível {nivel_acesso.name}, '
                        f'necessário: {required_level.name}'
                    ),
                    ip_address=get_client_ip(request) if request else None,
                    endpoint=request.url.path if request else None,
                )
            )

            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail=detail_message,
            )

        # Registro de auditoria para acesso bem-sucedido de níveis elevados
        if nivel_acesso.value >= NivelAcesso.intermediario.value:
            log_security_event(
                SecurityEvent(
                    event_type='admin_access',
                    user_id=user.id,
                    user_phone=user.telefone,
                    details=f'Acesso com nível {nivel_acesso.name}',
                    ip_address=get_client_ip(request) if request else None,
                    endpoint=request.url.path if request else None,
                )
            )

        return user

    return permission_checker


def get_client_ip(request: Request) -> Optional[str]:
    """
    Obtém o endereço IP real do cliente, considerando proxies e cabeçalhos
    de encaminhamento

    Args:
        request: O objeto Request do FastAPI

    Returns:
        O endereço IP do cliente ou None se não for possível determiná-lo
    """
    if not request:
        return None

    # Verifica cabeçalhos comuns de proxy
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        # Pega o primeiro IP da lista (o IP original do cliente)
        return forwarded_for.split(',')[0].strip()

    # Cabeçalho alternativo
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip

    # Caso não tenha cabeçalhos de proxy, usa o cliente direto
    try:
        return request.client.host
    except Exception:
        return None


class SecurityEvent(NamedTuple):
    """Estrutura para eventos de segurança para facilitar o log"""

    event_type: str
    user_id: Optional[int] = None
    user_phone: Optional[str] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    endpoint: Optional[str] = None


def log_security_event(event: SecurityEvent) -> None:
    """
    Registra um evento de segurança para auditoria

    Args:
        event: Objeto SecurityEvent com informações do evento
    """
    # Formata a mensagem para o log
    log_data = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'event_type': event.event_type,
        'user_id': event.user_id,
        'user_phone': event.user_phone,
        'details': event.details,
        'ip_address': event.ip_address,
        'endpoint': event.endpoint,
    }

    # Registra no logger dedicado a eventos de segurança
    security_logger = logging.getLogger('security')
    security_logger.info(json.dumps(log_data))

    # TODO: Em ambiente de produção, considerar salvar esses logs
    # em uma tabela específica do banco de dados ou enviar para
    # um sistema externo de monitoramento de segurança.


# Dependências específicas por nível
require_intermediario = check_permission(NivelAcesso.intermediario)
require_super_usuario = check_permission(NivelAcesso.super_usuario)


# Funções de validação segura para Telegram
def verify_telegram_webhook(secret_token: str) -> bool:
    """
    Verifica se a solicitação veio realmente do Telegram

    Args:
        secret_token: Token secreto do webhook do Telegram

    Returns:
        bool: True se a origem for válida, False caso contrário
    """
    # Verifica se o token secreto está configurado
    if not settings.TELEGRAM_SECRET_TOKEN:
        logger.warning('Token secreto do Telegram não configurado')
        return False

    # Validação de token secreto - usamos comparação com tempo constante
    # para prevenir timing attacks
    if not secret_token or not hmac.compare_digest(
        settings.TELEGRAM_SECRET_TOKEN, secret_token
    ):
        logger.warning('Token secreto do Telegram inválido')
        return False

    return True


async def authenticate_with_rate_limit(
    phone_number: str, ip_address: str, session: AsyncSession
) -> Tuple[Usuario, str, bool]:
    """
    Autentica um usuário com proteção contra ataques de força bruta

    Args:
        phone_number: Número de telefone do usuário
        ip_address: Endereço IP do cliente
        session: Sessão do banco de dados

    Returns:
        Tupla (usuario, token, é_novo)
    """
    # Verifica rate limiting por IP
    is_limited, wait_seconds = is_rate_limited(ip_address)
    if is_limited:
        log_security_event(
            SecurityEvent(
                event_type='rate_limited',
                user_phone=phone_number,
                details=f'Bloqueado por rate limit. Aguardar {wait_seconds}s',
                ip_address=ip_address,
            )
        )
        raise HTTPException(
            status_code=HTTPStatus.TOO_MANY_REQUESTS,
            detail=(
            f'Muitas tentativas. Tente novamente em {wait_seconds} segundos'
            ),
            headers={'Retry-After': str(wait_seconds)},
        )

    # Busca ou cria o usuário
    try:
        user = await get_auto_user_by_phone(phone_number, session)

        # Verificar se é novo
        is_new = getattr(user, 'is_new', False)

        # Gera o token de acesso
        token = create_whatsapp_token(phone_number)

        # Registra o sucesso no rate limiting
        record_login_attempt(ip_address, True)

        # Registra o evento de login bem-sucedido
        log_security_event(
            SecurityEvent(
                event_type='login',
                user_id=user.id,
                user_phone=user.telefone,
                details=(
                    'Login bem-sucedido'
                    + (' (novo usuário)' if is_new else '')
                ),
                ip_address=ip_address,
            )
        )

        return user, token, is_new

    except Exception as e:
        # Registra a falha no rate limiting
        record_login_attempt(ip_address, False)

        # Registra o evento de falha no login
        log_security_event(
            SecurityEvent(
                event_type='login_failed',
                user_phone=phone_number,
                details=f'Falha no login: {str(e)}',
                ip_address=ip_address,
            )
        )

        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED, detail='Falha na autenticação'
        )
