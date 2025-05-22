"""
Módulo de funções utilitárias para verificação de permissões.

Este módulo centraliza as verificações de permissão para evitar duplicação
de código entre os diferentes routers da aplicação.
"""

import logging
from typing import Any

from fastapi import HTTPException, status

from ..models import NivelAcesso, Usuario

logger = logging.getLogger(__name__)


def verificar_permissao_basica(
    current_user: Usuario, recurso_id_usuario: int, recurso_nome: str
) -> None:
    """
    Verifica se um usuário básico tem permissão para acessar/modificar
     um recurso.

    Usuários básicos só podem acessar/modificar seus próprios recursos.

    Args:
        current_user: O usuário atual
        recurso_id_usuario: ID do usuário associado ao recurso
        recurso_nome: Nome do tipo de recurso (para logs)

    Raises:
        HTTPException: Se o usuário não tiver permissão
    """
    if (
        current_user.nivel_acesso == NivelAcesso.basico
        and recurso_id_usuario != current_user.id
    ):
        logger.warning(
            f'Tentativa de acesso não autorizado: Usuário {current_user.id} '
            f'tentou acessar {recurso_nome} do usuário {recurso_id_usuario}'
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f'Não autorizado a acessar {
                recurso_nome
            } de outros usuários',
        )


def verificar_permissao_intermediaria(
    current_user: Usuario, recurso_id_usuario: int, recurso_nome: str
) -> None:
    """
    Verifica se um usuário intermediário tem permissão para acessar/modificar
      um recurso.

    Usuários intermediários só podem modificar seus próprios recursos, em
     certos casos.

    Args:
        current_user: O usuário atual
        recurso_id_usuario: ID do usuário associado ao recurso
        recurso_nome: Nome do tipo de recurso (para logs)

    Raises:
        HTTPException: Se o usuário não tiver permissão
    """
    if (
        current_user.nivel_acesso == NivelAcesso.intermediario
        and recurso_id_usuario != current_user.id
    ):
        logger.warning(
            f'Tentativa de acesso não autorizado: Usuário intermediário '
            f'{current_user.id} tentou modificar {recurso_nome} do usuário '
            f'{recurso_id_usuario}'
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f'Usuários intermediários só podem modificar seus próprios '
                f'{recurso_nome}'
            ),
        )


def verificar_permissao_recurso_processado(
    current_user: Usuario,
    status_recurso: Any,
    status_pendente: Any,
    recurso_nome: str,
) -> None:
    """
    Verifica se um usuário tem permissão para modificar um recurso que já
     foi processado.

    Args:
        current_user: O usuário atual
        status_recurso: Status atual do recurso
        status_pendente: Valor que representa o status pendente
        recurso_nome: Nome do tipo de recurso (para logs)

    Raises:
        HTTPException: Se o recurso já foi processado e o usuário não é
         super_usuario
    """
    if status_recurso != status_pendente:
        if current_user.nivel_acesso != NivelAcesso.super_usuario:
            logger.warning(
                f'Tentativa de modificar {recurso_nome} processado: '
                f'Usuário {current_user.id} com nível {
                    current_user.nivel_acesso
                }'
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f'Não é possível modificar {recurso_nome} que já foram '
                    f'processados'
                ),
            )


def validar_acesso_por_nivel(
    current_user: Usuario,
    objeto: Any,
    campo_id_usuario: str = 'id_usuario',
    recurso: str = 'recurso',
) -> None:
    """
    Valida o acesso a um objeto com base no nível de acesso do usuário.

    - Usuários básicos só podem acessar seus próprios recursos
    - Usuários intermediários e super_usuarios podem acessar todos

    Args:
        current_user: O usuário autenticado
        objeto: O objeto a ser acessado
        campo_id_usuario: Nome do campo que contém o ID do usuário no objeto
        recurso: Nome do recurso para mensagens de erro

    Raises:
        HTTPException: Se o acesso for negado
    """
    if current_user.nivel_acesso == NivelAcesso.basico:
        usuario_id_no_objeto = getattr(objeto, campo_id_usuario, None)
        if usuario_id_no_objeto != current_user.id:
            logger.warning(
                f'Acesso negado: Usuário {current_user.id} tentou acessar '
                f'{recurso} do usuário {usuario_id_no_objeto}'
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f'Não autorizado a acessar este {recurso}',
            )


def check_user_is_active(usuario: Usuario) -> bool:
    """
    Verifica se o usuário está ativo.
    Considera ativo se não for None e não estiver desativado.
    """
    # Ajuste conforme sua lógica de usuário ativo
    return usuario is not None


def check_user_is_admin(usuario: Usuario) -> bool:
    """
    Verifica se o usuário é super usuário (admin).
    """
    return usuario.nivel_acesso == NivelAcesso.super_usuario


def check_user_is_intermediate(usuario: Usuario) -> bool:
    """
    Verifica se o usuário é intermediário.
    """
    return usuario.nivel_acesso == NivelAcesso.intermediario


def escape_markdown_v2(text: str) -> str:
    """
    Escapa caracteres especiais para envio de mensagens no Telegram
    usando MarkdownV2.
    """
    escape_chars = r'_ * [ ] ( ) ~ ` > # + - = | { } . !'
    for char in escape_chars.split():
        text = text.replace(char, f'\\{char}')
    return text
