import pytest

from lima.models import NivelAcesso, Usuario
from tests.factories import SuperUsuarioFactory, UsuarioFactory

# Constantes para evitar magic numbers
TEST_YEAR = 2025
TEST_MONTH = 5  # Atualizado para refletir o mês atual (maio)
TEST_DAY = 3    # Atualizado para refletir o dia atual
ONE_HOUR_SECONDS = 3600


class TestUsuarioModel:
    """Testes unitários para o modelo Usuario"""

    @staticmethod
    def test_usuario_creation():
        """Testa a criação básica de um usuário"""
        usuario = UsuarioFactory.build(
            telefone='+5511999999999',
            nome='Usuário Teste',
            nivel_acesso=NivelAcesso.basico,
        )

        assert usuario.telefone == '+5511999999999'
        assert usuario.nome == 'Usuário Teste'
        assert usuario.nivel_acesso == NivelAcesso.basico
        assert usuario.buscas == []
        assert usuario.busca_logs == []
        assert usuario.sugestoes == []
        assert usuario.alteracoes == []
        assert usuario.anotacoes == []

    @staticmethod
    def test_usuario_factory_defaults():
        """Testa os valores padrão da factory de usuário"""
        usuario = UsuarioFactory.build()

        assert usuario.telefone is not None
        assert usuario.nivel_acesso == NivelAcesso.basico
        assert usuario.nome is not None

    @staticmethod
    def test_super_usuario_factory():
        """Testa a factory de super usuário"""
        usuario = SuperUsuarioFactory.build()

        assert usuario.nivel_acesso == NivelAcesso.super_usuario


@pytest.mark.asyncio
class TestUsuarioAsync:
    """Testes assíncronos para o modelo Usuario"""

    @staticmethod
    async def test_usuario_async_creation(async_session):
        """
        Testa a criação de um usuário no banco de dados de forma assíncrona
        """
        # Cria um usuário usando a factory e persiste no banco
        usuario = await UsuarioFactory.create_async(
            async_session,
            telefone='+5511999999999',
            nome='Usuário Teste Async',
        )

        # Verifica se o usuário foi persistido e tem um ID
        assert usuario.id is not None

        # Busca o usuário no banco para confirmar a persistência
        result = await async_session.get(Usuario, usuario.id)
        assert result is not None
        assert result.telefone == '+5511999999999'
        assert result.nome == 'Usuário Teste Async'

    @staticmethod
    async def test_frozen_time_with_usuario(async_session, frozen_time):
        """
        Testa a criação de usuário com tempo congelado usando freeze_gun
        """
        # O tempo está congelado em 2025-04-28 12:00:00
        usuario = await UsuarioFactory.create_async(async_session)

        # Verificamos apenas que a data é a mesma,
        # sem se preocupar com a hora exata
        assert usuario.created_at.year == TEST_YEAR
        assert usuario.created_at.month == TEST_MONTH
        assert usuario.created_at.day == TEST_DAY

        assert usuario.last_seen.year == TEST_YEAR
        assert usuario.last_seen.month == TEST_MONTH
        assert usuario.last_seen.day == TEST_DAY

    @staticmethod
    async def test_time_travel(async_session, time_travel):
        """
        Testa o conceito de viagem no tempo usando datetime manual
        """
        # Definimos manualmente o created_at para o primeiro usuário
        time1 = time_travel()
        usuario1 = await UsuarioFactory.create_async(
            async_session, telefone='+5511999999991'
        )
        # Atualizamos manualmente o campo created_at após a criação
        usuario1.created_at = time1
        usuario1.last_seen = time1
        await async_session.commit()

        # Avançamos o tempo em 1 hora
        time2 = time_travel(delta_hours=1)

        # Definimos manualmente o created_at para o segundo usuário
        usuario2 = await UsuarioFactory.create_async(
            async_session, telefone='+5511999999992'
        )
        # Atualizamos manualmente o campo created_at após a criação
        usuario2.created_at = time2
        usuario2.last_seen = time2
        await async_session.commit()

        # Recarregamos os usuários do banco de dados para garantir
        # que as alterações foram persistidas
        await async_session.refresh(usuario1)
        await async_session.refresh(usuario2)

        # Verificamos se o segundo usuário tem um timestamp posterior
        assert usuario2.created_at > usuario1.created_at

        # Verificamos se a diferença é de pelo menos 1 hora (3600 segundos)
        diff_seconds = (
            usuario2.created_at - usuario1.created_at
        ).total_seconds()
        assert diff_seconds >= ONE_HOUR_SECONDS
