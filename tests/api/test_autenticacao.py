import pytest
from fastapi import status
from jose import jwt
from sqlalchemy import select

from lima.models import NivelAcesso, Usuario
from lima.security import create_whatsapp_token
from lima.settings import settings


class TestAutenticacao:
    """Testes para o sistema de autenticação."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_criar_token_e_validar(usuario_basico):
        """Testa a criação e validação de um token JWT."""
        # O fixture usuario_basico não é mais uma coroutine,
        # é um objeto Usuario
        # Criar um token para o usuário
        token = create_whatsapp_token(usuario_basico.telefone)

        # Decodificar o token para validar
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])

        # Verificar se o token contém as informações corretas
        assert payload['sub'] == usuario_basico.telefone
        assert 'exp' in payload

    @staticmethod
    @pytest.mark.asyncio
    async def test_acesso_sem_token(async_client):
        """Testa acesso a endpoints protegidos sem token."""
        response = await async_client.get('/usuarios/me')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @staticmethod
    @pytest.mark.asyncio
    async def test_acesso_com_token_invalido(async_client):
        """Testa acesso com token inválido."""
        headers = {'Authorization': 'Bearer tokeninvalido'}
        response = await async_client.get('/usuarios/me', headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @staticmethod
    @pytest.mark.asyncio
    async def test_acesso_com_token_valido(
        async_client, criar_usuario_com_token
    ):
        """Testa acesso com token válido."""
        # Utiliza a fixture criar_usuario_com_token para simplificar o código
        _, _, headers = await criar_usuario_com_token(
            telefone='+5521888777666', nome='Usuário Teste Token Válido'
        )

        # Testar acesso com o token
        response = await async_client.get('/usuarios/me', headers=headers)

        # Verificar resultado
        assert response.status_code == status.HTTP_200_OK
        assert 'id' in response.json()
        assert 'nivel_acesso' in response.json()
        assert response.json()['nivel_acesso'] == 'basico'


class TestNiveisAcesso:
    """Testes para o sistema de níveis de acesso."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_acesso_usuario_basico(
        async_client, criar_usuario_com_token
    ):
        """Testa permissões de usuário básico."""
        # Utiliza a fixture criar_usuario_com_token
        _, _, headers = await criar_usuario_com_token(
            telefone='+5521777666555', nome='Usuário Básico Direto'
        )

        # Usuário básico pode acessar seus próprios dados
        response = await async_client.get('/usuarios/me', headers=headers)
        assert response.status_code == status.HTTP_200_OK

        # Usuário básico não pode acessar admin
        response = await async_client.get('/admin/usuarios/', headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @staticmethod
    @pytest.mark.asyncio
    async def test_acesso_usuario_intermediario(
        async_client, criar_usuario_com_token
    ):
        """Testa permissões de usuário intermediário."""
        # Utiliza a fixture criar_usuario_com_token
        usuario, _, headers = await criar_usuario_com_token(
            telefone='+5521666555444',
            nome='Usuário Intermediário Direto',
            nivel=NivelAcesso.intermediario,
        )

        # Usuário intermediário pode acessar seus próprios dados
        response = await async_client.get('/usuarios/me', headers=headers)
        assert response.status_code == status.HTTP_200_OK

        # Usuário intermediário pode acessar dados de outros usuários
        # Criar outro usuário para testar acesso
        outro_usuario, _, _ = await criar_usuario_com_token(
            telefone='+5521666555000', nome='Outro Usuário'
        )

        response = await async_client.get(
            f'/usuarios/{outro_usuario.id}', headers=headers
        )
        assert response.status_code == status.HTTP_200_OK

        # Usuário intermediário pode acessar admin (comportamento atual da API)
        response = await async_client.get('/admin/usuarios/', headers=headers)
        assert response.status_code == status.HTTP_200_OK

    @staticmethod
    @pytest.mark.asyncio
    async def test_acesso_super_usuario(async_client, criar_usuario_com_token):
        """Testa permissões de super usuário."""
        # Utiliza a fixture criar_usuario_com_token
        usuario, _, headers = await criar_usuario_com_token(
            telefone='+5521555444333',
            nome='Super Usuário Direto',
            nivel=NivelAcesso.super_usuario,
        )

        # Super usuário pode acessar seus próprios dados
        response = await async_client.get('/usuarios/me', headers=headers)
        assert response.status_code == status.HTTP_200_OK

        # Super usuário pode acessar dados de outros usuários
        # Criar outro usuário para testar acesso
        outro_usuario, _, _ = await criar_usuario_com_token(
            telefone='+5521555444000', nome='Outro Usuário'
        )

        response = await async_client.get(
            f'/usuarios/{outro_usuario.id}', headers=headers
        )
        assert response.status_code == status.HTTP_200_OK

        # Super usuário pode acessar admin
        response = await async_client.get('/admin/usuarios/', headers=headers)
        assert response.status_code == status.HTTP_200_OK


class TestAutenticacaoComponentes:
    """Testes de componentes individuais do sistema de autenticação."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_validacao_token_jwt():
        """Testa a criação e validação de tokens JWT."""
        # Simula dados de um usuário para o token
        telefone = '+5521900000999'

        # Cria token
        token = create_whatsapp_token(telefone)

        # Valida o token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])

        # Verifica informações no token
        assert payload['sub'] == telefone
        assert 'exp' in payload
        assert 'iat' in payload

    @staticmethod
    @pytest.mark.asyncio
    async def test_criacao_usuario(async_session):
        """Testa a criação e recuperação de um usuário."""
        # Cria usuário
        telefone = '+5521988776655'
        usuario = Usuario(
            telefone=telefone,
            nome='Usuário Teste Componente',
            nivel_acesso=NivelAcesso.basico,
        )
        async_session.add(usuario)
        await async_session.commit()
        # Recupera o usuário usando a função da fixture criar_usuario_com_token
        stmt = select(Usuario).where(Usuario.telefone == telefone)
        stmt = select(Usuario).where(Usuario.telefone == telefone)
        result = await async_session.execute(stmt)
        usuario_recuperado = result.scalar_one()

        # Verifica os dados
        assert usuario_recuperado.id is not None
        assert usuario_recuperado.telefone == telefone
        assert usuario_recuperado.nivel_acesso == NivelAcesso.basico
