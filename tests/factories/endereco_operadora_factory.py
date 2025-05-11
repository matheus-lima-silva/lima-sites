import factory
from factory.alchemy import SQLAlchemyModelFactory
from sqlalchemy.ext.asyncio import AsyncSession

from lima.models import EnderecoOperadora

from .endereco_factory import EnderecoFactory
from .operadora_factory import OperadoraFactory


class EnderecoOperadoraFactory(SQLAlchemyModelFactory):
    """Factory para criar instâncias do modelo
    EnderecoOperadora para testes."""

    class Meta:
        model = EnderecoOperadora
        sqlalchemy_session_persistence = 'flush'

    codigo_operadora = factory.Sequence(lambda n: f'COD-OP-{n:06d}')

    @classmethod
    async def create_async(
        cls, session: AsyncSession, endereco=None, operadora=None, **kwargs
    ):
        """
        Cria e persiste uma associação endereco-operadora de forma assíncrona.

        Args:
            session: Sessão assíncrona do SQLAlchemy
            endereco: Endereco a ser associado (opcional)
            operadora: Operadora a ser associada (opcional)
            **kwargs: Atributos para sobrescrever os padrões da factory

        Returns:
            EnderecoOperadora: Instância persistida no banco de dados
        """
        if endereco is None:
            endereco = await EnderecoFactory.create_async(session)

        if operadora is None:
            operadora = await OperadoraFactory.create_async(session)

        kwargs['endereco_id'] = endereco.id
        kwargs['operadora_id'] = operadora.id

        endereco_operadora = await session.run_sync(
            lambda sync_sess: cls.create(session=sync_sess, **kwargs)
        )
        await session.commit()
        await session.refresh(endereco_operadora)
        return endereco_operadora
