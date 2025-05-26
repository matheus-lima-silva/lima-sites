"""
Operações para buscar endereços por código, operadora ou detentora.
"""

import logging
from typing import Annotated, List, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....database import get_async_session
from ....models import (
    Anotacao,  # Adicionado
    BuscaLog,
    Detentora,
    Endereco,
    EnderecoOperadora,
    NivelAcesso,  # Adicionada importação faltante
    TipoBusca,
    Usuario,
)
from ....schemas import (
    AnotacaoResumida,
    AutorAnotacao,
    DetentoraRead,
    EnderecoRead,
    EnderecoReadComplete,
    OperadoraRead,
    OperadoraSimples,
)
from ....security import get_current_user
from ..utils import filtrar_anotacoes_por_acesso

router = APIRouter()

# Definições de dependências usando Annotated
AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]
CurrentUserDep = Annotated[Usuario, Depends(get_current_user)]


def load_relations_query(
    load_relations: bool = Query(
        False, description='Carregar dados relacionados'
    ),
) -> bool:
    return load_relations


LoadRelationsDep = Annotated[bool, Depends(load_relations_query)]


async def _buscar_endereco(
    codigo_endereco: str, load_relations: bool, session: AsyncSession
) -> Endereco:
    """Helper function to query the endereco"""
    if load_relations:
        stmt = (
            select(Endereco)
            .where(Endereco.codigo_endereco == codigo_endereco)
            .options(
                selectinload(Endereco.operadoras).selectinload(
                    EnderecoOperadora.operadora
                ),
                selectinload(Endereco.detentora),
                selectinload(Endereco.alteracoes),
                selectinload(Endereco.anotacoes).selectinload(
                    Anotacao.usuario
                ),
            )
        )
    else:
        stmt = select(Endereco).where(
            Endereco.codigo_endereco == codigo_endereco
        )

    return await session.scalar(stmt)


async def _registrar_busca(
    session: AsyncSession, usuario_id: int, codigo_endereco: str
) -> None:
    """Helper function to register the search log"""
    busca_log = BuscaLog(
        usuario_id=usuario_id,
        endpoint='/enderecos/codigo/{codigo}',
        parametros=f'codigo={codigo_endereco}',
        tipo_busca=TipoBusca.por_id,
    )
    session.add(busca_log)
    await session.commit()


async def _processar_anotacoes(
    endereco: Endereco, current_user: Usuario, session: AsyncSession
) -> List[AnotacaoResumida]:
    """Helper function to process annotations"""
    anotacoes_resumidas = []

    # Filtrar por nível de acesso
    if current_user.nivel_acesso == NivelAcesso.basico:
        # Usuário básico só vê suas próprias anotações
        anotacoes_filtradas = [
            a for a in endereco.anotacoes if a.id_usuario == current_user.id
        ]
    else:
        # Usuários privilegiados veem todas as anotações
        anotacoes_filtradas = endereco.anotacoes

    # Carregar os usuários relacionados às anotações
    usuario_ids = [a.id_usuario for a in anotacoes_filtradas]
    if usuario_ids:
        usuarios = await session.execute(
            select(Usuario).where(Usuario.id.in_(usuario_ids))
        )
        usuarios_dict = {u.id: u for u in usuarios.scalars().all()}

        # Converter para o formato esperado em AnotacaoResumida
        for a in anotacoes_filtradas:
            usuario = usuarios_dict.get(a.id_usuario)
            if usuario:
                autor = AutorAnotacao(
                    id=usuario.id,
                    nome=usuario.nome or usuario.telefone,
                )
                anotacao_resumida = AnotacaoResumida(
                    id=a.id,
                    texto=a.texto,
                    data_hora=a.data_criacao,
                    autor=autor,
                )
                anotacoes_resumidas.append(anotacao_resumida)

    return anotacoes_resumidas


def _criar_endereco_basico(endereco: Endereco) -> EnderecoRead:
    """Helper function to create the basic endereco response"""
    return EnderecoRead(
        id=endereco.id,
        codigo_endereco=endereco.codigo_endereco,
        logradouro=endereco.logradouro,
        bairro=endereco.bairro,
        municipio=endereco.municipio,
        uf=endereco.uf,
        tipo=endereco.tipo,
        numero=endereco.numero or '',
        complemento=endereco.complemento or '',
        cep=endereco.cep or '',
        class_infra_fisica=getattr(endereco, 'class_infra_fisica', None),
        latitude=endereco.latitude,
        longitude=endereco.longitude,
        compartilhado=False,  # Valor fixo para o campo problemático
    )


@router.get('/por-codigo/{codigo_endereco}')
async def buscar_por_codigo(
    codigo_endereco: str,
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
    load_relations: LoadRelationsDep,
) -> Union[EnderecoRead, EnderecoReadComplete]:
    """
    Busca um endereço pelo código único

    * Requer autenticação
    * O código do endereço é um identificador único por endereço
    * Opcionalmente carrega dados relacionados como operadoras e detentora
    * Registra a busca para fins de auditoria
    * Retorna EnderecoReadComplete quando load_relations=True, caso contrário
    * EnderecoRead
    """
    logger = logging.getLogger(__name__)

    try:
        # Log para depuração
        logger.info(f'Buscando endereço com código: {codigo_endereco}')
        logger.info(
            f'Usuário autenticado: {current_user.id} ({current_user.telefone})'
        )

        # Buscar o endereço
        endereco = await _buscar_endereco(
            codigo_endereco, load_relations, session
        )

        if not endereco:
            logger.warning(f'Endereço não encontrado: {codigo_endereco}')
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Endereço com código '{codigo_endereco}' não encontrado"
                ),
            )

        # Log para depuração
        logger.info(f'Endereço encontrado ID: {endereco.id}')

        # Registrar a busca para auditoria
        await _registrar_busca(session, current_user.id, codigo_endereco)

        # Criar resposta de acordo com o tipo solicitado
        if not load_relations:
            return _criar_endereco_basico(endereco)

        # Criar objeto completo com relações
        result = EnderecoReadComplete(
            **_criar_endereco_basico(endereco).dict(),
            operadoras=[],
            detentora=None,
            anotacoes=[],
        )

        # Adicionar operadoras se disponíveis
        if hasattr(endereco, 'operadoras') and endereco.operadoras:
            operadoras_list = []
            for eo in endereco.operadoras:
                if eo.operadora is not None:
                    operadoras_list.append(
                        OperadoraRead(
                            id=eo.operadora.id,
                            codigo=eo.operadora.codigo,
                            nome=eo.operadora.nome,
                        )
                    )
            result.operadoras = operadoras_list

        # Adicionar detentora se disponível
        if hasattr(endereco, 'detentora') and endereco.detentora:
            det = endereco.detentora
            result.detentora = DetentoraRead(
                id=det.id,
                codigo=det.codigo,
                nome=det.nome,
                telefone_noc=det.telefone_noc,
            )

        # Processar anotações
        if hasattr(endereco, 'anotacoes') and endereco.anotacoes:
            result.anotacoes = await _processar_anotacoes(
                endereco, current_user, session
            )

        return result

    except AttributeError as e:
        # Se houver erro ao acessar atributos do objeto desvinculado
        logger.error(f'Erro ao acessar atributos: {str(e)}')
        logger.error(f'Tipo de current_user: {type(current_user)}')

        if hasattr(current_user, '__dict__'):
            logger.error(f'Atributos disponíveis: {current_user.__dict__}')

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Não foi possível identificar o usuário autenticado.',
        )
    except Exception as e:
        # Log para qualquer outro erro não previsto
        logger.error(
            f'Erro não tratado na busca por código: {str(e)}', exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro ao processar a requisição: {str(e)}',
        )


@router.get(
    '/por-operadora/{codigo_operadora}',
    response_model=List[EnderecoReadComplete],
)
async def buscar_por_operadora(
    codigo_operadora: str,
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
):
    """
    Lista endereços de uma operadora específica

    * Requer autenticação
    * Busca pelo código da operadora (usando ILIKE para correspondência parcial
      insensível a maiúsculas/minúsculas)
    * Os resultados são paginados
    * Registra a busca para fins de auditoria
    * Retorna as operadoras associadas a cada endereço apenas com código e nome
    """
    logger = logging.getLogger(__name__)
    logger.info(
        f'Buscando endereços para operadora com código: {codigo_operadora}'
    )

    try:
        # Acesso direto ao ID é seguro pois current_user é um
        # objeto desvinculado
        usuario_id = current_user.id

        # Consulta modificada - usando ILIKE para busca parcial do código
        # insensível a maiúsculas/minúsculas
        stmt = (
            select(Endereco)
            .join(EnderecoOperadora)
            .where(
                EnderecoOperadora.codigo_operadora.ilike(
                    f'%{codigo_operadora}%'
                )
            )
            .offset(skip)
            .limit(limit)
            .options(
                selectinload(Endereco.operadoras).selectinload(
                    EnderecoOperadora.operadora
                ),
                selectinload(Endereco.detentora),
                selectinload(Endereco.anotacoes).selectinload(
                    Anotacao.usuario
                ),
            )
        )

        result = await session.scalars(stmt)
        enderecos = list(result)
        logger.info(f'Número de endereços encontrados: {len(enderecos)}')

        # Registrar a busca para auditoria
        busca_log = BuscaLog(
            usuario_id=usuario_id,
            endpoint='/enderecos/operadora/{codigo}',
            parametros=f'codigo={codigo_operadora}',
            tipo_busca=TipoBusca.por_operadora,
        )
        session.add(busca_log)
        await session.commit()

        # Precisamos processar manualmente os resultados para incluir
        # o código_operadora
        resultados = []

        for endereco in enderecos:
            # Criar o objeto base de endereço
            endereco_result = EnderecoReadComplete(
                id=endereco.id,
                codigo_endereco=endereco.codigo_endereco,
                logradouro=endereco.logradouro,
                bairro=endereco.bairro,
                municipio=endereco.municipio,
                uf=endereco.uf,
                tipo=endereco.tipo,
                numero=endereco.numero or '',
                complemento=endereco.complemento or '',
                cep=endereco.cep or '',
                class_infra_fisica=getattr(
                    endereco, 'class_infra_fisica', None
                ),
                latitude=endereco.latitude,
                longitude=endereco.longitude,
                compartilhado=getattr(endereco, 'compartilhado', False),
                operadoras=[],
                detentora=None,
                anotacoes=[],
            )

            # Adicionar operadoras com seus códigos específicos - usando
            # apenas nome e codigo_operadora
            if hasattr(endereco, 'operadoras') and endereco.operadoras:
                operadoras_list = []
                for eo in endereco.operadoras:
                    if eo.operadora is not None:
                        # Usando o modelo simplificado com apenas nome
                        # e codigo_operadora
                        op = OperadoraSimples(
                            nome=eo.operadora.nome,
                            codigo=eo.operadora.codigo,
                            codigo_operadora=eo.codigo_operadora,
                        )
                        operadoras_list.append(op)
                endereco_result.operadoras = operadoras_list

            # Adicionar detentora se disponível
            if hasattr(endereco, 'detentora') and endereco.detentora:
                det = endereco.detentora
                endereco_result.detentora = DetentoraRead(
                    id=det.id,
                    codigo=det.codigo,
                    nome=det.nome,
                    telefone_noc=det.telefone_noc,
                )

            # Processar anotações se necessário
            if hasattr(endereco, 'anotacoes') and endereco.anotacoes:
                anotacoes_filtradas = await filtrar_anotacoes_por_acesso(
                    endereco.anotacoes, current_user, session
                )
                anotacoes_resumidas = []

                for a in anotacoes_filtradas:
                    if hasattr(a, 'usuario') and a.usuario:
                        autor = AutorAnotacao(
                            id=a.usuario.id,
                            nome=a.usuario.nome or a.usuario.telefone,
                        )
                        anotacao_resumida = AnotacaoResumida(
                            id=a.id,
                            texto=a.texto,
                            data_hora=a.data_criacao,
                            autor=autor,
                        )
                        anotacoes_resumidas.append(anotacao_resumida)

                endereco_result.anotacoes = anotacoes_resumidas

            resultados.append(endereco_result)

        return resultados

    except AttributeError as e:
        # Se houver erro ao acessar atributos do objeto desvinculado
        logger.error(f'Erro ao acessar atributos de current_user: {str(e)}')

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Não foi possível identificar o usuário autenticado.',
        )


@router.get(
    '/por-detentora/{codigo_detentora}', response_model=List[EnderecoRead]
)
async def buscar_por_detentora(
    codigo_detentora: str,
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
):
    """
    Lista endereços de uma detentora específica

    * Requer autenticação
    * Busca pelo código da detentora
    * Os resultados são paginados
    * Registra a busca para fins de auditoria
    """
    try:
        # Acesso direto ao ID é seguro pois current_user é um
        # objeto desvinculado
        usuario_id = current_user.id

        stmt = (
            select(Endereco)
            .join(Detentora)
            .where(Detentora.codigo == codigo_detentora)
            .offset(skip)
            .limit(limit)
            .options(
                selectinload(Endereco.operadoras).selectinload(
                    EnderecoOperadora.operadora
                ),
                selectinload(Endereco.detentora),
            )
        )

        result = await session.scalars(stmt)
        enderecos = list(result)

        # Registrar a busca para auditoria
        busca_log = BuscaLog(
            usuario_id=usuario_id,
            endpoint='/enderecos/detentora/{codigo}',
            parametros=f'codigo={codigo_detentora}',
            tipo_busca=TipoBusca.por_detentora,
        )
        session.add(busca_log)
        await session.commit()

        return enderecos

    except AttributeError as e:
        # Se houver erro ao acessar atributos do objeto desvinculado
        logger = logging.getLogger(__name__)
        logger.error(f'Erro ao acessar atributos de current_user: {str(e)}')

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Não foi possível identificar o usuário autenticado.',
        )
