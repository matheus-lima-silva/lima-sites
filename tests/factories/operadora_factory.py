import factory
from factory.alchemy import SQLAlchemyModelFactory
from factory.faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from lima.models import Operadora


class OperadoraFactory(SQLAlchemyModelFactory):
    """Factory para criar instâncias do modelo Operadora para testes."""

    class Meta:
        model = Operadora
        sqlalchemy_session_persistence = 'flush'

    codigo = factory.Sequence(lambda n: f'OPR-{n:06d}')
    nome = Faker('company')

    @classmethod
    async def create_async(cls, session: AsyncSession, **kwargs):
        """
        Cria e persiste uma operadora de forma assíncrona.
        """
        operadora = await session.run_sync(
            lambda sync_sess: cls.create(session=sync_sess, **kwargs)
        )
        await session.commit()
        await session.refresh(operadora)
        return operadora
