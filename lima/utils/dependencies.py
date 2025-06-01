"""
Dependências compartilhadas para todos os routers.

Este módulo centraliza as dependências comuns usadas nos diferentes routers
da aplicação, evitando duplicação de código.
"""

# Dependências comuns do banco de dados
from typing import Annotated, AsyncGenerator, Optional

from fastapi import Depends, Path, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

# Importar USER_LOAD_OPTIONS de core.loading_options
# Este import é necessário porque outros módulos (como security.py ou routers)
# podem importar CurrentUserDep, etc., que dependem implicitamente de
# USER_LOAD_OPTIONS estar disponível no escopo onde get_current_user é usado.
# Mesmo que não seja usado DIRETAMENTE neste arquivo, ele é parte da
# "interface" que este módulo de dependências provê.
from ..core.loading_options import USER_LOAD_OPTIONS  # noqa: F401
from ..database import get_async_session
from ..models import Usuario  # Apenas Usuario é necessário aqui diretamente
from ..security import (
    get_current_user,
    require_intermediario,
    require_super_usuario,
)


async def get_session_dependency() -> AsyncGenerator[AsyncSession, None]:
    """Dependência que fornece uma sessão do banco de dados."""
    async with get_async_session() as session:
        yield session


AsyncSessionDep = Annotated[AsyncSession, Depends(get_session_dependency)]

# USER_LOAD_OPTIONS foi movido para core.loading_options.py
# e é importado acima para garantir que esteja no contexto quando necessário.

# Dependências de autenticação
CurrentUserDep = Annotated[Usuario, Depends(get_current_user)]
IntermediarioUserDep = Annotated[Usuario, Depends(require_intermediario)]
SuperUserDep = Annotated[Usuario, Depends(require_super_usuario)]

# Dependências de validação de parâmetros comuns
IdPathDep = Annotated[int, Path(ge=1, description='ID do registro')]


# Corrigindo a definição dos parâmetros Query
# Em vez de usar o valor padrão no Query(), definimos após o Annotated
def skip_query(
    skip: int = Query(0, ge=0, description='Registros a pular'),
) -> int:
    return skip


def limit_query(
    limit: int = Query(100, ge=1, le=100, description='Máximo de registros'),
) -> int:
    return limit


def order_desc_query(
    order_desc: bool = Query(True, description='Ordenação decrescente'),
) -> bool:
    return order_desc


# Adicionando a dependência NomeQueryDep que estava faltando
def nome_query(
    nome: Optional[str] = Query(  # Alterado para Optional[str]
        None,  # Alterado de ... para None
        min_length=2,
        max_length=100,
        description='Nome do usuário (opcional)',
    ),
) -> Optional[str]:  # Alterado para Optional[str]
    return nome


SkipQueryDep = Annotated[int, Depends(skip_query)]
LimitQueryDep = Annotated[int, Depends(limit_query)]
OrderDescQueryDep = Annotated[bool, Depends(order_desc_query)]
NomeQueryDep = Annotated[Optional[str], Depends(nome_query)]
# Alterado para Optional[str]


# Dependência para o parâmetro de telefone
def telefone_query(
    telefone: Optional[str] = Query(
        None,
        description='Filtrar usuários por telefone (opcional)',
        regex=r'^\\d{10,11}$',  # Exemplo de regex para validar telefone
    ),
) -> Optional[str]:
    return telefone


TelefoneQueryDep = Annotated[Optional[str], Depends(telefone_query)]


# Agrupando dependências de filtro e paginação
class ListarUsuariosParams(BaseModel):
    skip: SkipQueryDep
    limit: LimitQueryDep
    nome: NomeQueryDep
    telefone: TelefoneQueryDep


ListarUsuariosParamsDep = Annotated[
    ListarUsuariosParams, Depends(ListarUsuariosParams)
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
