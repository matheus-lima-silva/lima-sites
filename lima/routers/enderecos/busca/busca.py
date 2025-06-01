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
    Anotacao,
    BuscaLog,
    Detentora,
    Endereco,
    EnderecoOperadora,
    NivelAcesso,
    TipoBusca,
    Usuario,
)
from ....schemas import (
    AnotacaoResumida,  # Adicionado
    AutorAnotacao,  # Adicionado
    DetentoraRead,  # Adicionado
    EnderecoRead,
    EnderecoReadComplete,
    OperadoraRead,
)
from ....utils.dependencies import AsyncSessionDep, CurrentUserDep

router = APIRouter()


def load_relations_query(
    load_relations: bool = Query(
        False, description='Carregar dados relacionados'
    ),
) -> bool:
    return load_relations


LoadRelationsDep = Annotated[bool, Depends(load_relations_query)]


async def _buscar_endereco(
    codigo_endereco: str, load_relations: bool, session: AsyncSession
) -> Endereco | None:  # Alterado para retornar None se não encontrado
    """Helper function to query the endereco"""
    query = select(Endereco).where(Endereco.codigo_endereco == codigo_endereco)
    if load_relations:
        query = query.options(
            selectinload(Endereco.operadoras).selectinload(
                EnderecoOperadora.operadora
            ),
            selectinload(Endereco.detentora),
            selectinload(Endereco.alteracoes),
            selectinload(Endereco.anotacoes).selectinload(
                Anotacao.usuario  # Eager load Usuario related to Anotacao
            ),
        )
    return await session.scalar(query)


async def _registrar_busca(
    session: AsyncSession,
    usuario_id: int,
    endpoint: str,
    parametros: str,
    tipo_busca: TipoBusca,
) -> None:
    """Helper function to register the search log"""
    busca_log = BuscaLog(
        usuario_id=usuario_id,
        endpoint=endpoint,
        parametros=parametros,
        tipo_busca=tipo_busca,
    )
    session.add(busca_log)
    # Commit é feito no final da rota principal para atomicidade


async def _processar_anotacoes(
    endereco: Endereco, current_user: Usuario
) -> List[AnotacaoResumida]:
    """Helper function to process annotations"""
    anotacoes_resumidas = []
    anotacoes_a_processar = endereco.anotacoes or []

    # Filtrar por nível de acesso
    if current_user.nivel_acesso == NivelAcesso.basico:
        anotacoes_filtradas = [
            a for a in anotacoes_a_processar if a.id_usuario == current_user.id
        ]
    else:
        anotacoes_filtradas = anotacoes_a_processar

    for a in anotacoes_filtradas:
        if a.usuario:  # Usuário deve estar pré-carregado
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
        # else:
        #     logger.warning(
        #         f"Anotação {a.id} sem usuário carregado."
        #     )  # Opcional
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
        # Corrigido para usar getattr com None como padrão se o atributo
        # não existir
        class_infra_fisica=getattr(endereco, 'class_infra_fisica', None),
        latitude=endereco.latitude,
        longitude=endereco.longitude,
        # Corrigido para usar getattr com False como padrão
        compartilhado=getattr(endereco, 'compartilhado', False),
    )


async def _formatar_operadoras_endereco(
    operadoras_endereco: List[EnderecoOperadora],
) -> List[OperadoraRead]:
    """Formata os dados das operadoras para a resposta."""
    operadoras_formatadas = []
    if operadoras_endereco:
        for eo in operadoras_endereco:
            if eo.operadora:  # Checa se operadora existe
                # TODO: Revisar o schema OperadoraRead, pois codigo_operadora
                # não parece pertencer a ele.
                # No entanto, mantendo a lógica original por enquanto.
                op_data = {
                    "id": eo.operadora.id,
                    "codigo": eo.operadora.codigo,
                    "nome": eo.operadora.nome,
                    "codigo_operadora": eo.codigo_operadora,
                }
                operadoras_formatadas.append(OperadoraRead(**op_data))
    return operadoras_formatadas


@router.get('/por-codigo/{codigo_endereco}')
async def buscar_por_codigo(
    codigo_endereco: str,
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
    load_relations: LoadRelationsDep,
) -> Union[EnderecoRead, EnderecoReadComplete]:
    logger = logging.getLogger(__name__)
    try:
        logger.info(
            f'Buscando endereço: {codigo_endereco}, '
            f'load_relations: {load_relations}'
        )
        endereco = await _buscar_endereco(
            codigo_endereco, load_relations, session
        )

        if not endereco:
            logger.warning(f'Endereço não encontrado: {codigo_endereco}')
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Endereço '{codigo_endereco}' não encontrado",
            )

        await _registrar_busca(
            session,
            current_user.id,
            endpoint='/enderecos/por-codigo/{codigo_endereco}',
            parametros=f'codigo_endereco={codigo_endereco},load_relations={load_relations}',
            tipo_busca=TipoBusca.por_id,
        )

        if not load_relations:
            response_data = _criar_endereco_basico(endereco)
        else:
            base_data = _criar_endereco_basico(endereco).model_dump()
            operadoras_list = []
            if endereco.operadoras:
                for eo in endereco.operadoras:
                    if eo.operadora:
                        operadoras_list.append(
                            OperadoraRead.model_validate(eo.operadora)
                        )

            detentora_data = None
            if endereco.detentora:
                detentora_data = DetentoraRead.model_validate(
                    endereco.detentora
                )

            anotacoes_data = await _processar_anotacoes(endereco, current_user)

            response_data = EnderecoReadComplete(
                **base_data,
                operadoras=operadoras_list,
                detentora=detentora_data,
                anotacoes=anotacoes_data,
            )

        await session.commit()  # Commit após todas as operações de DB
        return response_data

    except AttributeError as e:
        logger.error(
            f'Erro de atributo em buscar_por_codigo: {e}', exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Erro ao processar dados do usuário.',
        )
    except Exception as e:
        logger.error(f'Erro em buscar_por_codigo: {e}', exc_info=True)
        await session.rollback()  # Rollback em caso de erro
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Erro interno ao buscar endereço por código.',
        )


@router.get(
    '/por-operadora/{codigo_operadora}',
    response_model=List[EnderecoReadComplete],
)
async def buscar_por_operadora(
    codigo_operadora: str,
    current_user: CurrentUserDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
):
    logger = logging.getLogger(__name__)
    async with get_async_session() as session:
        try:
            logger.info(
                f'Buscando por operadora: {codigo_operadora}, '
                f'skip: {skip}, limit: {limit}'
            )
            stmt = (
                select(Endereco)
                .join(Endereco.operadoras)
                # Junta Endereco com EnderecoOperadora
                # (através do relacionamento 'operadoras')
                .where(
                    EnderecoOperadora.codigo_operadora.ilike(
                        f'%{codigo_operadora}%'
                    )
                )  # MODIFICADO AQUI
                .offset(skip)
                .limit(limit)
                .options(
                    selectinload(Endereco.operadoras).selectinload(
                        EnderecoOperadora.operadora
                    ),
                    # Mantemos o selectinload para carregar os dados
                    # da operadora
                    selectinload(Endereco.detentora),
                    selectinload(Endereco.anotacoes).selectinload(
                        Anotacao.usuario
                    ),
                )
                .distinct()
            )

            db_result = await session.scalars(stmt)
            enderecos = list(db_result.all())  # Usar .all() para obter a lista

            await _registrar_busca(
                session,
                current_user.id,
                endpoint='/enderecos/por-operadora/{codigo_operadora}',
                parametros=f'codigo_operadora={codigo_operadora},skip={skip},limit={limit}',
                tipo_busca=TipoBusca.por_operadora,
            )

            resultados_finais = []
            for end_item in enderecos:
                base_data = _criar_endereco_basico(end_item).model_dump()

                # Utiliza a nova função auxiliar
                operadoras_formatadas = await _formatar_operadoras_endereco(
                    end_item.operadoras
                )

                detentora_formatada = None
                if end_item.detentora:
                    detentora_formatada = DetentoraRead.model_validate(
                        end_item.detentora
                    )

                anotacoes_formatadas = await _processar_anotacoes(
                    end_item, current_user
                )

                resultados_finais.append(
                    EnderecoReadComplete(
                        **base_data,
                        operadoras=operadoras_formatadas,
                        detentora=detentora_formatada,
                        anotacoes=anotacoes_formatadas,
                    )
                )

            await session.commit()
            return resultados_finais

        except AttributeError as e:
            logger.error(
                f'Erro de atributo em buscar_por_operadora: {e}', exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Erro ao processar dados do usuário.',
            )
        except Exception as e:
            logger.error(f'Erro em buscar_por_operadora: {e}', exc_info=True)
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Erro interno ao buscar endereços por operadora.',
            )


@router.get(
    '/por-detentora/{codigo_detentora}', response_model=List[EnderecoRead]
)
async def buscar_por_detentora(
    codigo_detentora: str,
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
    skip: Annotated[int, Query(ge=0)] = 0,  # Corrigido aqui
    limit: Annotated[int, Query(ge=1, le=500)] = 100,  # Corrigido aqui
):
    logger = logging.getLogger(__name__)
    try:
        logger.info(
            f'Buscando por detentora: {codigo_detentora}, '
            f'skip: {skip}, limit: {limit}'
        )
        # Não precisamos de selectinload aqui, pois EnderecoRead não usa
        # operadoras ou anotações diretamente.
        # Apenas o relacionamento com Detentora é necessário para o filtro.
        stmt = (
            select(Endereco)
            .join(Endereco.detentora)  # Junção explícita com Detentora
            .where(Detentora.codigo.ilike(f'%{codigo_detentora}%'))
            .offset(skip)
            .limit(limit)
            .distinct()  # Evitar duplicatas de Endereco
        )

        db_result = await session.scalars(stmt)
        enderecos = list(db_result.all())  # Usar .all() para obter a lista

        await _registrar_busca(
            session,
            current_user.id,
            endpoint='/enderecos/por-detentora/{codigo_detentora}',
            parametros=f'codigo_detentora={codigo_detentora},skip={skip},limit={limit}',
            tipo_busca=TipoBusca.por_detentora,
        )

        # Mapeia diretamente para EnderecoRead, pois não há campos complexos
        # que exijam processamento adicional como em buscar_por_operadora
        resultados_finais = [
            _criar_endereco_basico(end_item) for end_item in enderecos
        ]

        await session.commit()
        return resultados_finais

    except AttributeError as e:
        logger.error(
            f'Erro de atributo em buscar_por_detentora: {e}', exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Erro ao processar dados do usuário.',
        )
    except Exception as e:
        logger.error(f'Erro em buscar_por_detentora: {e}', exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Erro interno ao buscar endereços por detentora.',
        )
