import pytest
from fastapi import status
from httpx import AsyncClient


class TestRoutesBasicas:
    """Testes para verificar se as rotas básicas da API estão respondendo."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_rota_raiz(async_client: AsyncClient):
        """Testa se a rota raiz responde com status 200."""
        response = await async_client.get('/')
        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.json()

    @staticmethod
    @pytest.mark.asyncio
    async def test_documentacao(async_client: AsyncClient):
        """Testa se a documentação da API está acessível."""
        response = await async_client.get('/docs')
        assert response.status_code == status.HTTP_200_OK
        assert 'text/html' in response.headers['content-type']

    @staticmethod
    @pytest.mark.asyncio
    async def test_redoc(async_client: AsyncClient):
        """Testa se a documentação ReDoc está acessível."""
        response = await async_client.get('/redoc')
        assert response.status_code == status.HTTP_200_OK
        assert 'text/html' in response.headers['content-type']

    @staticmethod
    @pytest.mark.asyncio
    async def test_openapi_schema(async_client: AsyncClient):
        """Testa se o schema OpenAPI está acessível."""
        response = await async_client.get('/openapi.json')
        assert response.status_code == status.HTTP_200_OK
        assert 'application/json' in response.headers['content-type']
        schema = response.json()
        assert 'openapi' in schema
        assert 'paths' in schema
        assert 'components' in schema


class TestRotasEnderecosPublicas:
    """Testes para rotas de endereços públicas."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_listagem_enderecos_publica(async_client: AsyncClient):
        """Testa se a rota de endereços responde com
        informações sobre a API."""
        response = await async_client.get('/enderecos/')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'message' in data
        assert 'sub_apis' in data
        assert isinstance(data['sub_apis'], list)

    @staticmethod
    @pytest.mark.asyncio
    async def test_busca_endereco_por_id_nao_encontrado(
        async_client: AsyncClient,
    ):
        """Testa resposta quando um endereço não é encontrado."""
        response = await async_client.get('/enderecos/99999')  # ID inexistente
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestRotasUsuariosProtegidas:
    """Testes para rotas de usuários protegidas."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_listagem_usuarios_nao_permitida(async_client: AsyncClient):
        """Testa se a listagem de usuários sem método GET não é permitida."""
        response = await async_client.get('/usuarios/')
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    @staticmethod
    @pytest.mark.asyncio
    async def test_criar_usuario_proibido(async_client: AsyncClient):
        """Testa se a criação de usuário sem autenticação é proibida."""
        usuario_data = {'telefone': '+5521999999999', 'nome': 'Usuário Teste'}
        response = await async_client.post('/usuarios/', json=usuario_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
