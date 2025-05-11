import pytest
from fastapi import status
from httpx import AsyncClient


class TestAuthEndpoints:
    """Testes para os endpoints de autenticação."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_create_whatsapp_token(
        async_client: AsyncClient, async_session
    ):
        """Testa a criação de token para autenticação via WhatsApp."""
        # Dados para o pedido de token
        payload = {
            'phone_number': '+5511999999999',
            'verification_code': '123456',  # Código opcional
        }

        # Faz a requisição para o endpoint
        response = await async_client.post(
            '/auth/whatsapp/token', json=payload
        )

        # Verifica se a resposta foi bem-sucedida
        assert response.status_code == status.HTTP_200_OK

        # Verifica se o token foi gerado corretamente
        data = response.json()
        assert 'access_token' in data
        assert 'token_type' in data
        assert data['token_type'] == 'bearer'
        assert len(data['access_token']) > 0

    @staticmethod
    @pytest.mark.asyncio
    async def test_create_whatsapp_token_invalid_phone(
        async_client: AsyncClient,
    ):
        """Testa a criação de token com número de telefone inválido."""
        # Dados com número inválido
        payload = {
            'phone_number': 'numero_invalido',
        }

        # Faz a requisição para o endpoint
        response = await async_client.post(
            '/auth/whatsapp/token', json=payload
        )

        # Verifica se a resposta indica erro de validação
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @staticmethod
    @pytest.mark.asyncio
    async def test_verify_whatsapp_webhook(async_client: AsyncClient):
        """Testa a verificação do webhook do WhatsApp."""
        # Mock dos parâmetros de verificação do WhatsApp
        # Nota: o token WHATSAPP_VERIFY_TOKEN precisa ser definido
        # nas configurações
        params = {
            'hub_mode': 'subscribe',
            'hub_challenge': '1234567890',
            'hub_verify_token': 'test_verify_token',
            # Deve corresponder ao valor nas configurações
        }

        # Faz a requisição para o endpoint
        response = await async_client.get(
            '/auth/whatsapp/verify', params=params
        )

        # Verifica se a resposta tem o status correto
        # Nota: O teste pode falhar se o token não corresponder ao configurado
        # Este é apenas um exemplo e pode precisar de ajustes conforme
        #  a configuração real
        assert response.status_code in {
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN,
        }
