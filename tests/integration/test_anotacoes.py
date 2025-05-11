import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lima.models import Anotacao, Endereco, NivelAcesso, Usuario
from tests.factories import (
    AnotacaoFactory,
    EnderecoFactory,
    UsuarioFactory,
)

MAX_DIFF_SECONDS = 3600  # 1 hora em segundos
EXPECTED_ANNOTATION_COUNT = 2


class TestAnotacoesIntegration:
    """Testes de integração para o sistema de anotações."""

    # Usando o método recomendado para testes estáticos assíncronos em classes
    # pytestmark define marcações para todos os métodos de teste na classe
    pytestmark = pytest.mark.asyncio

    @staticmethod
    async def test_criar_anotacao(async_session):
        """
        Testa a criação de uma anotação e verifica se
        é persistida corretamente.
        """
        # Cria um usuário e um endereço para a anotação
        usuario = await UsuarioFactory.create_async(async_session)
        endereco = await EnderecoFactory.create_async(async_session)

        # Cria uma anotação para o endereço
        anotacao = await AnotacaoFactory.create_async(
            async_session,
            usuario=usuario,
            endereco=endereco,
            texto='Esta é uma anotação de teste para o endereço.',
        )

        # Verifica se a anotação foi persistida corretamente
        assert anotacao.id is not None
        assert anotacao.id_usuario == usuario.id
        assert anotacao.id_endereco == endereco.id
        assert anotacao.texto == (
            'Esta é uma anotação de teste para o endereço.'
        )

        # Busca diretamente do banco de dados para confirmar
        result = await async_session.get(Anotacao, anotacao.id)
        assert result is not None
        assert result.texto == 'Esta é uma anotação de teste para o endereço.'

    @staticmethod
    async def test_atualizacao_anotacao(async_session, time_travel):
        """
        Testa a atualização de uma anotação e
          verifica o campo data_atualizacao.
        """
        # Cria um usuário e endereço para a anotação
        usuario = await UsuarioFactory.create_async(async_session)
        endereco = await EnderecoFactory.create_async(async_session)

        # Marca o tempo inicial
        tempo_inicial = time_travel()

        # Cria a anotação
        anotacao = await AnotacaoFactory.create_async(
            async_session,
            usuario=usuario,
            endereco=endereco,
            texto='Anotação original',
        )

        # Definimos manualmente o campo data_criacao para o tempo inicial
        anotacao.data_criacao = tempo_inicial
        anotacao.data_atualizacao = tempo_inicial
        await async_session.commit()

        # Avança o tempo em 1 hora
        tempo_atualizacao = time_travel(delta_hours=1)

        # Atualiza a anotação
        anotacao.texto = 'Anotação atualizada'
        anotacao.data_atualizacao = tempo_atualizacao
        await async_session.commit()

        # Recarrega do banco de dados
        await async_session.refresh(anotacao)

        # Verifica se o texto foi atualizado
        assert anotacao.texto == 'Anotação atualizada'

        # Verifica se a data de criação permanece a mesma
        assert anotacao.data_criacao == tempo_inicial

        # Verifica se a data de atualização foi alterada
        assert anotacao.data_atualizacao == tempo_atualizacao

        # Verifica se há pelo menos 1 hora de diferença entre as datas
        diff_seconds = (
            anotacao.data_atualizacao - anotacao.data_criacao
        ).total_seconds()
        assert diff_seconds >= MAX_DIFF_SECONDS

    @staticmethod
    async def test_anotacoes_multiplas_por_endereco(async_session):
        """
        Testa a criação de múltiplas anotações para um mesmo endereço.
        """
        # Cria usuários
        usuario1 = await UsuarioFactory.create_async(async_session)
        usuario2 = await UsuarioFactory.create_async(async_session)

        # Cria um endereço para ser anotado
        endereco = await EnderecoFactory.create_async(async_session)

        # Cria anotações de usuários diferentes para o mesmo endereço
        await AnotacaoFactory.create_async(
            async_session,
            usuario=usuario1,
            endereco=endereco,
            texto='Anotação do usuário 1',
        )

        await AnotacaoFactory.create_async(
            async_session,
            usuario=usuario2,
            endereco=endereco,
            texto='Anotação do usuário 2',
        )

        # Recarrega o endereço do banco para garantir que as
        #  relações estão atualizadas
        await async_session.refresh(endereco)

        # Verifica se o endereço tem as anotações associadas
        assert len(endereco.anotacoes) == EXPECTED_ANNOTATION_COUNT
        assert any(
            a.texto == 'Anotação do usuário 1' for a in endereco.anotacoes
        )
        assert any(
            a.texto == 'Anotação do usuário 2' for a in endereco.anotacoes
        )

        # Verifica se os usuários são diferentes nas anotações
        usuario_ids = [a.id_usuario for a in endereco.anotacoes]
        assert len(set(usuario_ids)) == EXPECTED_ANNOTATION_COUNT


@pytest.mark.asyncio
async def test_criar_e_recuperar_anotacao(async_session: AsyncSession):
    """Testa a criação e recuperação de uma anotação."""
    # Criar um usuário de teste
    usuario = Usuario(
        telefone='+5521987654321',
        nome='Testador',
        nivel_acesso=NivelAcesso.basico,
    )
    async_session.add(usuario)
    await async_session.flush()

    # Criar um endereço de teste
    endereco = Endereco(
        codigo_endereco='END-TEST-1',
        logradouro='Rua de Teste',
        bairro='Bairro Teste',
        municipio='Cidade Teste',
        uf='RJ',
        latitude=-22.9068,
        longitude=-43.1729,
    )
    async_session.add(endereco)
    await async_session.flush()

    # Criar uma anotação
    anotacao = Anotacao(
        id_endereco=endereco.id,
        id_usuario=usuario.id,
        texto='Esta é uma anotação de teste para integração.',
    )
    async_session.add(anotacao)
    await async_session.commit()

    # Recuperar a anotação
    resultado = await async_session.execute(
        select(Anotacao).where(Anotacao.id == anotacao.id)
    )
    anotacao_recuperada = resultado.scalar_one()

    # Verificar se os dados estão corretos
    assert anotacao_recuperada.id == anotacao.id
    assert (
        anotacao_recuperada.texto
        == 'Esta é uma anotação de teste para integração.'
    )
    assert anotacao_recuperada.id_endereco == endereco.id
    assert anotacao_recuperada.id_usuario == usuario.id
    assert anotacao_recuperada.data_criacao is not None


@pytest.mark.asyncio
async def test_atualizar_anotacao(async_session: AsyncSession):
    """Testa a atualização de uma anotação."""
    # Criar um usuário de teste
    usuario = Usuario(
        telefone='+5521987654322',
        nome='Testador 2',
        nivel_acesso=NivelAcesso.basico,
    )
    async_session.add(usuario)

    # Criar um endereço de teste
    endereco = Endereco(
        codigo_endereco='END-TEST-2',
        logradouro='Rua de Teste 2',
        bairro='Bairro Teste 2',
        municipio='Cidade Teste 2',
        uf='SP',
        latitude=-23.5505,
        longitude=-46.6333,
    )
    async_session.add(endereco)
    await async_session.flush()

    # Criar uma anotação
    anotacao = Anotacao(
        id_endereco=endereco.id,
        id_usuario=usuario.id,
        texto='Anotação original antes da atualização.',
    )
    async_session.add(anotacao)
    await async_session.commit()

    # Atualizar a anotação
    anotacao_id = anotacao.id
    anotacao.texto = 'Anotação atualizada para teste de integração.'
    await async_session.commit()

    # Recuperar a anotação atualizada
    resultado = await async_session.execute(
        select(Anotacao).where(Anotacao.id == anotacao_id)
    )
    anotacao_atualizada = resultado.scalar_one()

    # Verificar se os dados foram atualizados
    assert (
        anotacao_atualizada.texto
        == 'Anotação atualizada para teste de integração.'
    )
    assert (
        anotacao_atualizada.data_atualizacao > anotacao_atualizada.data_criacao
    )


@pytest.mark.asyncio
async def test_recuperar_anotacoes_do_endereco(async_session: AsyncSession):
    """Testa a recuperação de todas as anotações de um endereço."""
    EXPECTED_ANNOTATIONS_FOR_ENDERECO = 3
    # Criar um usuário de teste
    usuario = Usuario(
        telefone='+5521987654323',
        nome='Testador 3',
        nivel_acesso=NivelAcesso.basico,
    )
    async_session.add(usuario)

    # Criar um endereço de teste
    endereco = Endereco(
        codigo_endereco='END-TEST-3',
        logradouro='Rua de Teste 3',
        bairro='Bairro Teste 3',
        municipio='Cidade Teste 3',
        uf='MG',
        latitude=-19.9245,
        longitude=-43.9352,
    )
    async_session.add(endereco)
    await async_session.flush()
    # Criar múltiplas anotações para o mesmo endereço
    for i in range(EXPECTED_ANNOTATIONS_FOR_ENDERECO):
        anotacao = Anotacao(
            id_endereco=endereco.id,
            id_usuario=usuario.id,
            texto=f'Anotação {i + 1} para o endereço de teste.',
        )
        async_session.add(anotacao)

    await async_session.commit()

    # Recuperar todas as anotações do endereço
    resultado = await async_session.execute(
        select(Anotacao).where(Anotacao.id_endereco == endereco.id)
    )
    anotacoes = resultado.scalars().all()
    # Verificar se todas as anotações foram recuperadas
    # Verificar se todas as anotações foram recuperadas
    assert len(anotacoes) == EXPECTED_ANNOTATIONS_FOR_ENDERECO
    assert all(a.id_usuario == usuario.id for a in anotacoes)
