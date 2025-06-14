import logging

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Request,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from telegram import Update as PTBUpdate  # Movido para o topo

from lima.bot.main import obter_aplicacao  # Funções do Bot
from lima.database import get_async_session  # Sessão do banco de dados
from lima.schemas import (
    TelegramUserRegistrationRequest,
    Token,
)
from lima.security import (
    create_access_token,
    get_or_create_user_by_telegram_id,  # Corrigido
)

from ..settings import settings  # Configurações da aplicação

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/login', response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    # Esta rota é para login de usuário padrão com email/senha.
    # A função authenticate_user original precisaria ser adaptada ou
    # uma nova lógica de verificação de senha implementada aqui.
    # A função get_or_create_user_by_telegram_id espera 'telegram_user_id',
    # e não 'email' como form_data.username provê.

    # Comentando a lógica que causa erro por enquanto e retornando 501.
    # user = await get_or_create_user_by_telegram_id(
    #     session=session,
    #     telegram_user_id=form_data.username, # Isso não vai funcionar
    #     name=None,
    #     expected_phone=None # Precisa de um telefone esperado
    # )
    # if not user:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail=\'Email ou senha incorretos\',
    #         headers={\'WWW-Authenticate\': \'Bearer\'},
    #     )
    # access_token = create_access_token(data={"user_id": user.id})
    # return Token(access_token=access_token, token_type=\'bearer\')

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail='Login padrão não implementado para este fluxo.',
    )


@router.post('/telegram/register', response_model=Token)
async def register_telegram_user_via_api(
    payload: TelegramUserRegistrationRequest,
    # Alterado para receber o payload no corpo da requisição
):
    """
    Registra ou obtém um usuário com base no ID do Telegram.
    Este endpoint é chamado internamente pelo bot para criar/logar usuários.
    """
    if not payload.telegram_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='telegram_user_id é obrigatório.',
        )

    async with get_async_session() as session:
        user_db = await get_or_create_user_by_telegram_id(  # Corrigido
            session=session,
            telegram_user_id=payload.telegram_user_id,
            expected_phone=payload.phone_number,  # Adicionado expected_phone
            name=payload.nome,
        )

    if not user_db:
        detail_msg = (
            f'Não foi possível criar ou encontrar o usuário com ID Telegram '
            f'{payload.telegram_user_id}.'
        )
        logger.error(detail_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail_msg,
        )

    logger.info(
        f'Usuário Telegram registrado/logado via API: ID {user_db.id}, '
        f'TelegramID: {payload.telegram_user_id}, Nome: {
            payload.nome or user_db.nome
        }'
        # Corrigido para payload.nome
    )

    access_token = create_access_token(
        data={
            'user_id': user_db.id,
            'telegram_user_id': user_db.telegram_user_id,
        }
    )
    return Token(access_token=access_token, token_type='bearer')


# Webhook para o Telegram (se o PTB não estiver auto-hospedando o webhook)
@router.post('/telegram/webhook')  # Removida a barra final
async def telegram_webhook(
    request: Request,  # Usar Request para obter o corpo raw
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    """
    Endpoint de webhook para o Telegram.

    Este endpoint é usado se você configurar manualmente o webhook do Telegram
    para apontar para sua aplicação FastAPI, em vez de usar o servidor web
    embutido do `python-telegram-bot` (`application.run_webhook()`).

    A validação do `X-Telegram-Bot-Api-Secret-Token` é crucial por segurança.
    """
    logger.info('Webhook do Telegram recebido.')

    # 1. Validar o token secreto (MUITO IMPORTANTE)
    if settings.TELEGRAM_SECRET_TOKEN:
        if not x_telegram_bot_api_secret_token:
            logger.warning('Token secreto do webhook do Telegram ausente.')
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Token secreto ausente.',
            )
        if x_telegram_bot_api_secret_token != settings.TELEGRAM_SECRET_TOKEN:
            logger.warning('Token secreto do webhook do Telegram inválido.')
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Token secreto inválido.',
            )
    else:
        logger.warning(
            'TELEGRAM_SECRET_TOKEN não configurado. Webhook vulnerável.'
        )
        # Considere recusar a requisição se o token não
        #  estiver configurado por segurança.
        # raise HTTPException(status_code=status.
        # HTTP_500_INTERNAL_SERVER_ERROR,
        #  detail="Configuração de segurança incompleta.")

    # 2. Obter o corpo da requisição como JSON
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(
            f'Erro ao fazer parse do JSON do webhook do Telegram: {e}'
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Payload JSON inválido.',
        )

    logger.debug(f'Payload do webhook: {payload}')

    # 3. Processar a atualização usando a aplicação PTB
    # É crucial que a aplicação PTB esteja inicializada e acessível.
    try:
        application = (
            obter_aplicacao()
        )  # Função que retorna a instância da app PTB

        update = PTBUpdate.de_json(payload, application.bot)
        await application.process_update(update)
        logger.info('Atualização do Telegram processada pela aplicação.')
    except ImportError:
        logger.exception(
            'Falha ao importar telegram.Update. Verifique as dependências.'
        )
        raise HTTPException(
            status_code=500,
            detail='Erro interno ao processar atualização (ImportError).',
        )
    except Exception as e:
        logger.exception(
            'Erro ao processar atualização do Telegram via webhook.'
        )
        # Não relance a exceção diretamente para o Telegram,
        #  pois pode expor detalhes.
        # O Telegram tentará reenviar a atualização se receber um erro não-2xx.
        # Se o processamento falhar consistentemente, é melhor retornar 200 OK
        # para evitar um loop de reenvio, e logar o erro agressivamente.
        # No entanto, para depuração inicial, um 500 pode ser útil.
        raise HTTPException(
            status_code=500,
            detail=f'Erro interno ao processar atualização: {
                type(e).__name__
            }',
        )

    status_message = (
        'atualização do telegram recebida e enfileirada para processamento'
    )
    return {'status': status_message}


# TODO: Verificar a necessidade e
#  funcionalidade da rota de webhook do WhatsApp.
# @router.post('/whatsapp/webhook')
# async def whatsapp_webhook(request: Request):
#     # payload = await request.json()
#     # logger.info(f"Whatsapp webhook: {payload}")
#     # Aqui iria a lógica para processar o webhook do WhatsApp
#     return {"status": "recebido"}

# TODO: Adicionar rota para verificar o status do bot ou informações de saúde,
#  se necessário.
