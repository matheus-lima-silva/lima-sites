import random

from sqlalchemy.ext.asyncio import AsyncSession

from lima.models import NivelAcesso, Usuario


class UsuarioFactory:
    """Factory para criar instâncias do modelo Usuario para testes."""

    @classmethod
    async def create_async(cls, session: AsyncSession, **kwargs):
        """
        Cria e persiste um usuário de forma assíncrona.

        Args:
            session: Sessão assíncrona do SQLAlchemy
            **kwargs: Atributos para sobrescrever os valores padrão

        Returns:
            Usuario: Instância persistida no banco de dados
        """
        # Gerar um telefone único se não for fornecido
        telefone = kwargs.pop('telefone', cls._gerar_telefone())
        nome = kwargs.pop('nome', cls._gerar_nome())
        nivel_acesso = kwargs.pop('nivel_acesso', NivelAcesso.basico)

        # Criar o usuário - apenas com os campos esperados pelo construtor
        usuario = Usuario(
            telefone=telefone, nome=nome, nivel_acesso=nivel_acesso, **kwargs
        )

        # Persistir no banco de dados
        session.add(usuario)
        await session.commit()
        await session.refresh(usuario)
        return usuario

    @classmethod
    def build(cls, **kwargs):
        """
        Cria uma instância de Usuario sem persistir no banco de dados.
        Útil para testes unitários que não precisam de persistência.

        Args:
            **kwargs: Atributos para sobrescrever os valores padrão

        Returns:
            Usuario: Instância não persistida no banco de dados
        """
        # Gerar um telefone único se não for fornecido
        telefone = kwargs.pop('telefone', cls._gerar_telefone())
        nome = kwargs.pop('nome', cls._gerar_nome())
        nivel_acesso = kwargs.pop('nivel_acesso', NivelAcesso.basico)

        # Criar o usuário sem persistir
        return Usuario(
            telefone=telefone, nome=nome, nivel_acesso=nivel_acesso, **kwargs
        )

    @staticmethod
    def _gerar_telefone():
        """Gera um número de telefone único para testes."""
        return f'+5521{random.randint(900000000, 999999999)}'

    @staticmethod
    def _gerar_nome():
        """Gera um nome aleatório para testes."""
        nomes = [
            'Ana',
            'João',
            'Maria',
            'Pedro',
            'Carlos',
            'Julia',
            'Marcelo',
            'Patricia',
        ]
        sobrenomes = [
            'Silva',
            'Santos',
            'Oliveira',
            'Souza',
            'Lima',
            'Pereira',
            'Costa',
            'Rodrigues',
        ]
        return f'{random.choice(nomes)} {random.choice(sobrenomes)}'


class SuperUsuarioFactory(UsuarioFactory):
    """Factory para criar usuários com nível de acesso super_usuario."""

    @classmethod
    async def create_async(cls, session: AsyncSession, **kwargs):
        """Cria um super usuário."""
        kwargs['nivel_acesso'] = NivelAcesso.super_usuario
        return await super().create_async(session, **kwargs)

    @classmethod
    def build(cls, **kwargs):
        """Cria uma instância de super usuário sem persistir."""
        kwargs['nivel_acesso'] = NivelAcesso.super_usuario
        return super().build(**kwargs)


class UsuarioIntermediarioFactory(UsuarioFactory):
    """Factory para criar usuários com nível de acesso intermediário."""

    @classmethod
    async def create_async(cls, session: AsyncSession, **kwargs):
        """Cria um usuário intermediário."""
        kwargs['nivel_acesso'] = NivelAcesso.intermediario
        return await super().create_async(session, **kwargs)

    @classmethod
    def build(cls, **kwargs):
        """Cria uma instância de usuário intermediário sem persistir."""
        kwargs['nivel_acesso'] = NivelAcesso.intermediario
        return super().build(**kwargs)
