# Projeto Lima - API de Endereços via WhatsApp e Telegram

![Status](https://img.shields.io/badge/Status-Em%20Desenvolvimento-yellow)
![Versão](https://img.shields.io/badge/Versão-0.1.0-blue)

## 📋 Descrição

O Projeto Lima é uma API para gestão de endereços com integração ao WhatsApp e Telegram. Ele permite consultas, sugestões e gerenciamento de endereços através de uma interface RESTful e também via interações por mensagens.

> ⚠️ **Aviso**: Este projeto ainda está em desenvolvimento e não deve ser usado em produção.

## 🚀 Funcionalidades

- ✅ Gestão de endereços (CRUD)
- ✅ Sistema de usuários com níveis de acesso
- ✅ Sistema de sugestões para novos endereços ou alterações
- ✅ Histórico de alterações em endereços
- ✅ Anotações vinculadas a endereços
- ✅ API RESTful para integração com outros sistemas
- 🚧 Interface via WhatsApp para consultas e sugestões (em desenvolvimento)
- ✅ Interface via Telegram com suporte a múltiplos comandos e anotações

## 🛠️ Tecnologias Utilizadas

- **Backend**: FastAPI, SQLAlchemy, Pydantic, Alembic
- **Banco de Dados**: SQLite (desenvolvimento), PostgreSQL (produção)
- **Integrações**: API WhatsApp Cloud (Meta), API Telegram Bot
- **Ferramentas**: Poetry (gerenciamento de dependências), Ruff (linting)
- **Testes**: Pytest, Coverage

## 📦 Estrutura do Projeto

```
lima/
├── app.py                 # Ponto de entrada da aplicação
├── models.py              # Modelos de dados
├── schemas.py             # Schemas Pydantic
├── settings.py            # Configurações e variáveis de ambiente
├── database.py            # Configuração do banco de dados
├── security.py            # Autenticação e segurança
├── scheduler.py           # Agendador de tarefas
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
    ├── whatsapp_commands.py # Comandos para WhatsApp
    └── telegram/          # Módulo de integração com Telegram
        ├── __init__.py    # Exportação da API do módulo
        ├── core.py        # Funções básicas de comunicação com a API
        ├── commands.py    # Gerenciamento de comandos
        ├── formatters.py  # Formatação de mensagens
        ├── conversation.py # Gerenciamento de conversas
        ├── registro.py    # Funções para registro de usuários
        └── handlers/      # Handlers para diferentes tipos de comandos
            ├── annotation_commands.py  # Comandos de anotação
            ├── search_commands.py      # Comandos de busca
            ├── detail_commands.py      # Comandos de detalhes
            └── basic_commands.py       # Comandos básicos
```

## 🔧 Instalação

### Pré-requisitos

- Python 3.10+
- Poetry (gerenciador de dependências)
- Conta no Facebook Business (para integração com WhatsApp)
- Bot no Telegram (para integração com Telegram)

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

# Para configurar o webhook do Telegram (opcional)
poetry run python configure_telegram_webhook.py
```

Para mais detalhes sobre a configuração, consulte a [documentação completa](docs/README.md).

## 📚 Documentação

- [Guia de Instalação](docs/installation.md)
- [Configuração do WhatsApp](docs/whatsapp-setup.md)
- [Configuração do Telegram](docs/telegram-setup.md)
- [Configuração do Webhook do Telegram](docs/telegram-webhook-guide.md)
- [Sistema de Anotações via Telegram](docs/telegram-anotacoes.md)
- [Estrutura do Banco de Dados](docs/database.md)
- [API Reference](docs/api.md)
- [Guia de Testes](docs/testing-guide.md)
- [Guia de Contribuição](docs/contributing.md)

## 📝 Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## ✒️ Autores

- **Desenvolvedor Principal** - [Matheus Lima](https://github.com/matheus-lima-silva)