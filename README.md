# Projeto Lima - API de Endereços via WhatsApp

![Status](https://img.shields.io/badge/Status-Em%20Desenvolvimento-yellow)
![Versão](https://img.shields.io/badge/Versão-0.1.0-blue)

## 📋 Descrição

O Projeto Lima é uma API para gestão de endereços com integração ao WhatsApp. Ele permite consultas, sugestões e gerenciamento de endereços através de uma interface RESTful e também via interações por WhatsApp.

> ⚠️ **Aviso**: Este projeto ainda está em desenvolvimento e não deve ser usado em produção.

## 🚀 Funcionalidades

- ✅ Gestão de endereços (CRUD)
- ✅ Sistema de usuários com níveis de acesso
- ✅ Sistema de sugestões para novos endereços ou alterações
- ✅ Histórico de alterações em endereços
- ✅ Anotações vinculadas a endereços
- ✅ API RESTful para integração com outros sistemas
- ✅ Interface via WhatsApp para consultas e sugestões

## 🛠️ Tecnologias Utilizadas

- **Backend**: FastAPI, SQLAlchemy, Pydantic, Alembic
- **Banco de Dados**: SQLite (desenvolvimento), PostgreSQL (produção)
- **Integrações**: API WhatsApp Cloud (Meta)
- **Ferramentas**: Poetry (gerenciamento de dependências)

## 📦 Estrutura do Projeto

```
lima/
├── app.py                 # Ponto de entrada da aplicação
├── models.py              # Modelos de dados
├── schemas.py             # Schemas Pydantic
├── settings.py            # Configurações e variáveis de ambiente
├── database.py            # Configuração do banco de dados
├── security.py            # Autenticação e segurança
├── routers/               # Endpoints da API
│   ├── auth.py            # Autenticação
│   ├── usuarios.py        # Gerenciamento de usuários
│   ├── enderecos.py       # CRUD de endereços
│   ├── sugestoes.py       # Sistema de sugestões
│   ├── alteracoes.py      # Registro de alterações
│   ├── buscas.py          # Histórico de buscas
│   └── anotacoes.py       # Anotações em endereços
└── services/
    ├── ai_service.py      # Serviço de IA para processamento
    ├── whatsapp.py        # Integração com WhatsApp
    └── whatsapp_commands.py # Comandos para WhatsApp
```

## 🔧 Instalação

### Pré-requisitos

- Python 3.10+
- Poetry (gerenciador de dependências)
- Conta no Facebook Business (para integração com WhatsApp)

### Instalação para Desenvolvimento

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/lima.git
cd lima

# Instale as dependências com Poetry
poetry install

# Configure as variáveis de ambiente
cp .env.example .env
# Edite o arquivo .env com suas configurações

# Execute as migrações do banco de dados
poetry run alembic upgrade head

# Inicie o servidor de desenvolvimento
poetry run uvicorn lima.app:app --reload
```

Para mais detalhes sobre a configuração, consulte a [documentação completa](docs/README.md).

## 📚 Documentação

- [Guia de Instalação](docs/installation.md)
- [Configuração do WhatsApp](docs/whatsapp-setup.md)
- [Estrutura do Banco de Dados](docs/database.md)
- [API Reference](docs/api.md)
- [Guia de Contribuição](docs/contributing.md)

## 📝 Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## ✒️ Autores

- **Desenvolvedor Principal** - [Seu Nome](https://github.com/seu-usuario)