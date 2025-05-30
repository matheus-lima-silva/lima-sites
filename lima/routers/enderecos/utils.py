"""
Funções utilitárias para manipulação de endereços.
"""

import logging

from sqlalchemy import select

from ...models import NivelAcesso, Usuario
from ...schemas import (
    AnotacaoResumida,
    AutorAnotacao,
    DetentoraRead,
    EnderecoRead,
    EnderecoReadComplete,
    OperadoraRead,
)


def endereco_to_schema(
    endereco, include_relations=False, anotacoes_resumidas=None
):
    """
    Converte um objeto Endereco do ORM para um schema
      EnderecoRead ou EnderecoReadComplete

    Args:
        endereco: O objeto Endereco do SQLAlchemy
        include_relations: Se deve incluir relações
          (operadoras, detentora, anotações)
        anotacoes_resumidas: Lista formatada de anotações

    Returns:
        EnderecoRead ou EnderecoReadComplete: O objeto
          formatado para a resposta da API
    """
    # Extrair os dados básicos do endereço - comum aos dois schemas
    dados_basicos = {
        'id': endereco.id,
        'codigo_endereco': endereco.codigo_endereco,
        'logradouro': endereco.logradouro,
        'bairro': endereco.bairro,
        'municipio': endereco.municipio,
        'uf': endereco.uf,
        'tipo': endereco.tipo,
        'numero': endereco.numero,
        'complemento': endereco.complemento,
        'cep': endereco.cep,
        'class_infra_fisica': getattr(endereco, 'class_infra_fisica', None),
        'latitude': endereco.latitude,
        'longitude': endereco.longitude,
        'compartilhado': getattr(endereco, 'compartilhado', False),
    }

    if not include_relations:
        # Se não precisa de relações, usa o schema básico
        return EnderecoRead(**dados_basicos)
    else:
        # Criar o schema completo com os dados básicos
        result = EnderecoReadComplete(
            **dados_basicos,
            operadoras=[],
            detentora=None,
            anotacoes=[],
        )

        # Adicionar operadoras se disponíveis
        if hasattr(endereco, 'operadoras') and endereco.operadoras:
            result.operadoras = [
                OperadoraRead(
                    id=eo.operadora.id,
                    codigo=eo.operadora.codigo,
                    nome=eo.operadora.nome,
                    codigo_operadora=eo.codigo_operadora,  # Adicionado
                )
                for eo in endereco.operadoras
                if eo.operadora is not None
            ]

        # Adicionar detentora se disponível
        if hasattr(endereco, 'detentora') and endereco.detentora:
            result.detentora = DetentoraRead(
                id=endereco.detentora.id,
                codigo=endereco.detentora.codigo,
                nome=endereco.detentora.nome,
                telefone_noc=endereco.detentora.telefone_noc,
            )

        # Adicionar anotações se disponíveis
        if anotacoes_resumidas:
            result.anotacoes = anotacoes_resumidas

        return result


async def filtrar_anotacoes_por_acesso(endereco, current_user, session):
    """
    Filtra as anotações de um endereço com base no nível de acesso do usuário.

    Args:
        endereco: O objeto Endereco com as anotações carregadas
        current_user: O usuário atual (objeto desvinculado)
        session: A sessão do banco de dados

    Returns:
        List[AnotacaoResumida]: Lista de anotações resumidas filtradas por
         nível de acesso
    """
    logger = logging.getLogger(__name__)
    anotacoes_resumidas = []

    # Verificar se o endereço tem anotações
    if not hasattr(endereco, 'anotacoes') or not endereco.anotacoes:
        return anotacoes_resumidas

    try:
        # Debug log para verificar tipo de objetos
        logger.info(
            f'Filtrando anotações para usuário: {current_user.id}, '
            f'tipo: {type(current_user).__name__}'
        )
        logger.info(
            f'Endereço: {endereco.id}, tipo: {type(endereco).__name__}'
        )

        # Filtrar por nível de acesso
        usuario_id = current_user.id
        nivel_acesso = current_user.nivel_acesso

        # Aplicar filtragem baseada no nível de acesso
        anotacoes_filtradas = (
            [a for a in endereco.anotacoes if a.id_usuario == usuario_id]
            if nivel_acesso == NivelAcesso.basico
            else endereco.anotacoes
        )

        # Se não houver anotações após filtragem, retorna lista vazia
        if not anotacoes_filtradas:
            return anotacoes_resumidas

        # Processar anotações filtradas
        return await _processar_anotacoes_filtradas(
            anotacoes_filtradas, session
        )

    except AttributeError as e:
        # Se houver erro ao acessar atributos do objeto desvinculado
        logger.error(
            f'Erro ao acessar atributos em filtrar_anotacoes_por_acesso: '
            f'{str(e)}'
        )

        # Verifica qual objeto está causando o problema
        if 'compartilhado' in str(e):
            logger.error(
                "Erro relacionado ao atributo 'compartilhado' no endereço. "
                'Continuando sem esse campo.'
            )

        # Retorna lista vazia em caso de erro, para não bloquear o fluxo
        return []


async def _processar_anotacoes_filtradas(anotacoes_filtradas, session):
    """
    Função auxiliar para processar anotações filtradas e obter
     informações de usuários.

    Args:
        anotacoes_filtradas: Lista de anotações já filtradas
        session: Sessão do banco de dados

    Returns:
        List[AnotacaoResumida]: Lista de anotações resumidas
    """
    anotacoes_resumidas = []

    # Carregar os usuários relacionados às anotações
    usuario_ids = [a.id_usuario for a in anotacoes_filtradas]
    if not usuario_ids:
        return anotacoes_resumidas

    usuarios = await session.execute(
        select(Usuario).where(Usuario.id.in_(usuario_ids))
    )
    usuarios_dict = {u.id: u for u in usuarios.scalars().all()}

    # Converter para o formato esperado em AnotacaoResumida
    for a in anotacoes_filtradas:
        usuario = usuarios_dict.get(a.id_usuario)
        if usuario:
            autor = AutorAnotacao(
                id=usuario.id, nome=usuario.nome or usuario.telefone
            )
            anotacao_resumida = AnotacaoResumida(
                id=a.id,
                texto=a.texto,
                data_hora=a.data_criacao,  # Usando data_criacao como data_hora
                autor=autor,
            )
            anotacoes_resumidas.append(anotacao_resumida)

    return anotacoes_resumidas
