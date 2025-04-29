import re
from datetime import datetime, timedelta, timezone
from http import HTTPStatus

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
    now = datetime.utcnow()
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


def verify_whatsapp_origin(phone_number: str, whatsapp_id: str = None) -> bool:
    """
    Verifica se a solicitação veio realmente do WhatsApp.
    Em produção, isso verificaria assinaturas, IDs da plataforma, etc.
    """
    # Implementação robusta para ambiente de produção
    if not phone_number:
        return False

    # Validação básica do formato do telefone
    if not validate_phone_number(phone_number):
        return False

    # Verificações adicionais para produção:
    # 1. Verificar se o ID do WhatsApp é válido e está na lista de IDs
    # permitidos
    if whatsapp_id and whatsapp_id not in settings.ALLOWED_WHATSAPP_IDS:
        # Em produção, adicionar logging para tentativas suspeitas
        return False

    # 2. Em uma integração real com o WhatsApp, você deve verificar:
    #    - A assinatura HMAC do cabeçalho X-Hub-Signature para confirmar
    #      a origem
    #    - Validar tokens de verificação webhook
    #    - Verificar se a mensagem está dentro de um período de tempo válido

    # Nota: Esta é uma implementação de exemplo que deve ser expandida
    # com a lógica real de verificação para o ambiente de produção

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
            if x_whatsapp_phone and not verify_whatsapp_origin(
                x_whatsapp_phone
            ):
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

    if not user and create_if_not_exists:
        try:
            # Cria automaticamente um usuário básico
            user = Usuario(
                telefone=phone_number, nivel_acesso=NivelAcesso.basico
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
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
        # Token expirado, verificar se deve renovar automaticamente
        try:
            # Decodificar sem verificar a expiração para obter o número
            #  do telefone
            payload = decode(
                credentials.credentials,
                settings.SECRET_KEY,
                algorithms=['HS256'],
                options={'verify_exp': False},
            )
            phone_number = payload.get('sub')

            if not phone_number:
                raise credentials_exception

            # Aqui poderia adicionar uma verificação se o usuário tem permissão
            # para renovação automática
            # Por exemplo, verificar o último login ou alguma regra específica

            # Para fins de log/auditoria, seria bom registrar essa renovação
            # automática
            # Em produção, adicione um log aqui

            # Retorna exceção de token expirado com informação adicional
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail='Token expirado. Solicite um novo token de acesso.',
                headers={
                    'WWW-Authenticate': 'Bearer',
                    'X-Token-Expired': 'true',
                },
            )

        except Exception:
            # Se houver qualquer erro ao tentar renovar, retorna a exceção
            #  padrão
            raise credentials_exception

    user = await session.scalar(
        select(Usuario).where(Usuario.telefone == phone_number)
    )

    if not user:
        raise credentials_exception

    try:
        # Atualiza last_seen - Usa datetime com timezone UTC
        user.last_seen = datetime.now(timezone.utc)
        await session.commit()
    except Exception:  # Removida a variável 'e' não utilizada
        await session.rollback()
        # Não bloqueia o acesso se falhar a atualização do last_seen
        # apenas registra o erro
        # Em produção, considere adicionar um log aqui
        pass

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
    async def permission_checker(user: Usuario = Depends(get_current_user)):
        if user.nivel_acesso.value < required_level.value:
            detail_message = (
                f'Acesso insuficiente. Nível necessário: {required_level.name}'
            )
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail=detail_message,
            )
        return user

    return permission_checker


# Dependências específicas por nível
require_intermediario = check_permission(NivelAcesso.intermediario)
require_super_usuario = check_permission(NivelAcesso.super_usuario)
