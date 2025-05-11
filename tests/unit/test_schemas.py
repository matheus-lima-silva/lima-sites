import pytest
from pydantic import ValidationError

from lima.schemas import (
    AnotacaoCreate,
    AnotacaoRead,
    EnderecoCreate,
    EnderecoRead,
    UsuarioCreate,
    UsuarioRead,
)


class TestEnderecoSchemas:
    """Testes para os schemas de Endereco."""

    @staticmethod
    def test_endereco_create_valid():
        """Testa criação de schema EnderecoCreate com dados válidos."""
        endereco_data = {
            'codigo_endereco': 'END-123',
            'logradouro': 'Avenida Brasil',
            'bairro': 'Centro',
            'municipio': 'Rio de Janeiro',
            'uf': 'RJ',
        }
        endereco = EnderecoCreate(**endereco_data)
        assert endereco.codigo_endereco == 'END-123'
        assert endereco.logradouro == 'Avenida Brasil'
        assert endereco.bairro == 'Centro'
        assert endereco.municipio == 'Rio de Janeiro'
        assert endereco.uf == 'RJ'

    @staticmethod
    def test_endereco_create_invalid_uf():
        """Testa validação de UF inválida no schema EnderecoCreate."""
        endereco_data = {
            'codigo_endereco': 'END-123',
            'logradouro': 'Avenida Brasil',
            'bairro': 'Centro',
            'municipio': 'Rio de Janeiro',
            'uf': 'XX',  # UF inválida
        }
        with pytest.raises(ValidationError):
            EnderecoCreate(**endereco_data)

    @staticmethod
    def test_endereco_read():
        """Testa leitura de schema EnderecoRead."""
        endereco_data = {
            'id': 1,
            'codigo_endereco': 'END-123',
            'logradouro': 'Avenida Brasil',
            'bairro': 'Centro',
            'municipio': 'Rio de Janeiro',
            'uf': 'RJ',
            'cep': '20000-000',
            'latitude': -22.9068,
            'longitude': -43.1729,
        }
        endereco = EnderecoRead(**endereco_data)
        assert endereco.id == 1
        assert endereco.codigo_endereco == 'END-123'
        assert endereco.logradouro == 'Avenida Brasil'
        assert endereco.uf == 'RJ'


class TestUsuarioSchemas:
    """Testes para os schemas de Usuario."""

    @staticmethod
    def test_usuario_create_valid():
        """Testa criação de schema UsuarioCreate com dados válidos."""
        usuario_data = {
            'telefone': '+5521999999999',
            'nome': 'Usuário Teste',
        }
        usuario = UsuarioCreate(**usuario_data)
        assert usuario.telefone == '+5521999999999'
        assert usuario.nome == 'Usuário Teste'

    @staticmethod
    def test_usuario_read():
        """Testa leitura de schema UsuarioRead."""
        usuario_data = {
            'id': 1,
            'telefone': '+5521999999999',
            'nome': 'Usuário Teste',
            'nivel_acesso': 'basico',
            'created_at': '2025-04-28T12:00:00',
            'last_seen': '2025-04-28T12:00:00',
        }
        usuario = UsuarioRead(**usuario_data)
        assert usuario.id == 1
        assert usuario.telefone == '+5521999999999'
        assert usuario.nivel_acesso == 'basico'


class TestAnotacaoSchemas:
    """Testes para os schemas de Anotacao."""

    @staticmethod
    def test_anotacao_create_valid():
        """Testa criação de schema AnotacaoCreate com dados válidos."""
        anotacao_data = {
            'id_endereco': 1,
            'id_usuario': 1,
            'texto': 'Esta é uma anotação de teste.',
        }
        anotacao = AnotacaoCreate(**anotacao_data)
        assert anotacao.id_endereco == 1
        assert anotacao.id_usuario == 1
        assert anotacao.texto == 'Esta é uma anotação de teste.'

    @staticmethod
    def test_anotacao_read():
        """Testa leitura de schema AnotacaoRead."""
        anotacao_data = {
            'id': 1,
            'id_endereco': 1,
            'id_usuario': 1,
            'texto': 'Esta é uma anotação de teste.',
            'data_criacao': '2025-04-28T12:00:00',
            'data_atualizacao': '2025-04-28T12:00:00',
        }
        anotacao = AnotacaoRead(**anotacao_data)
        assert anotacao.id == 1
        assert anotacao.id_endereco == 1
        assert anotacao.id_usuario == 1
        assert anotacao.texto == 'Esta é uma anotação de teste.'
