"""
Utilitários para validação de recursos e tratamento padronizado de erros.

Este módulo centraliza funções para validação de existência de recursos,
formatação de mensagens de erro e outros padrões recorrentes identificados
no código da aplicação.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Busca, BuscaLog, Endereco

# Definição do tipo genérico para modelos
T = TypeVar('T')

logger = logging.getLogger(__name__)

# Mensagens padronizadas de erro
ERRO_RECURSO_NAO_ENCONTRADO = (
    '❌ Nenhum {recurso} encontrado com o {campo} "{valor}".'
)
ERRO_PERMISSAO_NEGADA = '❌ Você não tem permissão para acessar este recurso.'
ERRO_VALIDACAO = '⚠️ {mensagem}'
ERRO_PROCESSAMENTO = (
    '❌ Ocorreu um erro ao processar sua solicitação.'
    ' Por favor, tente novamente mais tarde.'
)


async def get_resource_or_none(
    session: AsyncSession,
    model_class: Any,
    filter_by: Dict[str, Any],
    options: Optional[List] = None,
    with_for_update: bool = False,
) -> Optional[Any]:
    """
    Busca um recurso no banco de dados, retornando None se não encontrado.

    Args:
        session: Sessão do banco de dados
        model_class: Classe do modelo a ser consultado
        filter_by: Dicionário com os filtros (campo: valor)
        options: Opções de carregamento (selectinload, etc.)
        with_for_update: Se True, adiciona .with_for_update() à consulta

    Returns:
        O objeto encontrado ou None
    """
    try:
        stmt = select(model_class)

        # Aplica os filtros
        for field, value in filter_by.items():
            stmt = stmt.where(getattr(model_class, field) == value)

        # Aplica as opções de carregamento
        if options:
            for option in options:
                stmt = stmt.options(option)

        # Adiciona o bloqueio de atualização se solicitado
        if with_for_update:
            stmt = stmt.with_for_update()

        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f'Erro ao buscar {model_class.__name__}: {str(e)}')
        return None


async def get_endereco_by_identifier(
    session: AsyncSession, identificador: str, options: Optional[List] = None
) -> Optional[Endereco]:
    """
    Busca um endereço por seu identificador (código ou ID).

    Args:
        session: Sessão do banco de dados
        identificador: Código ou ID do endereço
        options: Opções de carregamento (selectinload, etc.)

    Returns:
        O objeto Endereco encontrado ou None
    """
    try:
        # Tenta converter para inteiro (caso seja um ID)
        try:
            endereco_id = int(identificador)
            # Se converteu com sucesso, vamos buscar por ID
            filter_by = {'id': endereco_id}
        except ValueError:
            # Se não for um número, busca por código
            filter_by = {'codigo_endereco': identificador}

        return await get_resource_or_none(
            session, Endereco, filter_by, options
        )
    except Exception as e:
        logger.error(f'Erro ao buscar endereço por identificador: {str(e)}')
        return None


def format_error_message(tipo_erro: str, **kwargs) -> str:
    """
    Formata uma mensagem de erro padronizada.

    Args:
        tipo_erro: Tipo da mensagem (ERRO_RECURSO_NAO_ENCONTRADO, etc.)
        **kwargs: Argumentos para formatação da mensagem

    Returns:
        Mensagem de erro formatada
    """
    try:
        return tipo_erro.format(**kwargs)
    except Exception as e:
        logger.error(f'Erro ao formatar mensagem: {str(e)}')
        return 'Ocorreu um erro inesperado.'


def format_not_found_message(recurso: str, campo: str, valor: str) -> str:
    """
    Formata uma mensagem padronizada para recursos não encontrados.

    Args:
        recurso: Nome do recurso (endereço, usuário, etc.)
        campo: Campo usado para busca (ID, código, etc.)
        valor: Valor buscado

    Returns:
        Mensagem padronizada
    """
    return format_error_message(
        ERRO_RECURSO_NAO_ENCONTRADO, recurso=recurso, campo=campo, valor=valor
    )


@dataclass
class SearchLogParams:
    user_id: int
    endereco_id: int
    endpoint: str
    parametros: str
    tipo_busca: Any
    info_adicional: Optional[str] = None


async def register_search_log(
    session: AsyncSession,
    params: SearchLogParams,
) -> Tuple[Any, Any]:
    """
    Registra o log de uma busca no sistema.

    Args:
        session: Sessão do banco de dados
        params: Parâmetros agrupados para o log de busca

    Returns:
        Tupla com os objetos de log criados (BuscaLog, Busca)
    """

    try:
        # Registrar no log de buscas
        busca_log = BuscaLog(
            usuario_id=params.user_id,
            endpoint=params.endpoint,
            parametros=params.parametros,
            tipo_busca=params.tipo_busca,
        )
        session.add(busca_log)

        # Registrar no histórico do usuário
        info = (
            params.info_adicional
            or f'Busca via {params.endpoint}: {params.parametros}'
        )
        new_busca = Busca(
            id_endereco=params.endereco_id,
            id_usuario=params.user_id,
            info_adicional=info,
        )
        session.add(new_busca)

        return busca_log, new_busca
    except Exception as e:
        logger.error(f'Erro ao registrar log de busca: {str(e)}')
        # Não propaga a exceção para não interromper o fluxo principal
        return None, None
