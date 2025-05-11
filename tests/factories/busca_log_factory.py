import json
import random

import factory
from factory.alchemy import SQLAlchemyModelFactory
from sqlalchemy.ext.asyncio import AsyncSession

from lima.models import BuscaLog, TipoBusca

from .usuario_factory import UsuarioFactory

# Endpoints comuns para evitar linha longa
API_ENDPOINTS = ['enderecos', 'buscas', 'operadoras']


class BuscaLogFactory(SQLAlchemyModelFactory):
    """Factory para criar instâncias do modelo BuscaLog para testes."""

    class Meta:
        model = BuscaLog
        sqlalchemy_session_persistence = 'flush'

    endpoint = factory.LazyFunction(
        lambda: f'/api/{random.choice(API_ENDPOINTS)}'
    )
    parametros = factory.LazyFunction(
        lambda: json.dumps({'query': 'texto de busca', 'page': 1, 'size': 10})
    )
    tipo_busca = factory.LazyFunction(lambda: random.choice(list(TipoBusca)))

    @classmethod
    async def create_async(cls, session: AsyncSession, usuario=None, **kwargs):
        """
        Cria e persiste um log de busca de forma assíncrona.

        Args:
            session: Sessão assíncrona do SQLAlchemy
            usuario: Usuário que realizou a busca (opcional)
            **kwargs: Atributos para sobrescrever os padrões da factory

        Returns:
            BuscaLog: Instância persistida no banco de dados
        """
        if usuario is None:
            usuario = await UsuarioFactory.create_async(session)

        kwargs['usuario_id'] = usuario.id

        # Gerar valores para os campos dinâmicos
        endpoint_value = kwargs.get(
            'endpoint', f'/api/{random.choice(API_ENDPOINTS)}'
        )
        parametros_value = kwargs.get(
            'parametros',
            json.dumps({'query': 'texto de busca', 'page': 1, 'size': 10}),
        )
        tipo_busca_value = kwargs.get(
            'tipo_busca', random.choice(list(TipoBusca))
        )

        # Criamos diretamente uma instância de BuscaLog ao invés de
        #  usar Factory Boy
        # para evitar problemas com a sessão
        busca_log = BuscaLog(
            usuario_id=kwargs['usuario_id'],
            endpoint=endpoint_value,
            parametros=parametros_value,
            tipo_busca=tipo_busca_value,
        )

        # Adicionamos o log à sessão e persistimos
        session.add(busca_log)
        await session.commit()
        await session.refresh(busca_log)
        return busca_log
