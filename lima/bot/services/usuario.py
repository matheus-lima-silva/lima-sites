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
from .token_service import token_manager

logger = logging.getLogger(__name__)


def _armazenar_token_usuario(access_token: str) -> None:
    """
    Armazena token de acesso no TokenManager
    """
    token_manager.set_token(access_token)


async def obter_usuario_por_telefone(
    telefone: str,
    user_id: Optional[int] = None,  # Adicionado
    user_name: Optional[str] = None,
    expected_phone: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Busca um usuário pelo número de telefone.

    Args:
        telefone: Número de telefone do usuário.
        user_id: ID do usuário do Telegram para autenticação (opcional).
        user_name: Nome do usuário do Telegram.
        expected_phone: Telefone esperado para o usuário.

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
    logger.info(
        f'DEBUG: obter_usuario_por_telefone chamando fazer_requisicao_get com:'
        f'user_id={user_id}, user_name={user_name}, expected_phone={
            expected_phone
        }'
    )
    response_data = await fazer_requisicao_get(
        'usuarios/',
        params,
        user_id=user_id,
        user_name=user_name,
        expected_phone=expected_phone,
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
        'telegram_user_id': telegram_user_id,
    }

    if nome:
        data['nome'] = nome

    if telefone_para_api:
        data['phone_number'] = telefone_para_api

    log_msg = (
        f'Registrando novo usuário via API: '
        f'telegram_user_id={telegram_user_id}, nome={nome}, '
        f'telefone_para_api={telefone_para_api}'
    )
    logger.info(log_msg)
    # Retorna a resposta completa da API, que esperamos que contenha o token
    response_data = await fazer_requisicao_post('auth/telegram/register', data)
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
        f'Tentando atualizar último acesso para usuário ID: {id_alvo_usuario} '
        f'(autenticado como user_id: {user_id_auth})'
    )

    try:
        usuario_data = await fazer_requisicao_get(
            f'usuarios/{id_alvo_usuario}', user_id=user_id_auth
        )

        if not usuario_data:
            warning_msg = (
                f'Usuário ID {id_alvo_usuario} não encontrado (GET) ao tentar '
                f'atualizar último acesso. Autenticado como {user_id_auth}.'
            )
            logger.warning(warning_msg)
            return {
                'error': f'Usuário {id_alvo_usuario} não encontrado via GET',
                'status_code': 404,
            }

        return await fazer_requisicao_put(
            f'usuarios/{id_alvo_usuario}',
            data=usuario_data,
            user_id=user_id_auth,
        )

    except Exception as e:
        error_msg = (
            'Erro ao atualizar último acesso para '
            f'usuário ID {id_alvo_usuario} '
            f'(autenticado como {user_id_auth}): {str(e)}'
        )
        logger.error(error_msg)
        return {'error': 'Falha ao atualizar último acesso', 'detail': str(e)}


async def obter_usuario_por_telegram_id(
    telegram_user_id: int,
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,
    expected_phone: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Busca um usuário pelo telegram_user_id.
    """
    params = {'telegram_user_id': telegram_user_id}
    logger.info(
        'DEBUG: obter_usuario_por_telegram_id chamando fazer_requisicao_get'
        ' com: '
        f'user_id={user_id}, user_name={user_name}, '
        f'expected_phone={expected_phone}'
    )
    response_data = await fazer_requisicao_get(
        'usuarios/',
        params,
        user_id=user_id,
        user_name=user_name,
        expected_phone=expected_phone,
    )

    if isinstance(response_data, list):
        # Filtra exatamente pelo telegram_user_id
        for usuario in response_data:
            if str(usuario.get('telegram_user_id')) == str(telegram_user_id):
                return usuario
        # Se não encontrar, retorna o primeiro como fallback
        if response_data:
            return response_data[0]
    elif isinstance(response_data, dict):
        if response_data:
            return response_data
    return None


async def obter_ou_criar_usuario(
    telegram_user_id: int,
    nome: Optional[str],
    telefone_id_interno: str,  # Ex: "telegram_12345"
) -> Dict[str, Any]:
    """
    Garante que um usuário exista/seja criado/atualizado via API.

    Primeiro, chama /auth/telegram/register para criar/atualizar o usuário
    (incluindo nome, telefone, last_seen) e obter o token.
    Depois, busca e retorna os dados completos do usuário.
    """
    try:
        logger.info(
            f'Processando obter_ou_criar_usuario para telegram_id: '
            f'{telegram_user_id}, nome: {nome}, '
            f'telefone_id_interno: {telefone_id_interno}'
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
            access_token = dados_registro.get('access_token')

            if access_token:
                # Armazena token usando instância local para evitar ciclo
                _armazenar_token_usuario(access_token)
                logger.info('Token de acesso armazenado no TokenManager.')
            else:
                logger.warning(
                    "Resposta de criar_usuario não continha 'access_token'."
                )

        else:
            logger.error(
                f'Falha ao registrar/logar usuário {telegram_user_id} '
                f'via criar_usuario. Resposta: {dados_registro}'
            )
            return {
                'error': 'Falha na etapa de registro/login do usuário.',
                'detail': (
                    f'Resposta inesperada de criar_usuario: {dados_registro}'
                ),
                'status_code': 500,
            }

        # Etapa 2: Buscar os dados completos do usuário usando /usuarios/me.
        # Este endpoint permite que usuários básicos acessem próprios dados.
        # O token para telegram_user_id já deve estar no token_manager.
        logger.info(
            'Buscando dados do usuário atual usando endpoint /usuarios/me '
            'após registro/atualização. Telegram_user_id: %s',
            telegram_user_id,
        )
        usuario_completo = await fazer_requisicao_get(
            'usuarios/me',
            user_id=telegram_user_id,
            user_name=nome,
            expected_phone=telefone_id_interno,
        )

        if not usuario_completo:
            logger.error(
                f'Falha ao obter usuário ({telefone_id_interno}) após '
                f'registro/atualização (aparentemente bem-sucedido).'
            )
            return {
                'error': 'Falha ao recuperar usuário pós criação/atualização.',
                'detail': f'Usuário {telefone_id_interno} não encontrado.',
                'status_code': 500,
            }

        logger.info(
            f'Usuário completo obtido para {telefone_id_interno}: '
            f'{usuario_completo}'
        )
        return usuario_completo

    except Exception as e:
        logger.exception(
            f'Erro em obter_ou_criar_usuario para telegram_id: '
            f'{telegram_user_id}. Erro: {e}'
        )
        return {
            'error': 'Erro inesperado ao obter ou criar usuário.',
            'detail': str(e),
            'status_code': 500,
        }
