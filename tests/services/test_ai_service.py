from unittest.mock import MagicMock, patch

import pytest

from lima.services.ai_service import (
    generate_ai_response,
    process_address_request,
)


class TestAIService:
    """Testes para o serviço de IA."""

    @staticmethod
    @pytest.mark.asyncio
    @patch('lima.services.ai_service.genai')
    async def test_generate_ai_response(mock_genai):
        """Testa a geração de respostas da IA com mock."""
        # Configura o mock do Gemini AI
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        # Configura a resposta mock do modelo
        mock_response = MagicMock()
        mock_response.text = 'Esta é uma resposta simulada da IA.'
        mock_model.generate_content.return_value = mock_response

        # Chama a função com uma mensagem de teste
        result = await generate_ai_response('Como posso ajudar com endereços?')

        # Verifica se a função retornou a resposta esperada
        assert result == 'Esta é uma resposta simulada da IA.'

        # Verifica se o método correto foi chamado com os argumentos esperados
        mock_model.generate_content.assert_called_once()

    @staticmethod
    @pytest.mark.asyncio
    @patch('lima.services.ai_service.generate_ai_response')
    async def test_process_address_request(mock_generate_response):
        """Testa o processamento de solicitações relacionadas a endereços."""
        # Configura a resposta mock da função AI
        mock_generate_response.return_value = """
        Encontrei o seguinte endereço:
        Código: END-123456
        Logradouro: Avenida Paulista
        Bairro: Bela Vista
        Município: São Paulo
        UF: SP
        Tipo: rooftop
        """

        # Chama a função com uma solicitação de teste
        result = await process_address_request(
            'Preciso do endereço na Avenida Paulista', user_id=1
        )

        # Verifica se o resultado contém informações chave
        assert 'Avenida Paulista' in result
        assert 'São Paulo' in result

        # Verifica se a função generate_ai_response foi chamada corretamente
        mock_generate_response.assert_called_once()
        args = mock_generate_response.call_args[0][0]
        assert 'Avenida Paulista' in args
