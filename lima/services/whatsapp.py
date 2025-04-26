"""
Módulo para integração com a API do WhatsApp Cloud.
Este módulo contém funções para envio e recebimento de mensagens via WhatsApp.
"""
import hashlib
import hmac
import logging
from typing import Any, Dict, List, Optional

import httpx

from ..settings import Settings

settings = Settings()
logger = logging.getLogger(__name__)

# Constantes
BASE_URL = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}"
PHONE_NUMBER_ID = settings.WHATSAPP_PHONE_NUMBER_ID
ACCESS_TOKEN = settings.WHATSAPP_ACCESS_TOKEN


class WhatsAppError(Exception):
    """Exceção para erros relacionados à API do WhatsApp"""
    pass


def check_whatsapp_credentials():
    """
    Verifica se as credenciais do WhatsApp estão disponíveis.
    
    Raises:
        WhatsAppError: Se as credenciais necessárias não estiverem configuradas.
    """
    if not settings.whatsapp_configured:
        missing = []
        if not PHONE_NUMBER_ID:
            missing.append("WHATSAPP_PHONE_NUMBER_ID")
        if not ACCESS_TOKEN:
            missing.append("WHATSAPP_ACCESS_TOKEN")

        error_msg = f"Credenciais do WhatsApp não configuradas: {', '.join(missing)}"
        logger.error(error_msg)
        raise WhatsAppError(error_msg)


async def verify_webhook_signature(request_body: bytes, signature_header: str) -> bool:
    """
    Verifica a assinatura do webhook enviada pelo WhatsApp para garantir 
    que a solicitação é autêntica.
    
    Args:
        request_body: Corpo da requisição em bytes
        signature_header: Cabeçalho X-Hub-Signature-256 enviado pelo WhatsApp
    
    Returns:
        bool: True se a assinatura for válida, False caso contrário
    """
    if not settings.WHATSAPP_APP_SECRET or not signature_header:
        return False

    try:
        # O cabeçalho tem o formato "sha256=hash"
        expected_signature = signature_header.split('sha256=')[1].strip()

        # Calculando o hash com o app secret
        key = settings.WHATSAPP_APP_SECRET.encode()
        signature = hmac.new(
            key,
            msg=request_body,
            digestmod=hashlib.sha256
        ).hexdigest()

        # Comparando as assinaturas
        return hmac.compare_digest(signature, expected_signature)
    except (IndexError, Exception) as e:
        logger.error(f"Erro na verificação da assinatura: {str(e)}")
        return False


async def send_text_message(to: str, message: str) -> Dict[str, Any]:
    """
    Envia uma mensagem de texto via WhatsApp Cloud API.
    
    Args:
        to: Número do destinatário no formato internacional (ex: "55119999999999")
        message: Texto da mensagem a ser enviada
    
    Returns:
        Dict: Resposta da API do WhatsApp
    
    Raises:
        WhatsAppError: Se as credenciais do WhatsApp não estiverem configuradas.
    """
    # Verifica se as credenciais estão disponíveis
    check_whatsapp_credentials()

    url = f"{BASE_URL}/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"body": message}
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem: {str(e)}")
        return {"error": str(e)}


async def send_template_message(
    to: str,
    template_name: str,
    language_code: str = "pt_BR",
    components: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Envia uma mensagem de template via WhatsApp Cloud API.
    
    Args:
        to: Número do destinatário no formato internacional
        template_name: Nome do template configurado no WhatsApp Business
        language_code: Código do idioma do template (padrão: pt_BR)
        components: Componentes para personalizar o template (opcional)
    
    Returns:
        Dict: Resposta da API do WhatsApp
        
    Raises:
        WhatsAppError: Se as credenciais do WhatsApp não estiverem configuradas.
    """
    # Verifica se as credenciais estão disponíveis
    check_whatsapp_credentials()

    url = f"{BASE_URL}/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code}
        }
    }

    # Adiciona componentes se fornecidos
    if components:
        payload["template"]["components"] = components

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Erro ao enviar template: {str(e)}")
        return {"error": str(e)}


async def parse_webhook_message(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analisa o payload do webhook e extrai informações relevantes da mensagem.
    
    Args:
        payload: Payload do webhook do WhatsApp
    
    Returns:
        Dict: Informações extraídas da mensagem
    """
    try:
        result = {
            "phone_number": None,
            "message_type": None,
            "message_content": None,
            "timestamp": None,
            "message_id": None,
            "raw": payload
        }

        # Navegando na estrutura do webhook para encontrar os dados da mensagem
        entry = payload.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})

        messages = value.get("messages", [])
        if not messages:
            return result

        message = messages[0]
        result["phone_number"] = message.get("from")
        result["message_id"] = message.get("id")
        result["timestamp"] = message.get("timestamp")

        # Identifica o tipo de mensagem
        message_type = message.get("type")
        result["message_type"] = message_type

        # Extrai o conteúdo com base no tipo
        if message_type == "text":
            result["message_content"] = message.get("text", {}).get("body", "")
        elif message_type == "interactive":
            interactive = message.get("interactive", {})
            if "button_reply" in interactive:
                result["message_content"] = interactive["button_reply"].get("id")
            elif "list_reply" in interactive:
                result["message_content"] = interactive["list_reply"].get("id")
        elif message_type == "location":
            loc = message.get("location", {})
            result["message_content"] = {
                "latitude": loc.get("latitude"),
                "longitude": loc.get("longitude"),
                "address": loc.get("address", ""),
                "name": loc.get("name", "")
            }

        return result
    except (IndexError, KeyError) as e:
        logger.error(f"Erro ao analisar mensagem do webhook: {str(e)}")
        return {
            "error": str(e),
            "raw": payload
        }


async def send_interactive_message(
    to: str,
    header_text: str,
    body_text: str,
    footer_text: str = "",
    buttons: List[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Envia uma mensagem interativa com botões via WhatsApp Cloud API.
    
    Args:
        to: Número do destinatário no formato internacional
        header_text: Texto do cabeçalho da mensagem
        body_text: Corpo da mensagem
        footer_text: Texto do rodapé (opcional)
        buttons: Lista de botões no formato [{"id": "btn_id", "title": "Texto do botão"}]
    
    Returns:
        Dict: Resposta da API do WhatsApp
        
    Raises:
        WhatsAppError: Se as credenciais do WhatsApp não estiverem configuradas.
    """
    # Verifica se as credenciais estão disponíveis
    check_whatsapp_credentials()

    url = f"{BASE_URL}/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    # Prepara os botões no formato esperado pela API
    formatted_buttons = []
    if buttons:
        for btn in buttons[:3]:  # Limite de 3 botões
            formatted_buttons.append({
                "type": "reply",
                "reply": {
                    "id": btn["id"],
                    "title": btn["title"][:20]  # Limite de 20 caracteres por botão
                }
            })

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "header": {
                "type": "text",
                "text": header_text[:60]  # Limite de 60 caracteres
            },
            "body": {
                "text": body_text[:1024]  # Limite de 1024 caracteres
            },
            "action": {
                "buttons": formatted_buttons
            }
        }
    }

    # Adiciona o footer se fornecido
    if footer_text:
        payload["interactive"]["footer"] = {
            "text": footer_text[:60]  # Limite de 60 caracteres
        }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem interativa: {str(e)}")
        return {"error": str(e)}
