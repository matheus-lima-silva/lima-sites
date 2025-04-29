"""
Operações básicas para manipulação de endereços.
"""

from typing import Annotated, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...database import get_async_session
from ...models import (
    Alteracao,
    BuscaLog,
    Detentora,
    Endereco,
    EnderecoOperadora,
    Operadora,
    TipoAlteracao,
    TipoBusca,
    Usuario,
)
from ...schemas import (
    EnderecoCreate,
    EnderecoRead,
    EnderecoReadComplete,
    EnderecoUpdate,
)
from ...security import (
    get_current_user,
    require_intermediario,
    require_super_usuario,
)
from .utils import endereco_to_schema, filtrar_anotacoes_por_acesso

router = APIRouter()

# Definições de dependências usando Annotated
AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]
CurrentUserDep = Annotated[Usuario, Depends(get_current_user)]
IntermediarioUserDep = Annotated[Usuario, Depends(require_intermediario)]
SuperUserDep = Annotated[Usuario, Depends(require_super_usuario)]


# Corrigindo a definição do parâmetro Query com função auxiliar
def load_relations_query(load_relations: bool = Query(False,
                                 description='Carregar dados relacionados')):
    return load_relations


LoadRelationsDep = Annotated[bool, Depends(load_relations_query)]


@router.post(
    '/', response_model=EnderecoRead, status_code=status.HTTP_201_CREATED
)
async def criar_endereco(
    endereco: EnderecoCreate,
    session: AsyncSessionDep,
    current_user: IntermediarioUserDep,
):
    """
    Cria um novo endereço no sistema

    * Requer nível de acesso intermediário ou superior
    * Permite associar operadoras e detentora ao criar o endereço
    * O código de endereço precisa ser único e pode ser alfanumérico
    """
    # Verificar se já existe um endereço com este código
    existing_endereco = await session.scalar(
        select(Endereco).where(
            Endereco.codigo_endereco == endereco.codigo_endereco
        )
    )

    if existing_endereco:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe um endereço com o código '{
                endereco.codigo_endereco
            }'",
        )

    try:
        # Cria o novo endereço
        db_endereco = Endereco(
            codigo_endereco=endereco.codigo_endereco,
            logradouro=endereco.logradouro,
            bairro=endereco.bairro,
            municipio=endereco.municipio,
            uf=endereco.uf,
            tipo=endereco.tipo,
            numero=endereco.numero,
            complemento=endereco.complemento,
            cep=endereco.cep,
            latitude=endereco.latitude,
            longitude=endereco.longitude,
            compartilhado=endereco.compartilhado,
        )

        session.add(db_endereco)

        # Se houver detentora, processa-a
        if endereco.detentora:
            # Verifica se a detentora já existe
            detentora = await session.scalar(
                select(Detentora).where(
                    Detentora.codigo == endereco.detentora.id
                )
            )

            # Se não existe, cria uma nova
            if not detentora:
                detentora = Detentora(
                    codigo=endereco.detentora.id,
                    nome=endereco.detentora.nome,
                    telefone_noc=endereco.detentora.telefone_noc,
                )
                session.add(detentora)
                await session.flush()  # Para obter o ID da detentora

            # Associa a detentora ao endereço
            db_endereco.detentora_id = detentora.id

        # Processa as operadoras
        if endereco.operadoras:
            for op_data in endereco.operadoras:
                # Verifica se a operadora já existe
                operadora = await session.scalar(
                    select(Operadora).where(Operadora.codigo == op_data.id)
                )

                # Se não existe, cria uma nova
                if not operadora:
                    operadora = Operadora(codigo=op_data.id, nome=op_data.nome)
                    session.add(operadora)
                    await session.flush()  # Para obter o ID da operadora

                # Cria a associação entre endereço e operadora
                endereco_operadora = EnderecoOperadora(
                    endereco_id=db_endereco.id,
                    operadora_id=operadora.id,
                    codigo_operadora=op_data.id,
                )
                session.add(endereco_operadora)

        await session.commit()
        await session.refresh(db_endereco)

        return db_endereco
    except Exception as e:
        await session.rollback()
        # Verificar se é um erro de constraint violation
        error_message = str(e)
        if (
            'violates unique constraint' in error_message
            or 'UNIQUE constraint failed' in error_message
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f'Já existe um endereço com algum atributo único '
                f'duplicado:{error_message}',
            )
        # Para outros erros, relança a exceção
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro ao criar endereço: {error_message}',
        )


@router.get('/{endereco_id}')
async def obter_endereco(
    endereco_id: int,
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
    load_relations: LoadRelationsDep,
) -> Union[EnderecoRead, EnderecoReadComplete]:
    """
    Recupera detalhes de um endereço específico

    * Requer autenticação
    * Todos os usuários podem consultar endereços
    * Permite carregar dados relacionados (anotações, operadoras, detentora)
    """
    if load_relations:
        stmt = (
            select(Endereco)
            .where(Endereco.id == endereco_id)
            .options(
                selectinload(Endereco.anotacoes).selectinload(
                    Endereco.anotacoes.and_(Usuario)
                ),
                selectinload(Endereco.alteracoes),
                selectinload(Endereco.operadoras).selectinload(
                    EnderecoOperadora.operadora
                ),
                selectinload(Endereco.detentora),
            )
        )
    else:
        stmt = select(Endereco).where(Endereco.id == endereco_id)

    endereco = await session.scalar(stmt)

    if not endereco:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Endereço não encontrado',
        )

    # Registrar a busca para auditoria
    busca_log = BuscaLog(
        usuario_id=current_user.id,
        endpoint='/enderecos/{id}',
        parametros=f'id={endereco_id}',
        tipo_busca=TipoBusca.por_id,
    )
    session.add(busca_log)

    # Filtra e processa anotações
    anotacoes_resumidas = []
    if load_relations:
        anotacoes_resumidas = await filtrar_anotacoes_por_acesso(
            endereco, current_user, session
        )

    await session.commit()

    # Retorna o endereço com base no parâmetro include_relations
    if load_relations:
        return endereco_to_schema(
            endereco,
            include_relations=True,
            anotacoes_resumidas=anotacoes_resumidas,
        )

    return endereco_to_schema(endereco, include_relations=False)


@router.put('/{endereco_id}', response_model=EnderecoRead)
async def atualizar_endereco(
    endereco_id: int,
    endereco_update: EnderecoCreate,
    session: AsyncSessionDep,
    current_user: IntermediarioUserDep,
):
    """
    Atualiza um endereço existente
    * Requer nível de acesso intermediário ou superior
    * Permite atualizar operadoras e detentora associadas ao endereço
    * O código de endereço precisa ser único e pode ser alfanumérico
    """
    # Verifica se o endereço existe
    db_endereco = await session.get(Endereco, endereco_id)
    if not db_endereco:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Endereço não encontrado',
        )

    # Verifica se está tentando utilizar
    # um código que já existe em outro endereço
    if db_endereco.codigo_endereco != endereco_update.codigo_endereco:
        existing_endereco = await session.scalar(
            select(Endereco).where(
                and_(
                    Endereco.codigo_endereco
                    == endereco_update.codigo_endereco,
                    Endereco.id != endereco_id,
                )
            )
        )

        if existing_endereco:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f'Já existe outro endereço com o código '
                    f"'{endereco_update.codigo_endereco}'"
                ),
            )

    try:
        async with session.begin_nested():
            # Atualiza os campos básicos do endereço
            for field, value in endereco_update.model_dump(
                exclude={'operadoras', 'detentora'}
            ).items():
                setattr(db_endereco, field, value)

            # Atualiza a detentora se fornecida
            await _processar_detentora(
                session, db_endereco, endereco_update.detentora
            )

            # Atualiza as operadoras
            if endereco_update.operadoras is not None:
                await _atualizar_operadoras(
                    session, db_endereco.id, endereco_update.operadoras
                )

        # Registra a alteração no histórico
        alteracao = Alteracao(
            id_endereco=db_endereco.id,
            id_usuario=current_user.id,
            tipo_alteracao=TipoAlteracao.modificacao,
            detalhe='Atualização completa via endpoint PUT',
        )
        session.add(alteracao)
        # Commit fora do bloco begin_nested para aplicar as alterações
        await session.commit()
        await session.refresh(db_endereco)

        return db_endereco
    except Exception as e:
        await session.rollback()
        # Verificar se é um erro de constraint violation
        error_message = str(e)
        if (
            'violates unique constraint' in error_message
            or 'UNIQUE constraint failed' in error_message
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f'Conflito ao atualizar o endereço: {error_message}',
            )
        # Relança o erro original
        if isinstance(e, HTTPException):
            raise e
        # Para outros erros, cria uma HTTP exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro ao atualizar endereço: {error_message}',
        )


# Funções auxiliares para reutilização de código
async def _processar_detentora(session, endereco, detentora_data):
    """Processa a atualização ou remoção de uma detentora de um endereço"""
    if detentora_data is None:
        endereco.detentora_id = None
        return

    # Verifica se a detentora já existe
    detentora = await session.scalar(
        select(Detentora).where(Detentora.codigo == detentora_data.id)
    )

    # Se não existe, cria uma nova
    if not detentora:
        detentora = Detentora(
            codigo=detentora_data.id,
            nome=detentora_data.nome,
            telefone_noc=detentora_data.telefone_noc,
        )
        session.add(detentora)
        await session.flush()  # Para obter o ID da detentora

    # Associa a detentora ao endereço
    endereco.detentora_id = detentora.id


async def _atualizar_operadoras(session, endereco_id, operadoras_data):
    """Atualiza as operadoras associadas a um endereço"""
    # Remove todas as associações atuais usando ORM
    await session.execute(
        select(EnderecoOperadora)
        .where(EnderecoOperadora.endereco_id == endereco_id)
        .execution_options(synchronize_session='fetch')
    )

    # Adiciona as novas associações
    for op_data in operadoras_data:
        # Verifica se a operadora já existe
        operadora = await session.scalar(
            select(Operadora).where(Operadora.codigo == op_data.id)
        )

        # Se não existe, cria uma nova
        if not operadora:
            operadora = Operadora(codigo=op_data.id, nome=op_data.nome)
            session.add(operadora)
            await session.flush()

        # Cria a associação entre endereço e operadora
        endereco_operadora = EnderecoOperadora(
            endereco_id=endereco_id,
            operadora_id=operadora.id,
            codigo_operadora=op_data.id,
        )
        session.add(endereco_operadora)


@router.patch('/{endereco_id}', response_model=EnderecoRead)
async def atualizar_endereco_parcial(
    endereco_id: int,
    endereco_update: EnderecoUpdate,
    session: AsyncSessionDep,
    current_user: IntermediarioUserDep,
):
    """
    Atualiza parcialmente um endereço existente

    * Requer nível de acesso intermediário ou superior
    * Permite atualizar apenas os campos fornecidos no corpo da requisição
    * Se não fornecidos, os campos mantêm seus valores atuais
    * Suporta atualização de operadoras e detentora
    """
    # Verifica se o endereço existe
    db_endereco = await session.get(Endereco, endereco_id)
    if not db_endereco:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Endereço não encontrado',
        )

    # Verifica colisão de código_endereco apenas se este campo for atualizado
    await _verificar_codigo_endereco_unico(
        session, db_endereco, endereco_update.codigo_endereco
    )

    try:
        async with session.begin_nested():
            # Atualiza os campos básicos do endereço
            update_data = endereco_update.model_dump(
                exclude_unset=True, exclude={'operadoras', 'detentora'}
            )

            # Atualiza apenas os campos não nulos
            for field, value in update_data.items():
                if value is not None:
                    setattr(db_endereco, field, value)

            # Atualiza a detentora se fornecida
            if endereco_update.detentora is not None:
                await _processar_detentora(
                    session, db_endereco, endereco_update.detentora
                )

            # Atualiza as operadoras se fornecidas
            if endereco_update.operadoras is not None:
                await _atualizar_operadoras(
                    session, db_endereco.id, endereco_update.operadoras
                )

        # Registra a alteração no histórico
        alteracao = Alteracao(
            id_endereco=db_endereco.id,
            id_usuario=current_user.id,
            tipo_alteracao=TipoAlteracao.modificacao,
            detalhe=f'Atualização parcial via endpoint PATCH: '
            f'{", ".join(update_data.keys())}',
        )
        session.add(alteracao)
        await session.flush()
        # Commit fora do bloco begin_nested para aplicar as alterações
        await session.commit()
        await session.refresh(db_endereco)

        return db_endereco
    except Exception as e:
        await session.rollback()
        await _tratar_erro_atualizacao(e)


# Função auxiliar para verificar se o código de endereço é único
async def _verificar_codigo_endereco_unico(session, endereco, novo_codigo):
    """Verifica se o código de endereço
    é único (excluindo o próprio endereço)"""
    if novo_codigo is None or novo_codigo == endereco.codigo_endereco:
        return

    existing_endereco = await session.scalar(
        select(Endereco).where(
            and_(
                Endereco.codigo_endereco == novo_codigo,
                Endereco.id != endereco.id,
            )
        )
    )

    if existing_endereco:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe outro endereço com o código '{novo_codigo}'",
        )


# Função auxiliar para tratar erros em atualizações
async def _tratar_erro_atualizacao(e):
    """Trata erros durante atualizações de endereços"""
    error_message = str(e)

    # Verificar se é um erro de constraint violation
    if (
        'violates unique constraint' in error_message
        or 'UNIQUE constraint failed' in error_message
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Conflito ao atualizar o endereço: {error_message}',
        )

    # Relança o erro original se for um HTTP Exception
    if isinstance(e, HTTPException):
        raise e

    # Para outros erros, cria uma HTTP exception
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f'Erro ao atualizar endereço: {error_message}',
    )


@router.delete('/{endereco_id}', status_code=status.HTTP_204_NO_CONTENT)
async def deletar_endereco(
    endereco_id: int,
    session: AsyncSessionDep,
    current_user: SuperUserDep,
):
    """
    Remove um endereço do sistema

    * Requer nível de acesso super_usuario
    * Verifica e impede exclusão se houver dependências
    """
    async with session.begin():
        # Verificar dependências antes de excluir
        endereco = await session.get(Endereco, endereco_id)

        if not endereco:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Endereço não encontrado',
            )

        # Verificar dependências (usando recursos avançados do PostgreSQL)
        has_dependencies = await session.scalar(
            text("""
            SELECT EXISTS(
                SELECT 1 FROM buscas WHERE id_endereco = :id
                UNION ALL
                SELECT 1 FROM alteracoes WHERE id_endereco = :id
                UNION ALL
                SELECT 1 FROM anotacoes WHERE id_endereco = :id
                LIMIT 1
            )
            """),
            {'id': endereco_id},
        )

        if has_dependencies:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Não é possível remover este endereço'
                ' pois ele possui registros dependentes',
            )

        # Remove as associações com operadoras
        await session.execute(
            text(
                'DELETE FROM endereco_operadora WHERE'
                ' endereco_id = :endereco_id'
            ),
            {'endereco_id': endereco_id},
        )

        # Remove o endereço
        await session.delete(endereco)

    # O commit está implícito pelo contexto do begin()
