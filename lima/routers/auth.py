from typing import Annotated, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Header, Request, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..security import (
    create_whatsapp_token, 
    validate_phone_number,
    get_auto_user_by_phone,
)
from ..settings import Settings
from ..services.whatsapp import verify_webhook_signature, parse_webhook_message
from ..services.whatsapp_commands import processar_interacao, enviar_menu_inicial

router = APIRouter(prefix="/auth", tags=["Auth"])
settings = Settings()

AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


class Token(BaseModel):
    access_token: str
    token_type: str


class WhatsAppAuthRequest(BaseModel):
    phone_number: str
    verification_code: Optional[str] = None


class WhatsAppWebhookPayload(BaseModel):
    phone_number: str
    message: str
    timestamp: Optional[str] = None


@router.post("/whatsapp/token", response_model=Token)
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
            detail="Número de telefone inválido",
        )
    
    # Em produção: verifique o código recebido via WhatsApp
    # if not verify_code(auth_request.phone_number, auth_request.verification_code):
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Código de verificação inválido",
    #     )
    
    # Registra ou atualiza o usuário
    await get_auto_user_by_phone(auth_request.phone_number, session)
    
    # Gera o token
    access_token = create_whatsapp_token(auth_request.phone_number)
    
    return Token(access_token=access_token, token_type="bearer")


@router.get("/whatsapp/verify")
async def verify_whatsapp_webhook(
    hub_mode: str = None,
    hub_challenge: str = None,
    hub_verify_token: str = None,
):
    """
    Endpoint para verificação de webhook pelo WhatsApp Cloud API.
    
    - **hub_mode**: Modo de verificação (deve ser 'subscribe')
    - **hub_challenge**: Desafio enviado pelo WhatsApp
    - **hub_verify_token**: Token de verificação (deve corresponder à configuração)
    """
    # Usa o token de verificação das configurações
    VERIFY_TOKEN = settings.WHATSAPP_VERIFY_TOKEN
    
    if hub_mode and hub_verify_token:
        if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
            return int(hub_challenge) if hub_challenge else "WEBHOOK_VERIFIED"
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Verificação falhou",
    )


@router.get("/whatsapp/webhook")
async def verify_whatsapp_webhook_alt(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
):
    """
    Endpoint alternativo para verificação de webhook pelo WhatsApp Cloud API.
    Permite usar a mesma rota tanto para verificação quanto para recebimento de mensagens.
    
    - **hub_mode**: Modo de verificação (deve ser 'subscribe')
    - **hub_challenge**: Desafio enviado pelo WhatsApp
    - **hub_verify_token**: Token de verificação (deve corresponder à configuração)
    """
    # Usa o token de verificação das configurações
    VERIFY_TOKEN = settings.WHATSAPP_VERIFY_TOKEN
    
    if hub_mode and hub_verify_token:
        if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
            return int(hub_challenge) if hub_challenge else "WEBHOOK_VERIFIED"
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Verificação falhou",
    )


@router.post("/whatsapp/webhook")
async def whatsapp_webhook(
    request: Request,
    session: AsyncSessionDep,
    x_hub_signature_256: Optional[str] = Header(None),
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
        is_valid = await verify_webhook_signature(body_bytes, x_hub_signature_256)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Assinatura do webhook inválida",
            )
    
    # Converter o corpo para JSON
    payload = await request.json()
    
    # Verifica se é uma mensagem de status ou uma mensagem real
    if "entry" not in payload or not payload.get("entry"):
        return {"status": "ignored", "reason": "No entry data"}
        
    # Usa a função de parsing para extrair informações da mensagem
    parsed_message = await parse_webhook_message(payload)
    
    # Ignora se não tiver número de telefone ou não for uma mensagem
    if not parsed_message.get("phone_number"):
        return {"status": "ignored", "reason": "No phone number found"}
    
    phone_number = parsed_message["phone_number"]
    message_type = parsed_message["message_type"]
    message_content = parsed_message["message_content"]
    
    # Cria/atualiza o usuário automaticamente
    user = await get_auto_user_by_phone(phone_number, session)
    
    # Processa a interação usando o módulo de comandos
    result = await processar_interacao(
        session=session,
        phone_number=phone_number,
        user_id=user.id,
        message_type=message_type,
        message_content=message_content
    )
    
    # Se for a primeira mensagem do usuário, envia o menu de boas-vindas
    if getattr(user, 'is_new', False):
        await enviar_menu_inicial(phone_number)
    
    return {
        "status": "processed", 
        "user_id": user.id,
        "message_type": message_type,
        "processing_result": result
    }
