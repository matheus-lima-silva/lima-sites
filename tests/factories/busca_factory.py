from factory.alchemy import SQLAlchemyModelFactory
from factory.faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from lima.models import Busca

from .endereco_factory import EnderecoFactory
from .usuario_factory import UsuarioFactory


class BuscaFactory(SQLAlchemyModelFactory):
    """Factory para criar instâncias do modelo Busca para testes."""

    class Meta:
        model = Busca
        sqlalchemy_session_persistence = 'flush'

    info_adicional = Faker('sentence')

    @classmethod
    async def create_async(
        cls, session: AsyncSession, usuario=None, endereco=None, **kwargs
    ):
        """
        Cria e persiste uma busca de forma assíncrona.

        Args:
            session: Sessão assíncrona do SQLAlchemy
            usuario: Usuário que realizou a busca (opcional)
            endereco: Endereço que foi buscado (opcional)
            **kwargs: Atributos para sobrescrever os padrões da factory

        Returns:
            Busca: Instância persistida no banco de dados
        """
        if usuario is None:
            usuario = await UsuarioFactory.create_async(session)

        if endereco is None:
            endereco = await EnderecoFactory.create_async(session)

        kwargs['id_usuario'] = usuario.id
        kwargs['id_endereco'] = endereco.id

        # Gerar um texto informativo para o campo info_adicional se
        #  não fornecido
        if 'info_adicional' not in kwargs:
            kwargs['info_adicional'] = 'Informações sobre busca de teste'

        # Criamos diretamente uma instância de Busca ao invés de usar
        #  Factory Boy
        busca = Busca(
            id_usuario=kwargs['id_usuario'],
            id_endereco=kwargs['id_endereco'],
            info_adicional=kwargs['info_adicional'],
        )

        # Adicionamos a busca à sessão e persistimos
        session.add(busca)
        await session.commit()
        await session.refresh(busca)
        return busca
