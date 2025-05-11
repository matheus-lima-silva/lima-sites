import random

from sqlalchemy.ext.asyncio import AsyncSession

from lima.models import Detentora


class DetentoraFactory:
    """Factory para criar instâncias do modelo Detentora para testes."""

    # Contador para garantir códigos únicos
    _contador = 0

    @classmethod
    async def create_async(cls, session: AsyncSession, **kwargs):
        """
        Cria e persiste uma detentora de forma assíncrona.

        Args:
            session: Sessão assíncrona do SQLAlchemy
            **kwargs: Atributos para sobrescrever os valores padrão

        Returns:
            Detentora: Instância persistida no banco de dados
        """
        # Obter ou gerar valores para os atributos
        codigo = kwargs.pop('codigo', cls._gerar_codigo())
        nome = kwargs.pop('nome', cls._gerar_nome())
        telefone_noc = kwargs.pop('telefone_noc', cls._gerar_telefone())

        # Criar a detentora
        detentora = Detentora(
            codigo=codigo, nome=nome, telefone_noc=telefone_noc, **kwargs
        )

        # Persistir no banco de dados
        session.add(detentora)
        await session.commit()
        await session.refresh(detentora)
        return detentora

    @classmethod
    def _gerar_codigo(cls):
        """Gera um código único para a detentora."""
        cls._contador += 1
        return f'DET-{cls._contador:06d}'

    @staticmethod
    def _gerar_nome():
        """Gera um nome aleatório para a detentora."""
        prefixos = [
            'Telecom',
            'Net',
            'Tech',
            'Link',
            'Connect',
            'Mobile',
            'Fiber',
            'Global',
        ]
        sufixos = [
            'Brasil',
            'Telecom',
            'Networks',
            'Wireless',
            'Systems',
            'Communications',
            'Group',
            'Corp',
        ]
        return f'{random.choice(prefixos)} {random.choice(sufixos)}'

    @staticmethod
    def _gerar_telefone():
        """Gera um número de telefone único para o NOC."""
        return (
            f'+55 11 {random.randint(2000, 9999)}-{random.randint(1000, 9999)}'
        )
