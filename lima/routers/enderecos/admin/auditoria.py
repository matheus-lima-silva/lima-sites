"""
Operações de auditoria para endereços.
"""

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....database import get_async_session
from ....models import (
    BuscaLog,
    TipoBusca,
    Usuario,
)
from ....security import require_super_usuario

router = APIRouter()

AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]
SuperUserDep = Annotated[Usuario, Depends(require_super_usuario)]


class AuditoriaFiltrosParams(BaseModel):
    """Parâmetros de filtro para listagem de logs de auditoria."""

    skip: int = Field(default=0, description='Número de registros a pular')
    limit: int = Field(default=100, description='Número máximo de registros')
    usuario_id: Optional[int] = Field(
        default=None, description='Filtrar por ID do usuário'
    )
    tipo_busca: Optional[TipoBusca] = Field(
        default=None, description='Filtrar por tipo de busca'
    )


@router.get('/auditoria/buscas', response_model=List[dict])
async def listar_logs_busca(
    session: AsyncSessionDep,
    current_user: SuperUserDep,
    filtros: Annotated[AuditoriaFiltrosParams, Depends()],
):
    """
    Lista os logs de busca para auditoria
    * Requer nível de acesso super_usuario
    * Permite filtrar por usuário e tipo de busca
    """
    query = select(BuscaLog)

    if filtros.usuario_id:
        query = query.where(BuscaLog.usuario_id == filtros.usuario_id)

    if filtros.tipo_busca:
        query = query.where(BuscaLog.tipo_busca == filtros.tipo_busca)

    query = (
        query.order_by(BuscaLog.data_hora.desc())
        .offset(filtros.skip)
        .limit(filtros.limit)
    )

    result = await session.execute(query)
    logs = []

    for row in result.scalars():
        # Obter informações do usuário
        usuario = await session.get(Usuario, row.usuario_id)

        logs.append({
            'id': row.id,
            'usuario': {
                'id': usuario.id,
                'nome': usuario.nome or usuario.telefone,
            },
            'endpoint': row.endpoint,
            'parametros': row.parametros,
            'tipo_busca': row.tipo_busca.value,
            'data_hora': row.data_hora,
        })

    return logs
