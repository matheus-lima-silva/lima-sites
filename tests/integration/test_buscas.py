import pytest

from lima.models import Busca, TipoBusca
from tests.factories import (
    BuscaFactory,
    BuscaLogFactory,
    EnderecoFactory,
    UsuarioFactory,
)

# Constantes para evitar magic numbers
THIRTY_MINUTES_SECONDS = 1800
EXPECTED_BUSCAS = 2


class TestBuscasIntegration:
    """Testes de integração para o sistema de buscas."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_criar_busca_e_verificar_registro(async_session):
        """
        Testa a criação de uma busca e verifica se o registro
        é persistido corretamente.
        """
        # Cria um usuário e um endereço para a busca
        usuario = await UsuarioFactory.create_async(async_session)
        endereco = await EnderecoFactory.create_async(async_session)

        # Cria uma busca relacionando usuário e endereço
        busca = await BuscaFactory.create_async(
            async_session,
            usuario=usuario,
            endereco=endereco,
            info_adicional='Teste de busca integrada',
        )

        # Verifica se a busca foi persistida corretamente
        assert busca.id is not None
        assert busca.id_usuario == usuario.id
        assert busca.id_endereco == endereco.id
        assert busca.info_adicional == 'Teste de busca integrada'

        # Busca diretamente do banco de dados para confirmar
        result = await async_session.get(Busca, busca.id)
        assert result is not None
        assert result.id_usuario == usuario.id
        assert result.id_endereco == endereco.id

    @staticmethod
    @pytest.mark.asyncio
    async def test_registros_busca_log(async_session, time_travel):
        """Testa o registro de logs de busca com timestamps corretos."""
        # Cria um usuário para associar aos logs
        usuario = await UsuarioFactory.create_async(async_session)

        # Cria logs de busca em tempos diferentes
        tempo_inicial = time_travel()
        log1 = await BuscaLogFactory.create_async(
            async_session,
            usuario=usuario,
            endpoint='/api/enderecos',
            tipo_busca=TipoBusca.por_municipio,
        )
        log1.data_hora = tempo_inicial
        await async_session.commit()

        # Avança o tempo em 30 minutos
        tempo_avancado = time_travel(delta_minutes=30)
        log2 = await BuscaLogFactory.create_async(
            async_session,
            usuario=usuario,
            endpoint='/api/enderecos',
            tipo_busca=TipoBusca.por_logradouro,
        )
        log2.data_hora = tempo_avancado
        await async_session.commit()

        # Recarrega os objetos do banco
        await async_session.refresh(log1)
        await async_session.refresh(log2)

        # Verifica se os timestamps foram registrados corretamente
        assert (
            log2.data_hora - log1.data_hora
        ).total_seconds() >= THIRTY_MINUTES_SECONDS

        # Verifica se os logs estão associados ao usuário
        assert log1.usuario_id == usuario.id
        assert log2.usuario_id == usuario.id

    @staticmethod
    @pytest.mark.asyncio
    async def test_historico_buscas_usuario(async_session):
        """Testa o relacionamento entre usuários e suas buscas."""
        # Cria um usuário com várias buscas
        usuario = await UsuarioFactory.create_async(async_session)
        endereco1 = await EnderecoFactory.create_async(async_session)
        endereco2 = await EnderecoFactory.create_async(async_session)

        # Cria múltiplas buscas para o mesmo usuário
        busca1 = await BuscaFactory.create_async(
            async_session, usuario=usuario, endereco=endereco1
        )

        busca2 = await BuscaFactory.create_async(
            async_session, usuario=usuario, endereco=endereco2
        )

        # Recarrega o usuário para garantir que as relações estão atualizadas
        await async_session.refresh(usuario)

        # Verifica se o usuário tem as buscas associadas
        assert len(usuario.buscas) == EXPECTED_BUSCAS
        assert any(b.id == busca1.id for b in usuario.buscas)
        assert any(b.id == busca2.id for b in usuario.buscas)
