# Projeto Lima - API de Endereços e Bot Telegram

![Status](https://img.shields.io/badge/Status-Em%20Desenvolvimento-yellow)
![Versão](https://img.shields.io/badge/Versão-0.1.0-blue)

## 📋 Descrição

O Projeto Lima é uma API para gestão de endereços com um bot integrado para Telegram. Ele permite consultas, sugestões e gerenciamento de endereços através de uma interface RESTful e também via interações por mensagens no Telegram.

> ⚠️ **Aviso**: Este projeto ainda está em desenvolvimento e não deve ser usado em produção.

## 🚀 Funcionalidades

- ✅ Gestão de endereços (CRUD)
- ✅ Sistema de usuários com níveis de acesso
- ✅ Sistema de sugestões para novos endereços ou alterações
- ✅ Histórico de alterações em endereços
- ✅ Anotações vinculadas a endereços
- ✅ API RESTful para integração com outros sistemas
- ✅ Interface via Telegram com suporte a múltiplos comandos e anotações

## 🛠️ Tecnologias Utilizadas

- **Backend**: FastAPI, SQLAlchemy, Pydantic, Alembic
- **Banco de Dados**: SQLite (desenvolvimento), PostgreSQL (produção)
- **Integrações**: API Telegram Bot
- **Ferramentas**: Poetry (gerenciamento de dependências), Ruff (linting)
- **Testes**: Pytest, Coverage

## 📦 Estrutura do Projeto

```
lima/
├── app.py                 # Ponto de entrada da aplicação FastAPI
├── models.py              # Modelos de dados SQLAlchemy
├── schemas.py             # Schemas Pydantic para validação
├── settings.py            # Configurações e variáveis de ambiente
├── database.py            # Configuração do banco de dados
├── security.py            # Autenticação e segurança (JWT)
├── scheduler.py           # Agendador de tarefas (APScheduler)
├── routers/               # Endpoints da API (FastAPI routers)
│   ├── auth.py            # Autenticação de usuários
│   ├── usuarios.py        # Gerenciamento de usuários
│   ├── usuarios_admin.py  # Gerenciamento administrativo de usuários
│   ├── enderecos/         # Sub-aplicação para CRUD de endereços
│   │   ├── admin.py       # Endpoints administrativos de endereços
│   │   └── busca.py       # Endpoints de busca de endereços
│   ├── sugestoes.py       # Sistema de sugestões de endereços
│   ├── alteracoes.py      # Registro de alterações em endereços
│   ├── buscas_router.py   # Histórico de buscas (nome pode variar)
│   └── anotacoes_router.py# Anotações em endereços (nome pode variar)
└── bot/                   # Módulo de integração com Telegram
    ├── main.py            # Ponto de entrada e configuração do bot Telegram
    ├── handlers.py        # Handlers para comandos e mensagens do Telegram
    └── formatters.py      # Formatação de mensagens para o Telegram
```

## 🔧 Instalação

### Pré-requisitos

- Python 3.12+
- Poetry (gerenciador de dependências)
- Bot no Telegram (para integração com Telegram)

### Instalação para Desenvolvimento

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/lima.git
cd lima

# Instale as dependências com Poetry
poetry install

# Configure as variáveis de ambiente
# Crie um arquivo .env baseado no .env.example (se existir) ou defina as variáveis diretamente
# Edite o arquivo .env com suas configurações (tokens, URLs de banco, etc.)

# Execute as migrações do banco de dados
poetry run alembic upgrade head

# Inicie o servidor de desenvolvimento FastAPI
poetry run uvicorn lima.app:app --reload

# Para configurar o webhook do Telegram (opcional, se não usar polling)
poetry run python configure_telegram_webhook.py
```

Para mais detalhes sobre a configuração, consulte a documentação específica de cada componente.

## 📚 Documentação

- [Guia de Instalação](#-instalação)
- [Configuração do Webhook do Telegram](docs/README.md) <!-- Assumindo que o README.md em docs/ agora cobre isso -->
- [API Reference](docs/README.md) <!-- Assumindo que o README.md em docs/ agora cobre isso -->
- [Guia de Testes](docs/README.md) <!-- Assumindo que o README.md em docs/ agora cobre isso -->
- [Guia de Contribuição](docs/README.md) <!-- Assumindo que o README.md em docs/ agora cobre isso -->

## 📝 Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo `LICENSE` (se existir) para mais detalhes.

## ✒️ Autores

- **Desenvolvedor Principal** - [Matheus Lima](https://github.com/matheus-lima-silva)