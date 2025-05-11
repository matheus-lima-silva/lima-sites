from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import text

from ..models import (
    Busca,
    BuscaLog,
    Detentora,
    Endereco,
    EnderecoOperadora,
    NivelAcesso,
    TipoBusca,
)
from ..schemas import BuscaCreate, BuscaRead
from ..utils.dependencies import (
    AsyncSessionDep,
    CurrentUserDep,
    IdPathDep,
    SuperUserDep,
)
from ..utils.permissions import verificar_permissao_basica

router = APIRouter(prefix='/buscas', tags=['Buscas'])


class BuscaFiltrosParams(BaseModel):
    """Parâmetros de filtro para listagem de buscas."""

    id_endereco: Optional[int] = Field(
        default=None, description='ID do endereço para filtrar'
    )
    operadora_codigo: Optional[str] = Field(
        default=None, description='Código da operadora para filtrar'
    )
    detentora_codigo: Optional[str] = Field(
        default=None, description='Código da detentora para filtrar'
    )
    skip: int = Field(default=0, description='Número de registros a pular')
    limit: int = Field(default=100, description='Número máximo de registros')


BuscaFiltrosParamsDep = Annotated[BuscaFiltrosParams, Depends()]


@router.post(
    '/', response_model=BuscaRead, status_code=status.HTTP_201_CREATED
)
async def registrar_busca(
    busca: BuscaCreate,
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
):
    """
    Registra uma nova busca feita pelo usuário

    * Requer autenticação
    * A busca será associada ao usuário logado
    * Registra também um log para auditoria
    """
    # Cria a nova busca associando-a ao usuário atual
    db_busca = Busca(
        id_endereco=busca.id_endereco,
        id_usuario=current_user.id,  # Usa ID do usuário logado
        info_adicional=busca.info_adicional,
    )

    session.add(db_busca)

    # Adicionar registro de log para auditoria
    busca_log = BuscaLog(
        usuario_id=current_user.id,
        endpoint='/buscas',
        parametros=f'id_endereco={busca.id_endereco}',
        tipo_busca=TipoBusca.por_id,
    )
    session.add(busca_log)

    await session.commit()
    await session.refresh(db_busca)

    return db_busca


@router.get('/{busca_id}', response_model=BuscaRead)
async def obter_busca(
    busca_id: IdPathDep,
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
):
    """
    Recupera detalhes de uma busca específica

    * Requer autenticação
    * Usuários básicos só podem acessar suas próprias buscas
    * Usuários intermediários e super_usuários podem ver todas as buscas
    """
    stmt = (
        select(Busca)
        .where(Busca.id == busca_id)
        .options(
            selectinload(Busca.usuario),
            selectinload(Busca.endereco)
            .selectinload(Endereco.operadoras)
            .selectinload(EnderecoOperadora.operadora),
            selectinload(Busca.endereco).selectinload(Endereco.detentora),
        )
    )

    result = await session.execute(stmt)
    busca = result.scalar_one_or_none()

    if not busca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Busca não encontrada',
        )

    # Usando função centralizada para verificação de permissão
    verificar_permissao_basica(current_user, busca.id_usuario, 'busca')

    return busca


@router.get('/', response_model=List[BuscaRead])
async def listar_buscas(
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
    filtros: BuscaFiltrosParamsDep,
):
    """
    Lista buscas com paginação e filtros

    * Requer autenticação
    * Usuários básicos só veem suas próprias buscas
    * Usuários intermediários e super_usuários veem todas as buscas
    * Permite filtrar por endereço, operadora ou detentora
    """
    # Base query
    query = select(Busca).options(
        selectinload(Busca.usuario),
        selectinload(Busca.endereco)
        .selectinload(Endereco.operadoras)
        .selectinload(EnderecoOperadora.operadora),
        selectinload(Busca.endereco).selectinload(Endereco.detentora),
    )

    # Restrição para usuários básicos
    if current_user.nivel_acesso == NivelAcesso.basico:
        query = query.where(Busca.id_usuario == current_user.id)

    # Filtros adicionais
    if filtros.id_endereco:
        query = query.where(Busca.id_endereco == filtros.id_endereco)

    if filtros.operadora_codigo:
        query = (
            query.join(Busca.endereco)
            .join(Endereco.operadoras)
            .join(EnderecoOperadora.operadora)
            .where(
                EnderecoOperadora.codigo_operadora == filtros.operadora_codigo
            )
        )

    if filtros.detentora_codigo:
        query = (
            query.join(Busca.endereco)
            .join(Endereco.detentora)
            .where(Detentora.codigo == filtros.detentora_codigo)
        )

    # Aplica paginação
    query = query.order_by(Busca.data_busca.desc())
    query = query.offset(filtros.skip).limit(filtros.limit)

    result = await session.execute(query)
    buscas = result.scalars().all()

    # Registrar na auditoria
    tipo_busca = TipoBusca.por_id
    if filtros.operadora_codigo:
        tipo_busca = TipoBusca.por_operadora
    elif filtros.detentora_codigo:
        tipo_busca = TipoBusca.por_detentora

    busca_log = BuscaLog(
        usuario_id=current_user.id,
        endpoint='/buscas',
        parametros=(
            f'id_endereco={filtros.id_endereco},'
            f'operadora={filtros.operadora_codigo},'
            f'detentora={filtros.detentora_codigo}'
        ),
        tipo_busca=tipo_busca,
    )
    session.add(busca_log)
    await session.commit()

    return buscas


@router.delete('/{busca_id}', status_code=status.HTTP_204_NO_CONTENT)
async def deletar_busca(
    busca_id: IdPathDep,
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
):
    """
    Remove uma busca do histórico

    * Usuários básicos só podem deletar suas próprias buscas
    * Usuários intermediários não podem deletar buscas
    * Super-usuários podem deletar qualquer busca
    """
    # Localiza a busca
    stmt = select(Busca).where(Busca.id == busca_id)
    result = await session.execute(stmt)
    busca = result.scalar_one_or_none()

    if not busca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Busca não encontrada',
        )

    # Verifica permissão
    if current_user.nivel_acesso == NivelAcesso.basico:
        verificar_permissao_basica(current_user, busca.id_usuario, 'busca')
    elif current_user.nivel_acesso == NivelAcesso.intermediario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Usuários de nível intermediário não podem deletar buscas',
        )
    # Super-usuários podem deletar qualquer busca

    # Remove a busca
    await session.delete(busca)
    await session.commit()


@router.get('/estatisticas/resumo', response_model=dict)
async def estatisticas_buscas(
    session: AsyncSessionDep,
    current_user: SuperUserDep,
):
    """
    Retorna estatísticas sobre as buscas realizadas

    * Requer nível de acesso super_usuario
    * Exibe contagens e distribuição por tipo de busca
    """
    # Estatísticas do sistema tradicional de buscas
    total_buscas = await session.scalar(
        select(text('COUNT(*)')).select_from(Busca)
    )

    # Estatísticas do sistema de auditoria
    total_logs = await session.scalar(
        select(text('COUNT(*)')).select_from(BuscaLog)
    )

    # Distribuição por tipo de busca na auditoria
    query_tipos = select(
        BuscaLog.tipo_busca, text('COUNT(*) as total')
    ).group_by(BuscaLog.tipo_busca)

    result_tipos = await session.execute(query_tipos)
    por_tipo = {row[0].value: row[1] for row in result_tipos}

    # Buscas por operadora (top 5)
    query_operadoras = text("""
        SELECT o.nome, COUNT(*) as total FROM busca_logs bl
        JOIN usuarios u ON bl.usuario_id = u.id
        WHERE bl.tipo_busca = 'por_operadora'
        GROUP BY bl.parametros
        ORDER BY total DESC
        LIMIT 5
    """)

    result_operadoras = await session.execute(query_operadoras)
    por_operadora = {row[0]: row[1] for row in result_operadoras}

    # Buscas por detentora (top 5)
    query_detentoras = text("""
        SELECT d.nome, COUNT(*) as total FROM busca_logs bl
        JOIN usuarios u ON bl.usuario_id = u.id
        WHERE bl.tipo_busca = 'por_detentora'
        GROUP BY bl.parametros
        ORDER BY total DESC
        LIMIT 5
    """)

    result_detentoras = await session.execute(query_detentoras)
    por_detentora = {row[0]: row[1] for row in result_detentoras}

    return {
        'total_buscas': total_buscas,
        'total_logs_auditoria': total_logs,
        'por_tipo_busca': por_tipo,
        'top_operadoras': por_operadora,
        'top_detentoras': por_detentora,
    }
