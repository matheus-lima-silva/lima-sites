"""
Decorators para centralizar padrões comuns da aplicação.

Este módulo contém decorators para lidar com verificações de permissão,
validação de recursos, tratamento de erros e outros padrões recorrentes
identificados no código da aplicação.
"""

import functools
import logging
from typing import Callable, List, Optional, Union

from fastapi import HTTPException, status

from ..models import NivelAcesso, Usuario
from .permissions import (
    check_user_is_active,
    check_user_is_admin,
    check_user_is_intermediate,
)

logger = logging.getLogger(__name__)


def require_permission(
    required_nivel: Union[NivelAcesso, List[NivelAcesso]],
    owner_field: Optional[str] = None,
):
    """
    Decorator para verificar permissões de usuário.

    Args:
        required_nivel: Nível de acesso requerido ou lista de níveis permitidos
        owner_field: Nome do campo no resultado que identifica o proprietário
          (opcional)
         Se fornecido, usuários básicos podem acessar seus próprios recursos

    Returns:
        Decorator que verifica se o usuário tem acesso ao endpoint

    Exemplo de uso:
        @router.delete("/{id}")
        @require_permission(NivelAcesso.super_usuario)
        async def delete_resource(id: int, usuario: Usuario =
        Depends(get_current_user)):
            # Código do endpoint

    Ou com verificação de propriedade:
        @router.put("/{id}")
        @require_permission([NivelAcesso.intermediario,
          NivelAcesso.super_usuario], owner_field="usuario_id")
        async def update_resource(id: int, usuario: Usuario =
          Depends(get_current_user)):
            # Código do endpoint
    """
    if isinstance(required_nivel, NivelAcesso):
        required_levels = [required_nivel]
    else:
        required_levels = required_nivel

    def decorator(func: Callable) -> Callable:
        def find_usuario(*args, **kwargs):
            # Encontra o usuário atual nos argumentos
            for arg in args:
                if isinstance(arg, Usuario):
                    return arg

            for arg_name, arg_value in kwargs.items():
                if isinstance(arg_value, Usuario):
                    return arg_value

            return None

        def verify_access_permission(usuario):
            # Verifica se o usuário está ativo
            if not check_user_is_active(usuario):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail='Usuário inativo. Contate o administrador.',
                )

            # Super usuários têm acesso a tudo
            if (
                NivelAcesso.super_usuario in required_levels
                and check_user_is_admin(usuario)
            ):
                return True

            # Verifica nível intermediário
            if (
                NivelAcesso.intermediario in required_levels
                and check_user_is_intermediate(usuario)
            ):
                return True

            return False

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Encontra o usuário atual nos argumentos
            usuario = find_usuario(*args, **kwargs)

            if not usuario:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail='Erro interno: usuário não encontrado'
                    ' nos argumentos',
                )

            # Verifica permissões de acesso
            if verify_access_permission(usuario):
                return await func(*args, **kwargs)

            # Verifica se o campo de proprietário está disponível
            if owner_field:
                result = await func(*args, **kwargs)
                if result is None:
                    return None

                # Verifica se o usuário é o proprietário do recurso
                owner_id = getattr(result, owner_field, None)
                if owner_id is not None and owner_id == usuario.id:
                    return result

            # Acesso negado em todos os outros casos
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Você não tem permissão para acessar este recurso.',
            )

        return wrapper

    return decorator


def handle_not_found(resource_name: str):
    """
    Decorator para padronizar o tratamento de recursos não encontrados.

    Args:
        resource_name: Nome do recurso para mensagem de erro (ex: "endereço",
        "usuário")

    Returns:
        Decorator que trata o caso de recurso não encontrado

    Exemplo de uso:
        @router.get("/{id}")
        @handle_not_found("endereço")
        async def get_resource(id: int):
            # Código que retorna None se não encontrado
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            if result is None:
                resource_id = None
                for name, value in kwargs.items():
                    if name in {'id', f'{resource_name}_id'}:
                        resource_id = value
                        break

                message = f'{resource_name.capitalize()} não encontrado'
                if resource_id:
                    message += f' com ID {resource_id}'

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=message,
                )
            return result

        return wrapper

    return decorator


def log_operation(operation_name: str, log_result: bool = False):
    """
    Decorator para registrar operações importantes.

    Args:
        operation_name: Nome da operação para o log
        log_result: Se True, registra também o resultado da operação

    Returns:
        Decorator que registra a operação no log
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Encontra informações relevantes para o log
            usuario_id = None
            resource_id = None

            for arg_name, arg_value in kwargs.items():
                if arg_name == 'id' or arg_name.endswith('_id'):
                    resource_id = arg_value
                if isinstance(arg_value, Usuario):
                    usuario_id = arg_value.id

            # Registra o início da operação
            log_prefix = f'Operação: {operation_name}'
            if usuario_id:
                log_prefix += f' | Usuário: {usuario_id}'
            if resource_id:
                log_prefix += f' | Recurso ID: {resource_id}'

            logger.info(f'{log_prefix} - Iniciada')

            try:
                result = await func(*args, **kwargs)

                # Registra o resultado se solicitado
                if log_result and result is not None:
                    logger.info(
                        f'{log_prefix} - Concluída com sucesso | Resultado: {
                            result
                        }'
                    )
                else:
                    logger.info(f'{log_prefix} - Concluída com sucesso')

                return result
            except Exception as e:
                # Registra erros na operação
                logger.error(f'{log_prefix} - Falha: {str(e)}')
                raise

        return wrapper

    return decorator
