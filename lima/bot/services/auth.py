"""
Serviço de autenticação para o Bot.
Este módulo gerencia a autenticação do bot com a API e autenticação Telegram.
"""

import logging
from typing import Optional, Tuple

from telegram import CallbackQuery, Update
from telegram.ext import ContextTypes

from lima.database import get_async_session  # Adicionado

from ..api_client import fazer_requisicao_get
from ..formatters.base import escape_markdown
from .usuario import (
    obter_ou_criar_usuario,
)

logger = logging.getLogger(__name__)


async def _autenticar_e_atualizar_contexto(
    telegram_user_id: int,
    nome_completo: str,
    context: ContextTypes.DEFAULT_TYPE,
) -> Tuple[Optional[dict], Optional[str]]:
    """
    Chama a API para obter/criar usuário e atualiza o contexto.
    Retorna (dados_usuario_api, None) em sucesso, ou
      (None, error_detail) em falha.
    """
    try:
        # Usa get_async_session para obter uma sessão
        async with get_async_session() as session:  # Corrigido
            dados_usuario_api, access_token = await obter_ou_criar_usuario(
                session=session,  # Passa a sessão para a função
                telegram_user_id=telegram_user_id,
                nome=nome_completo,
                telefone=f'telegram_{telegram_user_id}',  # Corrigido
            )

        if dados_usuario_api:  # É o objeto Usuario ou None
            context.user_data['usuario_id'] = dados_usuario_api.id
            context.user_data['user_id_telegram'] = (
                dados_usuario_api.telegram_user_id  # Acesso direto
            )
            # Token de acesso pode ser armazenado
            context.user_data['access_token'] = access_token
            return dados_usuario_api, None  # Retorna Usuario e None (erro)
        else:
            # Se dados_usuario_api for None, houve problema
            error_detail = 'obter_ou_criar_usuario retornou None'
            logger.error(
                f'Falha em _autenticar_e_atualizar_contexto para '
                f'user {telegram_user_id}: {error_detail}'
            )
            return None, error_detail
    except Exception as e:
        logger.error(
            f'Exceção durante _autenticar_e_atualizar_contexto para '
            f'user {telegram_user_id}: {e}'
        )
        return None, str(e)


# =====================================================
# Funções de Autenticação Telegram - FASE 6 da Refatoração
# Migradas de busca_codigo.py para compatibilizar com módulo auth existente
# =====================================================


async def validar_dados_usuario_contexto(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Tuple[Optional[str], Optional[str]]:
    """
    Valida e retorna usuario_id e user_id_telegram do contexto.

    Args:
        update: Update do Telegram
        context: Contexto do bot

    Returns:
        Tupla com (usuario_id, user_id_telegram) ou (None, None)
          em caso de erro
    """
    usuario_id = context.user_data.get('usuario_id')
    user_id_telegram = context.user_data.get('user_id_telegram')

    if not usuario_id or not user_id_telegram:
        logger.error(
            f'Tentativa de buscar endereço sem usuario_id ({usuario_id}) ou '
            f'user_id_telegram ({user_id_telegram}). '
            f'Isso indica uma falha no fluxo de autenticação anterior.'
        )
        if update.effective_message:
            await update.effective_message.reply_text(
                'Falha crítica na autenticação. '
                'Não foi possível buscar o endereço. '
                'Por favor, tente iniciar com /start.'
            )
        return None, None  # Indica falha que deve encerrar a conversa
    return usuario_id, user_id_telegram


async def reautenticar_usuario_se_necessario(
    query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """
    Re-autentica o usuário se necessário durante callbacks.

    Args:
        query: Callback query do Telegram
        context: Contexto do bot

    Returns:
        True se autenticação bem-sucedida, False caso contrário
    """
    user = query.from_user if query else None
    if not user:
        logger.error(
            'Não foi possível identificar o usuário em '
            'reautenticar_usuario_se_necessario.'
        )
        if query and query.message:
            await query.message.reply_text(
                'Erro: Não foi possível identificar o usuário.'
            )
        return False

    if (
        'usuario_id' not in context.user_data
        or 'user_id_telegram' not in context.user_data
    ):
        logger.info(
            f'Re-autenticando usuário {user.id} em '
            f'reautenticar_usuario_se_necessario.'
        )
        dados_usuario_api, error_detail = (
            await _autenticar_e_atualizar_contexto(
                telegram_user_id=user.id,
                nome_completo=user.full_name,
                context=context,
            )
        )

        if dados_usuario_api:
            return True  # Autenticação bem-sucedida
        else:
            logger.error(f'Falha na re-autenticação: {error_detail}')
            if query and query.message:
                await query.message.reply_text(
                    f'Falha na autenticação: {
                        escape_markdown(error_detail or "Erro desconhecido")
                    }.'
                )
            return False  # Falha na autenticação
    return True  # Usuário já estava autenticado


async def autenticar_e_preparar_contexto_comando(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Tuple[Optional[int], Optional[int]]:
    """
    Autentica usuário e prepara contexto para comandos diretos.

    Args:
        update: Update do Telegram
        context: Contexto do bot

    Returns:
        Tupla com (usuario_id, user_id_telegram) ou (None, None)
          em caso de erro
    """
    user = update.effective_user
    if not user:
        logger.error(
            'Usuário não identificado em'
            ' autenticar_e_preparar_contexto_comando'
        )
        if update.effective_message:
            await update.effective_message.reply_text(
                'Erro: Não foi possível identificar o usuário.'
            )
        return None, None

    # Verifica se já existe autenticação válida
    usuario_id = context.user_data.get('usuario_id')
    user_id_telegram = context.user_data.get('user_id_telegram')

    if usuario_id and user_id_telegram:
        return int(usuario_id), int(user_id_telegram)

    # Autentica o usuário
    dados_usuario_api, error_detail = await _autenticar_e_atualizar_contexto(
        telegram_user_id=user.id,
        nome_completo=user.full_name,
        context=context,
    )

    if dados_usuario_api:
        # Os dados já foram salvos no contexto pela função auxiliar
        return int(context.user_data['usuario_id']), int(
            context.user_data['user_id_telegram']
        )
    else:
        logger.error(f'Falha na autenticação do comando: {error_detail}')
        if update.effective_message:
            await update.effective_message.reply_text(
                'Falha na autenticação. Tente novamente com /start.'
            )
        return None, None


async def obter_nivel_acesso_usuario(usuario_id: int) -> str:
    """
    Obtém o nível de acesso de um usuário da API.
    Usa o telegram_user_id para autenticar a requisição para /usuarios/me.

    Args:
        usuario_id: ID do usuário do Telegram.

    Returns:
        Nível de acesso do usuário (ex: "básico", "intermediário", "avançado")
        ou "desconhecido".
    """
    log_prefix = f'Usuário {usuario_id} via /usuarios/me:'
    try:
        # O usuario_id aqui é o telegram_user_id,
        # usado para autenticar a chamada para /usuarios/me
        # Não precisamos de user_name ou expected_phone para /usuarios/me
        # pois o token já identifica o usuário.
        dados_usuario = await fazer_requisicao_get(
            'usuarios/me', user_id=usuario_id
        )

        if dados_usuario:
            if 'nivel_acesso' in dados_usuario:
                nivel = dados_usuario['nivel_acesso']
                logger.info(f'{log_prefix} Nível de acesso: {nivel}')
                return nivel
            logger.warning(
                f'{log_prefix} Campo "nivel_acesso" não encontrado. '
                f'Dados: {dados_usuario}'
            )
        else:
            logger.warning(
                f'{log_prefix} Não foi possível obter dados. '
                f'Resposta None ou vazia.'
            )

    except (PermissionError, ConnectionError) as e:
        logger.error(
            f'{log_prefix} Erro de rede/permissão ao obter nível de '
            f'acesso: {e}'
        )
    except Exception as e:
        logger.error(
            f'{log_prefix} Erro inesperado ao obter nível de acesso: {e}'
        )
        # Logar o traceback para depuração mais detalhada em caso de erros
        # inesperados
        logger.exception(
            f'{log_prefix} Traceback do erro:'
        )

    return 'desconhecido'


async def verificar_acesso_avancado():
    pass
