from typing import Annotated, Dict, Optional, Union

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..schemas import Token, WhatsAppAuthRequest
from ..security import (
    create_whatsapp_token,
    get_auto_user_by_phone,
    validate_phone_number,
)
from ..services.telegram import (
    EstadoRegistro,
    cancelar_registro,
    extract_message_data,
    finalizar_registro,
    obter_estado_registro,
    process_webhook_update,
)
from ..services.telegram import (
    enviar_menu_inicial as telegram_enviar_menu_inicial,
)
from ..services.telegram import (
    processar_interacao as telegram_processar_interacao,
)
from ..services.telegram import (
    processar_registro_usuario as telegram_processar_registro_usuario,
)
from ..services.telegram import (
    send_text_message as telegram_send_text_message,
)
from ..services.whatsapp import parse_webhook_message, verify_webhook_signature
from ..services.whatsapp_commands import (
    enviar_menu_inicial,
    processar_interacao,
)
from ..settings import Settings

router = APIRouter(prefix='/auth', tags=['Auth'])
settings = Settings()

# Definições de dependências usando Annotated
AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]
OAuth2FormDep = Annotated[OAuth2PasswordRequestForm, Depends()]


# Corrigindo a definição dos parâmetros Query com funções auxiliares
def hub_mode_query(hub_mode: Optional[str] = Query(None, alias='hub.mode')):
    return hub_mode


def hub_challenge_query(
    hub_challenge: Optional[str] = Query(None, alias='hub.challenge'),
):
    return hub_challenge


def hub_verify_token_query(
    hub_verify_token: Optional[str] = Query(None, alias='hub.verify_token'),
):
    return hub_verify_token


def x_hub_signature_header(x_hub_signature_256: Optional[str] = Header(None)):
    return x_hub_signature_256


# Função auxiliar para verificar token secreto do Telegram
def telegram_secret_token(
    x_telegram_bot_api_secret_token: Optional[str] = Header(None),
):
    return x_telegram_bot_api_secret_token


HubModeDep = Annotated[Optional[str], Depends(hub_mode_query)]
HubChallengeDep = Annotated[Optional[str], Depends(hub_challenge_query)]
HubVerifyTokenDep = Annotated[Optional[str], Depends(hub_verify_token_query)]
HubSignatureDep = Annotated[Optional[str], Depends(x_hub_signature_header)]
TelegramSecretTokenDep = Annotated[
    Optional[str], Depends(telegram_secret_token)
]


# Função auxiliar para verificar webhooks do WhatsApp
def verify_whatsapp_token(
    hub_mode: Optional[str],
    hub_challenge: Optional[str],
    hub_verify_token: Optional[str],
) -> Union[int, str]:
    """
    Função auxiliar para verificar tokens do webhook do WhatsApp.

    Args:
        hub_mode: Modo de verificação (deve ser 'subscribe')
        hub_challenge: Desafio enviado pelo WhatsApp
        hub_verify_token: Token de verificação

    Returns:
        O challenge ou uma mensagem de verificação

    Raises:
        HTTPException: Se a verificação falhar
    """
    # Usa o token de verificação das configurações
    VERIFY_TOKEN = settings.WHATSAPP_VERIFY_TOKEN

    if hub_mode and hub_verify_token:
        if hub_mode == 'subscribe' and hub_verify_token == VERIFY_TOKEN:
            return int(hub_challenge) if hub_challenge else 'WEBHOOK_VERIFIED'

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail='Verificação falhou',
    )


# Função auxiliar para processar respostas de webhooks
def prepare_webhook_response(
    user_id: int, message_type: str, result: Dict, **extra_fields
) -> Dict:
    """
    Prepara a resposta padrão para webhooks.

    Args:
        user_id: ID do usuário
        message_type: Tipo da mensagem
        result: Resultado do processamento
        extra_fields: Campos adicionais para incluir na resposta

    Returns:
        Dicionário com a resposta formatada
    """
    response = {
        'status': 'processed',
        'user_id': user_id,
        'message_type': message_type,
        'processing_result': result,
    }

    # Adiciona campos extras se fornecidos
    if extra_fields:
        response.update(extra_fields)

    return response


@router.post('/whatsapp/token', response_model=Token)
async def create_whatsapp_access_token(
    auth_request: WhatsAppAuthRequest,
    session: AsyncSessionDep,
):
    """
    Gera um token de acesso para um número de WhatsApp.

    Em produção, esta rota deveria verificar um código enviado ao número
    do usuário para garantir a posse do número.
    """
    if not validate_phone_number(auth_request.phone_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Número de telefone inválido',
        )

    # Em produção: verifique o código recebido via WhatsApp
    # if not verify_code(auth_request.phone_number,
    #  auth_request.verification_code):
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Código de verificação inválido",
    #     )

    # Registra ou atualiza o usuário (resultado ignorado intencionalmente)
    _ = await get_auto_user_by_phone(auth_request.phone_number, session)

    # Gera o token
    access_token = create_whatsapp_token(auth_request.phone_number)

    return Token(access_token=access_token, token_type='bearer')


# Endpoint unificado para verificação do webhook do WhatsApp
@router.get('/whatsapp/webhook')
async def verify_whatsapp_webhook(
    hub_mode: HubModeDep,
    hub_challenge: HubChallengeDep,
    hub_verify_token: HubVerifyTokenDep,
):
    """
    Endpoint para verificação de webhook pelo WhatsApp Cloud API.

    Este endpoint é usado pelo WhatsApp durante a configuração do webhook
    para verificar a autenticidade do servidor.

    - **hub_mode**: Modo de verificação (deve ser 'subscribe')
    - **hub_challenge**: Desafio enviado pelo WhatsApp
    - **hub_verify_token**: Token de verificação (deve corresponder à config)
    """
    return verify_whatsapp_token(hub_mode, hub_challenge, hub_verify_token)


# Rota adicional para verificação de webhook (para compatibilidade)
@router.get('/whatsapp/verify')
async def verify_whatsapp_webhook_compat(
    hub_mode: HubModeDep,
    hub_challenge: HubChallengeDep,
    hub_verify_token: HubVerifyTokenDep,
):
    """
    Endpoint alternativo para verificação de webhook pelo WhatsApp.

    Este endpoint oferece a mesma funcionalidade que /whatsapp/webhook,
    mas com um caminho diferente para manter compatibilidade com integrações
    existentes ou testes.

    - **hub_mode**: Modo de verificação (deve ser 'subscribe')
    - **hub_challenge**: Desafio enviado pelo WhatsApp
    - **hub_verify_token**: Token de verificação (deve corresponder à config)
    """
    return verify_whatsapp_token(hub_mode, hub_challenge, hub_verify_token)


@router.post('/whatsapp/webhook')
async def whatsapp_webhook(
    request: Request,
    session: AsyncSessionDep,
    x_hub_signature_256: HubSignatureDep,
):
    """
    Webhook para receber mensagens do WhatsApp Cloud API

    Este endpoint processa as mensagens recebidas do WhatsApp e
    realiza a autenticação automática do usuário pelo número.
    """
    # Obter o corpo da requisição em bytes para verificar a assinatura
    body_bytes = await request.body()

    # Verificar a assinatura do webhook (em produção)
    if settings.WHATSAPP_APP_SECRET:
        is_valid = await verify_webhook_signature(
            body_bytes, x_hub_signature_256
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Assinatura do webhook inválida',
            )

    # Converter o corpo para JSON
    payload = await request.json()

    # Verifica se é uma mensagem de status ou uma mensagem real
    if 'entry' not in payload or not payload.get('entry'):
        return {'status': 'ignored', 'reason': 'No entry data'}

    # Usa a função de parsing para extrair informações da mensagem
    parsed_message = await parse_webhook_message(payload)

    # Ignora se não tiver número de telefone ou não for uma mensagem
    if not parsed_message.get('phone_number'):
        return {'status': 'ignored', 'reason': 'No phone number found'}

    phone_number = parsed_message['phone_number']
    message_type = parsed_message['message_type']
    message_content = parsed_message['message_content']

    # Cria/atualiza o usuário automaticamente
    user = await get_auto_user_by_phone(phone_number, session)

    # Processa a interação usando o módulo de comandos
    result = await processar_interacao(
        session=session,
        phone_number=phone_number,
        user_id=user.id,
        message_type=message_type,
        message_content=message_content,
    )

    # Se for a primeira mensagem do usuário, envia o menu de boas-vindas
    if getattr(user, 'is_new', False):
        await enviar_menu_inicial(phone_number)

    return prepare_webhook_response(
        user_id=user.id, message_type=message_type, result=result
    )


@router.post('/telegram/webhook')
async def telegram_webhook(
    request: Request,
    session: AsyncSessionDep,
    secret_token: TelegramSecretTokenDep = None,
):
    """
    Webhook para receber atualizações do Telegram Bot API.

    Este endpoint processa as mensagens recebidas do Telegram e
    realiza a autenticação automática do usuário pelo ID do chat.
    """
    # Verificar o token secreto do webhook (se configurado)
    if (
        settings.TELEGRAM_SECRET_TOKEN
        and settings.TELEGRAM_SECRET_TOKEN != secret_token
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Token secreto do webhook inválido',
        )

    # Converter o corpo para JSON
    payload = await request.json()

    # Processar a atualização do Telegram
    update = await process_webhook_update(payload)

    # Extrair informações relevantes
    message_data = await extract_message_data(update)

    # Se não tiver ID do chat, ignora a mensagem
    if not message_data.get('chat_id'):
        return {'status': 'ignored', 'reason': 'No chat ID found'}

    chat_id = message_data['chat_id']
    user_id = message_data['user_id']
    message_type = message_data['message_type']
    message_content = message_data['message_content']
    is_callback = message_data['is_callback']

    # Cria/atualiza o usuário automaticamente
    # Nota: Na produção, talvez você queira mapear IDs do Telegram para números de telefone  # noqa: E501
    telegram_id_as_phone = f'+telegram{user_id}'
    user = await get_auto_user_by_phone(telegram_id_as_phone, session)

    # Verifica se é um novo usuário ou uma solicitação de registro
    is_new_user = getattr(user, 'is_new', False)
    estado_registro = obter_estado_registro(chat_id)
    is_comando_registro = (
        message_type == 'text'
        and isinstance(message_content, str)
        and message_content.startswith('/registro')
    )

    # Lidar com botões de confirmação/cancelamento do registro
    if is_callback and message_type == 'interactive':
        if message_content == 'confirmar_registro':
            # Processar confirmação de registro via botão
            if estado_registro == EstadoRegistro.CONFIRMACAO:
                sucesso = await finalizar_registro(chat_id, user.id, session)
                if sucesso:
                    await telegram_send_text_message(
                        chat_id=chat_id,
                        message=(
                            '✅ *Registro concluído com sucesso\\!*\n\n'
                            'Seus dados foram salvos e agora você pode usar  '
                            'todos os recursos do sistema\\.\n\n'
                        'Use /ajuda para ver todos os comandos disponíveis\\.'
                        ),
                    )
                    result = {'status': 'completed', 'process': 'registro'}
                else:
                    await telegram_send_text_message(
                        chat_id=chat_id,
                        message=(
                            '❌ Ocorreu um erro ao salvar seus dados\\. '
                'Por favor, tente novamente mais tarde ou contate o suporte\\.'
                        ),
                    )
                    cancelar_registro(chat_id)
                    result = {
                        'status': 'error',
                        'process': 'registro',
                        'step': 'salvar',
                    }

                return prepare_webhook_response(
                    user_id=user.id,
                    message_type=message_type,
                    result=result,
                    chat_id=chat_id,
                )

        elif message_content == 'cancelar_registro':
            # Processar cancelamento de registro via botão
            cancelar_registro(chat_id)
            await telegram_send_text_message(
                chat_id=chat_id,
                message=(
                    '❌ Registro cancelado\\. '
                'Você pode iniciar novamente a qualquer momento com /registro'
                ),
            )
            result = {'status': 'cancelled', 'process': 'registro'}
            return prepare_webhook_response(
                user_id=user.id,
                message_type=message_type,
                result=result,
                chat_id=chat_id,
            )

    # Se estiver em estado de registro ou for o comando de registro, processa com prioridade  # noqa: E501
    if estado_registro is not None or is_comando_registro:
        result = await telegram_processar_registro_usuario(
            session=session,
            chat_id=chat_id,
            user_id=user.id,
            message_content=message_content,
        )

        return prepare_webhook_response(
            user_id=user.id,
            message_type=message_type,
            result=result,
            chat_id=chat_id,
        )

    # Para usuários novos, inicia o fluxo de registro
    if is_new_user:
        # Envia mensagem de boas-vindas primeiro
        await telegram_enviar_menu_inicial(chat_id)

        # Inicia o processo de registro
        await telegram_send_text_message(
            chat_id=chat_id,
            message=(
            'Para uma melhor experiência, vamos completar seu cadastro\\.\n\n'
                'Para começar, envie o comando /registro\\.'
            ),
        )
        return prepare_webhook_response(
            user_id=user.id,
            message_type=message_type,
            result={'status': 'new_user_welcome'},
            chat_id=chat_id,
        )

    # Processa a interação usando o módulo de comandos do Telegram
    result = await telegram_processar_interacao(
        session=session,
        chat_id=chat_id,
        user_id=user.id,
        message_data={
            'message_type': message_type,
            'message_content': message_content,
            'is_callback': is_callback,
        },
    )

    # Se for solicitação /start, envia o menu de boas-vindas
    if message_type == 'text' and message_content == '/start':
        await telegram_enviar_menu_inicial(chat_id)

    # Responder ao Telegram com sucesso
    return prepare_webhook_response(
        user_id=user.id,
        message_type=message_type,
        result=result,
        chat_id=chat_id,
    )


@router.post('/token', response_model=Token)
async def login_for_access_token(
    form_data: OAuth2FormDep,
    session: AsyncSessionDep,
):
    """
    Autentica um usuário e gera um token de acesso JWT

    * Não requer autenticação (endpoint público)
    * Use o número de telefone completo como username (ex: +5511999999999)
    * Por padrão, os tokens são válidos por 30 dias

    **Exemplo de uso:**

    ```
    curl -X POST "http://localhost:8000/auth/token" -d
      "username=%2B5511999999999&password=sua_senha"
    ```

    O token recebido deve ser usado nas requisições subsequentes
      através do headerAuthorization: Bearer {token}
    """
    # Implementar a lógica de autenticação
    # Exemplo simples: verificar se o usuário existe pelo username (telefone)
    # e validar credenciais
    phone_number = form_data.username
    # password = form_data.password

    # Criar ou atualizar o usuário automaticamente
    # Uso intencional para garantir que o usuário existe no sistema
    _user = await get_auto_user_by_phone(phone_number, session)

    # Gerar o token
    access_token = create_whatsapp_token(phone_number)

    return Token(access_token=access_token, token_type='bearer')
