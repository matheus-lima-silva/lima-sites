"""
Dependências compartilhadas para todos os routers.

Este módulo centraliza as dependências comuns usadas nos diferentes routers
da aplicação, evitando duplicação de código.
"""

from typing import Annotated

from fastapi import Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..models import Usuario
from ..security import (
    get_current_user,
    require_intermediario,
    require_super_usuario,
)

# Dependências comuns do banco de dados
AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]

# Dependências de autenticação
CurrentUserDep = Annotated[Usuario, Depends(get_current_user)]
IntermediarioUserDep = Annotated[Usuario, Depends(require_intermediario)]
SuperUserDep = Annotated[Usuario, Depends(require_super_usuario)]

# Dependências de validação de parâmetros comuns
IdPathDep = Annotated[int, Path(..., ge=1, description='ID do registro')]
SkipQueryDep = Annotated[int, Query(0, ge=0, description='Registros a pular')]
LimitQueryDep = Annotated[
    int, Query(100, ge=1, le=100, description='Máximo de registros')
]
OrderDescQueryDep = Annotated[
    bool, Query(True, description='Ordenação decrescente')
]


# Função útil para validar parâmetros de ordenação
def create_order_by_dependency(default_field: str, allowed_fields: list[str]):
    """
    Cria uma dependência para ordenação por campo.

    Args:
        default_field: Campo padrão para ordenação
        allowed_fields: Lista de campos permitidos para ordenação

    Returns:
        Uma dependência Annotated para uso nos parâmetros de função
    """

    def order_by_validator(
        order_by: str = Query(
            default_field, description='Campo para ordenação'
        ),
    ):
        if order_by not in allowed_fields:
            return default_field
        return order_by

    return Annotated[str, Depends(order_by_validator)]
