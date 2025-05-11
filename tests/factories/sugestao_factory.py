import random

import factory
from factory.alchemy import SQLAlchemyModelFactory
from factory.faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from lima.models import StatusSugestao, Sugestao, TipoSugestao

from .usuario_factory import UsuarioFactory


class SugestaoFactory(SQLAlchemyModelFactory):
    """Factory para criar instâncias do modelo Sugestao para testes."""

    class Meta:
        model = Sugestao
        sqlalchemy_session_persistence = 'flush'

    tipo_sugestao = factory.LazyFunction(
        lambda: random.choice(list(TipoSugestao))
    )
    status = StatusSugestao.pendente
    detalhe = Faker('paragraph')

    @classmethod
    async def create_async(
        cls, session: AsyncSession, usuario=None, endereco=None, **kwargs
    ):
        """
        Cria e persiste uma sugestão de forma assíncrona.

        Args:
            session: Sessão assíncrona do SQLAlchemy
            usuario: Usuário que fez a sugestão (opcional)
            endereco: Endereço associado à sugestão (opcional)
            **kwargs: Atributos para sobrescrever os padrões da factory

        Returns:
            Sugestao: Instância persistida no banco de dados
        """
        if usuario is None:
            usuario = await UsuarioFactory.create_async(session)
        kwargs['id_usuario'] = usuario.id
        if endereco is not None:
            kwargs['id_endereco'] = endereco.id
        sugestao = await session.run_sync(
            lambda sync_sess: cls.create(session=sync_sess, **kwargs)
        )
        await session.commit()
        await session.refresh(sugestao)
        return sugestao


class SugestaoAprovadaFactory(SugestaoFactory):
    """Factory para criar sugestões com status aprovado."""

    status = StatusSugestao.aprovado


class SugestaoRejeitadaFactory(SugestaoFactory):
    """Factory para criar sugestões com status rejeitado."""

    status = StatusSugestao.rejeitado
