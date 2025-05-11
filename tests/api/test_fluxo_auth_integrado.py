import pytest
from fastapi import status

from lima.models import NivelAcesso


class TestFluxoAutenticacaoIntegrado:
    """Testes para o fluxo de autenticação integrado."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_fluxo_autenticacao_basica(
        async_client, criar_usuario_com_token
    ):
        """
        Teste do fluxo básico de autenticação usando as melhorias
          no compartilhamento
        de sessão de banco de dados.
        """
        # 1. Criar um usuário de teste e obter seu token
        usuario, token, headers = await criar_usuario_com_token(
            telefone='+5521987654321', nome='Usuário Teste Auth'
        )

        # 2. Confirmar que o usuário foi criado
        assert usuario is not None
        assert usuario.telefone == '+5521987654321'
        assert usuario.nivel_acesso == NivelAcesso.basico

        # 3. Testar autenticação na API
        response = await async_client.get('/usuarios/me', headers=headers)

        # 4. Verificar resposta
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'telefone' in data
        assert data['telefone'] == '+5521987654321'
        assert data['nivel_acesso'] == 'basico'

        # 5. Testar acesso sem permissão a uma rota protegida
        response = await async_client.get('/admin/usuarios/', headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN
