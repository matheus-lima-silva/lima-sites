"""
Estatísticas relacionadas a endereços.
"""

from typing import Dict

from fastapi import APIRouter
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ....models import (
    Endereco,
    EnderecoOperadora,
    Operadora,
)
from ....utils.dependencies import AsyncSessionDep, CurrentUserDep

router = APIRouter()


async def _get_total_enderecos(session: AsyncSession) -> int:
    """Retorna o total de endereços cadastrados."""
    return (
        await session.scalar(select(func.count()).select_from(Endereco)) or 0
    )


async def _get_enderecos_por_uf(session: AsyncSession) -> Dict:
    """Retorna a contagem de endereços por UF."""
    stmt = select(Endereco.uf, func.count().label('total')).group_by(
        Endereco.uf
    )
    result = await session.execute(stmt)
    return {row.uf: row.total for row in result}


async def _get_enderecos_por_tipo(session: AsyncSession) -> Dict:
    """Retorna a contagem de endereços por tipo."""
    stmt = select(Endereco.tipo, func.count().label('total')).group_by(
        Endereco.tipo
    )
    result = await session.execute(stmt)
    por_tipo = {}
    for row in result:
        tipo_key = (
            str(row.tipo.value) if row.tipo is not None else 'desconhecido'
        )
        por_tipo[tipo_key] = row.total
    return por_tipo


async def _get_enderecos_por_operadora(session: AsyncSession) -> Dict:
    """Retorna a contagem de endereços por operadora."""
    stmt = (
        select(Operadora.nome, func.count().label('total'))
        .join(EnderecoOperadora)
        .join(Endereco)
        .group_by(Operadora.nome)
    )
    result = await session.execute(stmt)
    return {row.nome: row.total for row in result}


async def _get_enderecos_multi_operadoras(session: AsyncSession) -> int:
    """Retorna a contagem de endereços com múltiplas operadoras."""
    sql = """
    SELECT COUNT(*) FROM (
        SELECT endereco_id
        FROM endereco_operadora
        GROUP BY endereco_id
        HAVING COUNT(operadora_id) > 1
    ) AS multi_op
    """
    result = await session.execute(text(sql))
    return result.scalar() or 0


async def _get_enderecos_por_compartilhamento(session: AsyncSession) -> Dict:
    """Retorna estatísticas de compartilhamento de endereços."""
    stmt = select(
        Endereco.compartilhado, func.count().label('total')
    ).group_by(Endereco.compartilhado)

    result = await session.execute(stmt)
    por_compartilhamento = {}
    for row in result:
        status = (
            'compartilhados' if row.compartilhado else 'não_compartilhados'
        )
        por_compartilhamento[status] = row.total

    # Adicionar estatísticas para endereços compartilhados por operadora
    if por_compartilhamento.get('compartilhados', 0) > 0:
        stmt_compartilhados_por_operadora = (
            select(Operadora.nome, func.count().label('total'))
            .join(EnderecoOperadora)
            .join(Endereco)
            .where(Endereco.compartilhado.is_(True))
            .group_by(Operadora.nome)
        )
        result_compartilhados_op = await session.execute(
            stmt_compartilhados_por_operadora
        )
        compartilhados_por_operadora = {
            row.nome: row.total for row in result_compartilhados_op
        }

        # Adicionar às estatísticas apenas se houver endereços compartilhados
        if compartilhados_por_operadora:
            por_compartilhamento['por_operadora'] = (
                compartilhados_por_operadora
            )

    return por_compartilhamento


async def _get_analise_inconsistencia(
    session: AsyncSession, multi_op_count: int, compartilhados: int
) -> Dict:
    """Analisa inconsistências entre endereços multi-operadoras e
    flag compartilhado."""
    sql_inconsistencia = """
    SELECT COUNT(*) FROM (
        SELECT e.id, e.compartilhado, COUNT(eo.operadora_id) as num_operadoras
        FROM enderecos e
        JOIN endereco_operadora eo ON e.id = eo.endereco_id
        GROUP BY e.id, e.compartilhado
        HAVING COUNT(eo.operadora_id) > 1 AND e.compartilhado = FALSE
    ) AS inconsistencia
    """
    result_inconsistencia = await session.execute(text(sql_inconsistencia))
    inconsistencia_count = result_inconsistencia.scalar() or 0

    return {
        'enderecos_multi_operadoras': multi_op_count,
        'enderecos_marcados_compartilhados': compartilhados,
        'enderecos_multi_operadoras_nao_compartilhados': inconsistencia_count,
        'consistente': inconsistencia_count == 0,
    }


@router.get('/estatisticas', response_model=Dict)
async def estatisticas_enderecos(
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
):
    """
    Retorna estatísticas sobre os endereços cadastrados

    * Requer autenticação
    * Todos os usuários podem acessar as estatísticas
    * Inclui contagens de endereços por estado, tipo, etc.
    """
    # Obter estatísticas usando funções auxiliares
    total = await _get_total_enderecos(session)
    por_uf = await _get_enderecos_por_uf(session)
    por_tipo = await _get_enderecos_por_tipo(session)
    por_operadora = await _get_enderecos_por_operadora(session)
    multi_op_count = await _get_enderecos_multi_operadoras(session)
    por_compartilhamento = await _get_enderecos_por_compartilhamento(session)

    # Análise de inconsistência
    analise_inconsistencia = await _get_analise_inconsistencia(
        session, multi_op_count, por_compartilhamento.get('compartilhados', 0)
    )

    return {
        'total': total,
        'por_uf': por_uf,
        'por_tipo': por_tipo,
        'multi_operadoras': multi_op_count,
        'por_operadora': por_operadora,
        'compartilhamento': por_compartilhamento,
        'analise_inconsistencia': analise_inconsistencia,
    }
