import random

import factory
from factory.alchemy import SQLAlchemyModelFactory
from factory.faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from lima.models import Alteracao, TipoAlteracao

from .endereco_factory import EnderecoFactory
from .usuario_factory import UsuarioFactory


class AlteracaoFactory(SQLAlchemyModelFactory):
    """Factory para criar instâncias do modelo Alteracao para testes."""

    class Meta:
        model = Alteracao
        sqlalchemy_session_persistence = 'flush'

    tipo_alteracao = factory.LazyFunction(
        lambda: random.choice(list(TipoAlteracao))
    )
    detalhe = Faker('paragraph')

    @classmethod
    async def create_async(
        cls, session: AsyncSession, usuario=None, endereco=None, **kwargs
    ):
        """
        Cria e persiste uma alteração de forma assíncrona.

        Args:
            session: Sessão assíncrona do SQLAlchemy
            usuario: Usuário que realizou a alteração (opcional)
            endereco: Endereço alterado (opcional)
            **kwargs: Atributos para sobrescrever os padrões da factory

        Returns:
            Alteracao: Instância persistida no banco de dados
        """
        if usuario is None:
            usuario = await UsuarioFactory.create_async(session)

        if endereco is None:
            endereco = await EnderecoFactory.create_async(session)

        kwargs['id_usuario'] = usuario.id
        kwargs['id_endereco'] = endereco.id

        alteracao = cls(**kwargs)
        session.add(alteracao)
        await session.commit()
        await session.refresh(alteracao)
        return alteracao


class AlteracaoAdicaoFactory(AlteracaoFactory):
    """Factory para criar alterações do tipo adição."""

    tipo_alteracao = TipoAlteracao.adicao


class AlteracaoModificacaoFactory(AlteracaoFactory):
    """Factory para criar alterações do tipo modificação."""

    tipo_alteracao = TipoAlteracao.modificacao


class AlteracaoRemocaoFactory(AlteracaoFactory):
    """Factory para criar alterações do tipo remoção."""

    tipo_alteracao = TipoAlteracao.remocao
