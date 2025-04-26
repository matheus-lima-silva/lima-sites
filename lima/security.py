import re
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from zoneinfo import ZoneInfo

from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import DecodeError, ExpiredSignatureError, decode, encode
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_async_session
from .models import NivelAcesso, Usuario
from .settings import Settings

settings = Settings()

# Regex para validar números de telefone no formato internacional
PHONE_REGEX = re.compile(r'^\+[1-9]\d{1,14}$')


def create_whatsapp_token(phone_number: str):
    """Cria um token de acesso baseado no número do WhatsApp"""
    now = datetime.now(tz=ZoneInfo('UTC'))
    to_encode = {
        'sub': phone_number,
        'iat': now,
        'exp': now + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS),
    }
    encoded_jwt = encode(
        to_encode, settings.SECRET_KEY, algorithm='HS256'
    )
    return encoded_jwt


def validate_phone_number(phone_number: str) -> bool:
    """Valida se o número de telefone está em formato internacional válido"""
    return bool(PHONE_REGEX.match(phone_number))


def verify_whatsapp_origin(phone_number: str, whatsapp_id: str = None) -> bool:
    """
    Verifica se a solicitação veio realmente do WhatsApp.
    Em produção, isso verificaria assinaturas, IDs da plataforma, etc.
    """
    # Implementação simplificada - em produção, faça validações mais robustas
    if not phone_number:
        return False

    # Validação básica do formato do telefone
    if not validate_phone_number(phone_number):
        return False

    # Em produção: verificar assinaturas do WhatsApp Cloud API
    # e validar whatsapp_id contra a configuração da plataforma

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
            # Se o cabeçalho x_whatsapp_phone está presente, valida a origem do WhatsApp
            if x_whatsapp_phone and not verify_whatsapp_origin(x_whatsapp_phone):
                raise HTTPException(
                    status_code=HTTPStatus.UNAUTHORIZED,
                    detail="Origem do WhatsApp inválida",
                )
            return credentials
            
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="Credenciais inválidas",
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
    stmt = select(Usuario).where(Usuario.telefone == phone_number)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user and create_if_not_exists:
        # Cria automaticamente um usuário básico
        user = Usuario(
            telefone=phone_number,
            nivel_acesso=NivelAcesso.basico
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

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
        payload = decode(
            credentials.credentials, settings.SECRET_KEY, algorithms=['HS256']
        )
        phone_number = payload.get('sub')

        if not phone_number:
            raise credentials_exception

    except DecodeError:
        raise credentials_exception

    except ExpiredSignatureError:
        raise credentials_exception

    user = await session.scalar(
        select(Usuario).where(Usuario.telefone == phone_number)
    )

    if not user:
        raise credentials_exception

    # Atualiza last_seen - Corrigido para usar datetime sem timezone para compatibilidade com o PostgreSQL
    user.last_seen = datetime.now().replace(tzinfo=None)
    await session.commit()

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
            detail="Número de telefone inválido",
        )

    # Obtém ou cria usuário automaticamente
    user = await get_auto_user_by_phone(phone_number, session)

    if not user:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Usuário não encontrado e não foi possível criar",
        )

    return user


# Dependência para verificar níveis de acesso
def check_permission(required_level: NivelAcesso):
    async def permission_checker(user: Usuario = Depends(get_current_user)):
        if user.nivel_acesso.value < required_level.value:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail=f"Acesso insuficiente. Nível necessário: {required_level.name}",
            )
        return user

    return permission_checker


# Dependências específicas por nível
require_intermediario = check_permission(NivelAcesso.intermediario)
require_super_usuario = check_permission(NivelAcesso.super_usuario)
