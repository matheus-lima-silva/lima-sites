"""
Módulo para gerenciar o registro de usuários do Telegram.
Controla o fluxo de registro de novos usuários, solicitando nome e telefone.
"""

import re
from enum import Enum
from typing import Dict, Optional, Tuple, Union

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import Usuario
from .core import escape_markdown, send_interactive_message, send_text_message

# Constantes para validação
MIN_NOME_LENGTH = 3  # Tamanho mínimo para um nome válido


# Estados de registro para o fluxo de cadastro
class EstadoRegistro(str, Enum):
    INICIAL = 'inicial'
    AGUARDANDO_NOME = 'aguardando_nome'
    AGUARDANDO_TELEFONE = 'aguardando_telefone'
    CONFIRMACAO = 'confirmacao'
    COMPLETO = 'completo'


# Armazenamento temporário de dados de registro por chat_id
# Em uma implementação de produção, isso deveria usar
#  um banco de dados ou cache
_registros_em_andamento: Dict[Union[int, str], Dict] = {}


def iniciar_registro(chat_id: Union[int, str]) -> None:
    """
    Inicia o processo de registro para um chat específico.

    Args:
        chat_id: ID do chat do Telegram
    """
    _registros_em_andamento[chat_id] = {
        'estado': EstadoRegistro.INICIAL,
        'nome': None,
        'telefone': None,
    }


def obter_estado_registro(
    chat_id: Union[int, str],
) -> Optional[EstadoRegistro]:
    """
    Obtém o estado atual do registro para um chat.

    Args:
        chat_id: ID do chat do Telegram

    Returns:
        EstadoRegistro ou None se não estiver em processo de registro
    """
    if chat_id not in _registros_em_andamento:
        return None

    return _registros_em_andamento[chat_id]['estado']


def atualizar_estado_registro(
    chat_id: Union[int, str], estado: EstadoRegistro
) -> None:
    """
    Atualiza o estado do registro para um chat.

    Args:
        chat_id: ID do chat do Telegram
        estado: Novo estado do registro
    """
    if chat_id in _registros_em_andamento:
        _registros_em_andamento[chat_id]['estado'] = estado


def salvar_nome(chat_id: Union[int, str], nome: str) -> None:
    """
    Salva o nome fornecido pelo usuário.

    Args:
        chat_id: ID do chat do Telegram
        nome: Nome fornecido pelo usuário
    """
    if chat_id in _registros_em_andamento:
        _registros_em_andamento[chat_id]['nome'] = nome
        _registros_em_andamento[chat_id]['estado'] = (
            EstadoRegistro.AGUARDANDO_TELEFONE
        )


def salvar_telefone(chat_id: Union[int, str], telefone: str) -> None:
    """
    Salva o telefone fornecido pelo usuário.

    Args:
        chat_id: ID do chat do Telegram
        telefone: Telefone fornecido pelo usuário
    """
    if chat_id in _registros_em_andamento:
        # Normaliza o telefone para formato internacional se necessário
        if not telefone.startswith('+'):
            telefone = '+' + telefone

        _registros_em_andamento[chat_id]['telefone'] = telefone
        _registros_em_andamento[chat_id]['estado'] = EstadoRegistro.CONFIRMACAO


def obter_dados_registro(chat_id: Union[int, str]) -> Dict:
    """
    Retorna os dados de registro atuais para um chat.

    Args:
        chat_id: ID do chat do Telegram

    Returns:
        Dict com os dados do registro ou dict vazio se não existe
    """
    return _registros_em_andamento.get(chat_id, {})


async def finalizar_registro(
    chat_id: Union[int, str], usuario_id: int, session: AsyncSession
) -> bool:
    """
    Finaliza o registro atualizando os dados do usuário no banco de dados.

    Args:
        chat_id: ID do chat do Telegram
        usuario_id: ID do usuário no banco de dados
        session: Sessão do banco de dados

    Returns:
        bool: True se o registro foi concluído com sucesso
    """
    if chat_id not in _registros_em_andamento:
        return False

    dados = _registros_em_andamento[chat_id]

    if not dados.get('nome') or not dados.get('telefone'):
        return False

    try:
        # Atualiza o usuário com os novos dados
        await session.execute(
            update(Usuario)
            .where(Usuario.id == usuario_id)
            .values(
                nome=dados['nome'],
                telefone_contato=dados['telefone'],  # Telefone de contato real
            )
        )

        await session.commit()

        # Marca o registro como completo
        _registros_em_andamento[chat_id]['estado'] = EstadoRegistro.COMPLETO

        return True
    except Exception:
        await session.rollback()
        return False


def cancelar_registro(chat_id: Union[int, str]) -> None:
    """
    Cancela o processo de registro em andamento.

    Args:
        chat_id: ID do chat do Telegram
    """
    if chat_id in _registros_em_andamento:
        del _registros_em_andamento[chat_id]


async def processar_comando_cancelar(chat_id: Union[int, str]) -> Dict:
    """
    Processa o comando de cancelamento de registro.

    Args:
        chat_id: ID do chat do Telegram

    Returns:
        Dict com o status do cancelamento
    """
    cancelar_registro(chat_id)
    await send_text_message(
        chat_id=chat_id,
        message=(
            '❌ Registro cancelado\\. Você pode iniciar novamente a qualquer '
            'momento com /registro'
        ),
    )
    return {'status': 'cancelled', 'process': 'registro'}


async def iniciar_novo_registro(chat_id: Union[int, str]) -> Dict:
    """
    Inicia um novo processo de registro.

    Args:
        chat_id: ID do chat do Telegram

    Returns:
        Dict com o status da inicialização
    """
    iniciar_registro(chat_id)
    atualizar_estado_registro(chat_id, EstadoRegistro.AGUARDANDO_NOME)

    await send_text_message(
        chat_id=chat_id,
        message=(
            '📝 *Registro de Usuário*\n\n'
            'Vamos completar seu cadastro para melhorar sua experiência\\.\n\n'
            'Por favor, informe seu nome completo\\.\n\n'
            'Você pode cancelar o processo a qualquer momento '
            'enviando "cancelar"\\.'
        ),
    )
    return {'status': 'initiated', 'process': 'registro'}


async def processar_aguardando_nome(
    chat_id: Union[int, str], nome: str
) -> Tuple[bool, Dict]:
    """
    Processa a etapa de aguardando nome no registro.

    Args:
        chat_id: ID do chat do Telegram
        nome: Nome fornecido pelo usuário

    Returns:
        Tuple[bool, Dict]: (Sucesso, Resultado do processamento)
    """
    nome = nome.strip()

    if len(nome) < MIN_NOME_LENGTH:
        await send_text_message(
            chat_id=chat_id,
            message=(
                f'⚠️ O nome deve ter pelo menos {MIN_NOME_LENGTH} caracteres\\.'
                'Por favor, tente novamente\\.'
            ),
        )
        return False, {
            'status': 'error',
            'process': 'registro',
            'step': 'nome',
        }

    salvar_nome(chat_id, nome)

    await send_text_message(
        chat_id=chat_id,
        message=(
            f'✅ Nome salvo: *{escape_markdown(nome)}*\n\n'
            'Agora, por favor, informe seu número de telefone de contato '
            'no formato internacional \\(exemplo: \\+5511999999999\\)\\.\n\n'
            'Este telefone será usado apenas para contato em caso de '
            'necessidade\\.'
        ),
    )
    return True, {
        'status': 'in_progress',
        'process': 'registro',
        'step': 'telefone',
    }


async def processar_aguardando_telefone(
    chat_id: Union[int, str], telefone: str
) -> Tuple[bool, Dict]:
    """
    Processa a etapa de aguardando telefone no registro.

    Args:
        chat_id: ID do chat do Telegram
        telefone: Telefone fornecido pelo usuário

    Returns:
        Tuple[bool, Dict]: (Sucesso, Resultado do processamento)
    """
    telefone = telefone.strip()

    # Adiciona o + no início se não tiver
    if not telefone.startswith('+'):
        telefone = '+' + telefone

    # Validação básica do telefone
    if not re.match(r'^\+[1-9]\d{1,14}$', telefone):
        await send_text_message(
            chat_id=chat_id,
            message=(
                '⚠️ Formato de telefone inválido\\. '
                'Por favor, use o formato internacional: \\+XXXXXXXXXXXX '
                '\\(com o sinal de \\+ no início seguido do código do país e '
                'número\\)\\.'
            ),
        )
        return False, {
            'status': 'error',
            'process': 'registro',
            'step': 'telefone',
        }

    salvar_telefone(chat_id, telefone)
    dados = obter_dados_registro(chat_id)

    # Mostra confirmação
    await send_interactive_message(
        chat_id=chat_id,
        header_text='Confirmar Dados',
        body_text=(
            'Por favor, confirme se os dados abaixo estão corretos:\n\n'
            f'Nome: {dados["nome"]}\n'
            f'Telefone: {dados["telefone"]}'
        ),
        footer_text='Você pode cancelar e recomeçar enviando "cancelar"',
        buttons=[
            {'id': 'confirmar_registro', 'title': '✅ Confirmar dados'},
            {'id': 'cancelar_registro', 'title': '❌ Cancelar registro'},
        ],
    )
    return True, {
        'status': 'in_progress',
        'process': 'registro',
        'step': 'confirmacao',
    }


async def processar_confirmacao(
    chat_id: Union[int, str],
    user_id: int,
    session: AsyncSession,
    resposta: str,
) -> Dict:
    """
    Processa a etapa de confirmação no registro.

    Args:
        chat_id: ID do chat do Telegram
        user_id: ID do usuário no banco de dados
        session: Sessão do banco de dados
        resposta: Resposta do usuário

    Returns:
        Dict: Resultado do processamento
    """
    resposta = resposta.lower()

    # Caso 1: Confirmação
    if 'confirmar' in resposta or 'sim' in resposta:
        sucesso = await finalizar_registro(chat_id, user_id, session)

        if sucesso:
            await send_text_message(
                chat_id=chat_id,
                message=(
                    '✅ *Registro concluído com sucesso\\!*\n\n'
                    'Seus dados foram salvos e agora você pode usar todos os '
                    'recursos do sistema\\.\n\n'
                    'Use /ajuda para ver todos os comandos disponíveis\\.'
                ),
            )
            return {'status': 'completed', 'process': 'registro'}

        await send_text_message(
            chat_id=chat_id,
            message=(
                '❌ Ocorreu um erro ao salvar seus dados\\. '
                'Por favor, tente novamente mais tarde ou contate o suporte\\.'
            ),
        )
        cancelar_registro(chat_id)
        return {'status': 'error', 'process': 'registro', 'step': 'salvar'}

    # Caso 2: Cancelamento
    if 'cancelar' in resposta or 'não' in resposta:
        return await processar_comando_cancelar(chat_id)

    # Caso 3: Resposta inválida
    await send_text_message(
        chat_id=chat_id,
        message=(
            '⚠️ Por favor, confirme ou cancele o registro\\.\n'
            'Responda "confirmar" para salvar seus dados ou "cancelar" '
            'para desistir\\.'
        ),
    )
    return {
        'status': 'in_progress',
        'process': 'registro',
        'step': 'confirmacao_manual',
    }


async def processar_estado_desconhecido(chat_id: Union[int, str]) -> Dict:
    """
    Processa um estado desconhecido, reiniciando o processo.

    Args:
        chat_id: ID do chat do Telegram

    Returns:
        Dict: Resultado do processamento
    """
    cancelar_registro(chat_id)
    await send_text_message(
        chat_id=chat_id,
        message=(
            '⚠️ Houve um problema no processo de registro\\. '
            'Por favor, tente novamente com /registro'
        ),
    )
    return {
        'status': 'error',
        'process': 'registro',
        'reason': 'unknown_state',
    }


async def processar_registro_usuario(
    session: AsyncSession,
    chat_id: Union[int, str],
    user_id: int,
    message_content: str,
) -> Dict:
    """
    Processa o fluxo de registro de usuário do Telegram.

    Args:
        session: Sessão do banco de dados
        chat_id: ID do chat do Telegram
        user_id: ID do usuário no banco de dados
        message_content: Conteúdo da mensagem recebida

    Returns:
        Dict: Resultado do processamento
    """
    # Comandos especiais durante o registro
    if message_content.lower() == 'cancelar':
        return await processar_comando_cancelar(chat_id)

    # Obtém o estado atual do registro
    estado = obter_estado_registro(chat_id)

    # Processa baseado no estado atual
    if estado is None:
        # Iniciar novo registro
        return await iniciar_novo_registro(chat_id)

    if estado == EstadoRegistro.AGUARDANDO_NOME:
        # Processar nome
        sucesso, resultado = await processar_aguardando_nome(
            chat_id, message_content
        )
        return resultado

    if estado == EstadoRegistro.AGUARDANDO_TELEFONE:
        # Processar telefone
        sucesso, resultado = await processar_aguardando_telefone(
            chat_id, message_content
        )
        return resultado

    if estado == EstadoRegistro.CONFIRMACAO:
        # Processar confirmação
        return await processar_confirmacao(
            chat_id, user_id, session, message_content
        )

    # Estado desconhecido
    return await processar_estado_desconhecido(chat_id)
