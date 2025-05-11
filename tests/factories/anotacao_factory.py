import factory
from factory.alchemy import SQLAlchemyModelFactory
from factory.faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from lima.models import Anotacao

from .endereco_factory import EnderecoFactory
from .usuario_factory import UsuarioFactory


class AnotacaoFactory(SQLAlchemyModelFactory):
    """Factory para criar instâncias do modelo Anotacao para testes."""

    class Meta:
        model = Anotacao
        sqlalchemy_session_persistence = 'flush'

    texto = Faker('paragraph')
    id_usuario = factory.SelfAttribute('usuario.id', default=None)
    id_endereco = factory.SelfAttribute('endereco.id', default=None)

    @classmethod
    async def create_async(
        cls, session: AsyncSession, usuario=None, endereco=None, **kwargs
    ):
        """
        Cria e persiste uma anotação de forma assíncrona.

        Args:
            session: Sessão assíncrona do SQLAlchemy
            usuario: Usuário que criou a anotação (opcional)
            endereco: Endereço associado à anotação (opcional)
            **kwargs: Atributos para sobrescrever os padrões da factory

        Returns:
            Anotacao: Instância persistida no banco de dados
        """
        if usuario is None:
            usuario = await UsuarioFactory.create_async(session)

        if endereco is None:
            endereco = await EnderecoFactory.create_async(session)

        kwargs['id_usuario'] = usuario.id
        kwargs['id_endereco'] = endereco.id

        # Gerar texto para a anotação se não fornecido
        if 'texto' not in kwargs:
            kwargs['texto'] = "Esta é uma anotação de teste"

        # Criar diretamente uma instância de Anotacao em vez de usar
        #  Factory Boy
        anotacao = Anotacao(
            id_usuario=kwargs['id_usuario'],
            id_endereco=kwargs['id_endereco'],
            texto=kwargs['texto']
        )

        # Adicionar à sessão e persistir
        session.add(anotacao)
        await session.commit()
        await session.refresh(anotacao)
        return anotacao
