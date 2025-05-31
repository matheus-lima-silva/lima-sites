"""
Serviço de autenticação para o Bot.
Este módulo gerencia a autenticação do bot com a API e autenticação Telegram.
"""

import logging
from typing import Optional, Tuple

from telegram import CallbackQuery, Update
from telegram.ext import ContextTypes

from ..formatters.base import escape_markdown
from .usuario import obter_ou_criar_usuario, obter_usuario_por_telegram_id

logger = logging.getLogger(__name__)


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
        try:
            dados_usuario_api = await obter_ou_criar_usuario(
                telegram_user_id=user.id,
                nome=user.full_name,
                telefone_id_interno=f'telegram_{user.id}',
            )
            if dados_usuario_api and 'error' not in dados_usuario_api:
                context.user_data['usuario_id'] = dados_usuario_api.get('id')
                context.user_data['user_id_telegram'] = dados_usuario_api.get(
                    'telegram_user_id', user.id
                )
                return True  # Autenticação bem-sucedida
            else:
                error_detail = (
                    dados_usuario_api.get('detail', 'Erro desconhecido')
                    if dados_usuario_api
                    else 'Resposta None da API'
                )
                logger.error(f'Falha na re-autenticação: {error_detail}')
                if query and query.message:
                    await query.message.reply_text(
                        f'Falha na autenticação: {
                            escape_markdown(error_detail)
                        }.'
                    )
                return False  # Falha na autenticação
        except Exception as e:
            logger.error(f'Exceção durante re-autenticação: {e}')
            if query and query.message:
                await query.message.reply_text(
                    'Erro inesperado de autenticação ao selecionar resultado.'
                )
            return False
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
    try:
        dados_usuario_api = await obter_ou_criar_usuario(
            telegram_user_id=user.id,
            nome=user.full_name,
            telefone_id_interno=f'telegram_{user.id}',
        )

        if dados_usuario_api and 'error' not in dados_usuario_api:
            usuario_id = dados_usuario_api.get('id')
            user_id_telegram = dados_usuario_api.get(
                'telegram_user_id', user.id
            )

            # Salva no contexto
            context.user_data['usuario_id'] = usuario_id
            context.user_data['user_id_telegram'] = user_id_telegram

            return int(usuario_id), int(user_id_telegram)
        else:
            error_detail = (
                dados_usuario_api.get('detail', 'Erro desconhecido')
                if dados_usuario_api
                else 'Resposta None da API'
            )
            logger.error(f'Falha na autenticação do comando: {error_detail}')
            if update.effective_message:
                await update.effective_message.reply_text(
                    'Falha na autenticação. Tente novamente com /start.'
                )
            return None, None

    except Exception as e:
        logger.error(f'Exceção durante autenticação do comando: {e}')
        if update.effective_message:
            await update.effective_message.reply_text(
                'Erro inesperado de autenticação.'
            )
        return None, None


async def obter_nivel_acesso_usuario(usuario_id: int) -> str:
    """
    Obtém o nível de acesso de um usuário.

    Args:
        usuario_id: ID do usuário

    Returns:
        Nível de acesso ('basico', 'intermediario', 'super_usuario')
    """
    try:
        # Busca dados do usuário pela API
        dados_usuario = await obter_usuario_por_telegram_id(
            telegram_user_id=usuario_id, user_id=usuario_id
        )

        if dados_usuario and isinstance(dados_usuario, dict):
            nivel_acesso = dados_usuario.get('nivel_acesso', 'basico')
            logger.debug(
                f'Nível de acesso obtido para usuário {usuario_id}: {
                    nivel_acesso
                }'
            )
            return nivel_acesso
        else:
            logger.warning(
                f'Dados de usuário não encontrados para ID {usuario_id}'
            )
            return 'basico'  # Nível padrão

    except Exception as e:
        logger.error(
            f'Erro ao obter nível de acesso para usuário {usuario_id}: {e}'
        )
        return 'basico'  # Nível padrão em caso de erro
