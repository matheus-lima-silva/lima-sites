"""
Funções utilitárias para manipulação de endereços.
"""

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
    if not include_relations:
        # Se não precisa de relações, usa o schema básico
        return EnderecoRead(
            id=endereco.id,
            codigo_endereco=endereco.codigo_endereco,
            logradouro=endereco.logradouro,
            bairro=endereco.bairro,
            municipio=endereco.municipio,
            uf=endereco.uf,
            tipo=endereco.tipo,
            numero=endereco.numero,
            complemento=endereco.complemento,
            cep=endereco.cep,
            class_infra_fisica=getattr(endereco, 'class_infra_fisica', None),
            latitude=endereco.latitude,
            longitude=endereco.longitude,
            compartilhado=endereco.compartilhado,
        )
    else:
        # Dados básicos do endereço
        result = EnderecoReadComplete(
            id=endereco.id,
            codigo_endereco=endereco.codigo_endereco,
            logradouro=endereco.logradouro,
            bairro=endereco.bairro,
            municipio=endereco.municipio,
            uf=endereco.uf,
            tipo=endereco.tipo,
            numero=endereco.numero,
            complemento=endereco.complemento,
            cep=endereco.cep,
            class_infra_fisica=getattr(endereco, 'class_infra_fisica', None),
            latitude=endereco.latitude,
            longitude=endereco.longitude,
            compartilhado=endereco.compartilhado,
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
        current_user: O usuário atual
        session: A sessão do banco de dados

    Returns:
        List[AnotacaoResumida]: Lista de anotações já filtradas e formatadas
    """
    anotacoes_resumidas = []

    if not hasattr(endereco, 'anotacoes') or not endereco.anotacoes:
        return anotacoes_resumidas

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
                    id=usuario.id, nome=usuario.nome or usuario.telefone
                )
                anotacao_resumida = AnotacaoResumida(
                    id=a.id,
                    texto=a.texto,
                    data_hora=a.data_criacao,
                    # Usando data_criacao como data_hora
                    autor=autor,
                )
                anotacoes_resumidas.append(anotacao_resumida)

    return anotacoes_resumidas
