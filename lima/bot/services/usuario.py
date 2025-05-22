"""
Serviço para gerenciamento de usuários.
"""

import logging
from typing import Any, Dict, Optional

from ..api_client import (
    fazer_requisicao_get,
    fazer_requisicao_post,
    fazer_requisicao_put,
)
from .auth import token_manager  # Adicionado

logger = logging.getLogger(__name__)


async def obter_usuario_por_telefone(
    telefone: str,
    user_id: Optional[int] = None,  # Adicionado para consistência
) -> Optional[Dict[str, Any]]:
    """
    Busca um usuário pelo número de telefone.

    Args:
        telefone: Número de telefone do usuário.
        user_id: ID do usuário do Telegram para autenticação (opcional).

    Returns:
        Dados do usuário ou None se não encontrado.
    """
    params = {'telefone': telefone}
    # Passa user_id; se None, o api_client tratará
    # (não enviando o header de auth)
    # A resposta da API /usuarios/?telefone=... pode ser um objeto único ou
    # uma lista.
    # Se for um objeto único e o usuário não existir, a API pode retornar 404,
    # que fazer_requisicao_get pode transformar em None.
    # Se for uma lista, pode ser uma lista vazia.
    response_data = await fazer_requisicao_get(
        'usuarios/', params, user_id=user_id
    )

    if isinstance(response_data, list):
        if response_data:  # Se a lista não estiver vazia
            return response_data[0]  # Retorna o primeiro usuário da lista
    elif isinstance(response_data, dict):  # Se for um único objeto/dict
        # Verifica se o dicionário não está vazio (pode ser um usuário válido)
        if response_data:  # Garante que o dicionário não seja vazio
            return response_data

    # Se response_data for None, ou lista vazia, ou dict vazio, ou outro tipo
    return None


async def criar_usuario(
    telegram_user_id: int,
    nome: Optional[str] = None,
    telefone_para_api: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Cria um novo usuário através do endpoint de registro do Telegram.
    Retorna a resposta completa da API, que deve incluir o access_token.
    """
    data = {
        "telegram_user_id": telegram_user_id,
    }

    if nome:
        data["nome"] = nome

    if telefone_para_api:
        data["phone_number"] = telefone_para_api

    log_msg = (
        f"Registrando novo usuário via API: "
        f"telegram_user_id={telegram_user_id}, nome={nome}, "
        f"telefone_para_api={telefone_para_api}"
    )
    logger.info(log_msg)
    # Retorna a resposta completa da API, que esperamos que contenha o token
    response_data = await fazer_requisicao_post("auth/telegram/register", data)
    return response_data


async def atualizar_ultimo_acesso(
    id_alvo_usuario: int, user_id_auth: int
) -> Dict[str, Any]:
    """
    Atualiza o timestamp de último acesso do usuário.

    Args:
        id_alvo_usuario: ID do usuário cujo último acesso será atualizado.
        user_id_auth: ID do usuário do Telegram realizando a ação
                      (para autenticação).

    Returns:
        Usuário atualizado ou dicionário de erro.
    """
    logger.info(
        f"Tentando atualizar último acesso para usuário ID: {id_alvo_usuario} "
        f"(autenticado como user_id: {user_id_auth})"
    )

    try:
        usuario_data = await fazer_requisicao_get(
            f'usuarios/{id_alvo_usuario}', user_id=user_id_auth
        )

        if not usuario_data:
            warning_msg = (
                f"Usuário ID {id_alvo_usuario} não encontrado (GET) ao tentar "
                f"atualizar último acesso. Autenticado como {user_id_auth}."
            )
            logger.warning(warning_msg)
            return {
                "error": f"Usuário {id_alvo_usuario} não encontrado via GET",
                "status_code": 404
            }

        return await fazer_requisicao_put(
            f'usuarios/{id_alvo_usuario}',
            data=usuario_data,
            user_id=user_id_auth
        )

    except Exception as e:
        error_msg = (
            "Erro ao atualizar último acesso para "
            f"usuário ID {id_alvo_usuario} "
            f"(autenticado como {user_id_auth}): {str(e)}"
        )
        logger.error(error_msg)
        return {
            "error": "Falha ao atualizar último acesso",
            "detail": str(e)
        }


async def obter_ou_criar_usuario(
    telegram_user_id: int,
    nome: Optional[str],
    telefone_id_interno: str,  # Ex: "telegram_12345"
    user_id_telegram_para_get: int,  # Para autenticar o GET
) -> Dict[str, Any]:
    """
    Garante que um usuário exista/seja criado/atualizado via API.

    Primeiro, chama /auth/telegram/register para criar/atualizar o usuário
    (incluindo nome, telefone, last_seen) e obter o token.
    Depois, busca e retorna os dados completos do usuário.
    """
    try:
        logger.info(
            f"Processando obter_ou_criar_usuario para telegram_id: "
            f"{telegram_user_id}, nome: {nome}, "
            f"telefone_id_interno: {telefone_id_interno}"
        )
        # Etapa 1: Chamar criar_usuario (endpoint /auth/telegram/register).
        # Isso lida com a criação ou atualização (nome, phone_number,
        # last_seen) e retorna os dados da API, incluindo o token.
        dados_registro = await criar_usuario(
            telegram_user_id=telegram_user_id,
            nome=nome,
            telefone_para_api=telefone_id_interno,
        )

        if dados_registro and isinstance(dados_registro, dict):
            access_token = dados_registro.get("access_token")
            if access_token:
                token_manager.set_token(access_token)
                logger.info("Token de acesso armazenado no TokenManager.")
            else:
                logger.warning(
                    "Resposta de criar_usuario não continha 'access_token'."
                )
            # A resposta de /auth/telegram/register é esperada como:
            # {"access_token": "...", "token_type": "bearer",
            #  "user": {...dados do usuario...}}
            # Não precisamos extrair user_info_from_register aqui, pois
            # obter_usuario_por_telefone buscará os dados mais recentes
            # de qualquer maneira.

        else:
            logger.error(
                f"Falha ao registrar/logar usuário {telegram_user_id} "
                f"via criar_usuario. Resposta: {dados_registro}"
            )
            return {
                "error": "Falha na etapa de registro/login do usuário.",
                "detail": (
                    "Resposta inesperada de criar_usuario: "
                    f"{dados_registro}"
                ),
                "status_code": 500,
            }

        # Etapa 2: Buscar os dados completos do usuário.
        # Agora o token_manager deve ter o token, então
        # fazer_requisicao_get não deve precisar chamar
        # obter_token_api() novamente.
        logger.info(
            f"Buscando usuário completo com telefone: {telefone_id_interno} "
            f"após registro/atualização. Auth com user_id: "
            f"{user_id_telegram_para_get}"
        )
        usuario_completo = await obter_usuario_por_telefone(
            telefone=telefone_id_interno, user_id=user_id_telegram_para_get
        )

        if not usuario_completo:
            logger.error(
                f"Falha ao obter usuário ({telefone_id_interno}) após "
                f"registro/atualização (aparentemente bem-sucedido)."
            )
            return {
                "error": "Falha ao recuperar usuário pós criação/atualização.",
                "detail": f"Usuário {telefone_id_interno} não encontrado.",
                "status_code": 500
            }

        logger.info(
            f"Usuário completo obtido para {telefone_id_interno}: "
            f"{usuario_completo}"
        )
        return usuario_completo

    except Exception as e:
        logger.exception(
            f"Erro em obter_ou_criar_usuario para telegram_id: "
            f"{telegram_user_id}. Erro: {e}"
        )
        return {
            "error": "Erro inesperado ao obter ou criar usuário.",
            "detail": str(e),
            "status_code": 500
        }
