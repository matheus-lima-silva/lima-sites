# Projeto Lima - API de Endereços e Bot Telegram

![Status](https://img.shields.io/badge/Status-Em%20Desenvolvimento-yellow)
![Versão](https://img.shields.io/badge/Versão-0.1.0-blue)
![Python](https://img.shields.io/badge/Python-3.12+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green)

## 📋 Descrição

O Projeto Lima é uma API completa para gestão de endereços com bot integrado para Telegram. Permite consultas, sugestões, anotações e gerenciamento de endereços através de uma interface RESTful e também via interações por mensagens no Telegram.

### ✨ Principais Diferenciais

- **Sistema de Anotações**: Permite adicionar observações e comentários personalizados para endereços
- **Autenticação Integrada**: Sistema JWT para autenticação segura entre bot e API
- **Níveis de Acesso**: Sistema hierárquico de permissões (básico, intermediário, super usuário)
- **Histórico Completo**: Rastreamento de alterações e auditoria de modificações
- **Interface Dupla**: API REST + Bot Telegram para máxima flexibilidade

> ⚠️ **Aviso**: Este projeto ainda está em desenvolvimento ativo e não deve ser usado em produção.

## 🚀 Funcionalidades

### ✅ Funcionalidades Implementadas

- **Gestão de Endereços**: CRUD completo com busca avançada por operadora
- **Sistema de Usuários**: Autenticação JWT com níveis de acesso hierárquicos
- **Sistema de Anotações**: Adicionar, listar e gerenciar anotações vinculadas a endereços
- **Bot Telegram**: Interface conversacional com comandos intuitivos
- **Sistema de Sugestões**: Propor novos endereços ou alterações existentes
- **Histórico de Alterações**: Auditoria completa de modificações
- **API RESTful**: Endpoints documentados para integração com outros sistemas
- **Autenticação Segura**: Tokens JWT com expiração configurável

### 🔄 Em Desenvolvimento

- Sistema de notificações
- Interface web administrativa
- Exportação de dados
- Integração com WhatsApp
- Sistema de backup automatizado

## 🛠️ Tecnologias Utilizadas

### Backend
- **FastAPI**: Framework web assíncrono de alta performance
- **SQLAlchemy**: ORM moderno com suporte a async/await
- **Pydantic**: Validação de dados e serialização
- **Alembic**: Migração de banco de dados
- **APScheduler**: Agendamento de tarefas

### Banco de Dados
- **SQLite**: Desenvolvimento e testes
- **PostgreSQL**: Produção (via AsyncPG)

### Integrações
- **python-telegram-bot**: Integração com API do Telegram
- **HTTPX**: Cliente HTTP assíncrono
- **PyJWT**: Manipulação de tokens JWT

### Ferramentas de Desenvolvimento
- **Poetry**: Gerenciamento de dependências
- **Ruff**: Linting e formatação de código
- **Pytest**: Framework de testes
- **Coverage**: Cobertura de testes

## 📦 Estrutura do Projeto

```
lima/
├── app.py                 # Aplicação FastAPI principal
├── models.py              # Modelos SQLAlchemy (Usuário, Endereço, Anotação, etc.)
├── schemas.py             # Schemas Pydantic para validação de entrada/saída
├── settings.py            # Configurações e variáveis de ambiente
├── database.py            # Configuração do banco de dados e sessões
├── security.py            # Sistema de autenticação JWT e permissões
├── scheduler.py           # Agendador de tarefas (APScheduler)
│
├── routers/               # Endpoints da API REST (FastAPI routers)
│   ├── auth.py            # Autenticação e tokens JWT
│   ├── usuarios.py        # Gerenciamento de usuários
│   ├── usuarios_admin.py  # Administração de usuários
│   ├── anotacoes.py       # CRUD de anotações de endereços
│   ├── sugestoes.py       # Sistema de sugestões
│   ├── alteracoes.py      # Histórico de alterações
│   ├── buscas.py          # Histórico de buscas
│   └── enderecos/         # Sub-módulo para endereços
│       ├── __init__.py
│       ├── admin.py       # Administração de endereços
│       └── busca.py       # Busca e consulta de endereços
│
├── services/              # Lógica de negócio
│   ├── __init__.py
│   └── utils.py           # Utilitários diversos
│
├── utils/                 # Funções auxiliares
│   ├── __init__.py
│   └── auditoria.py       # Sistema de auditoria
│
└── bot/                   # Módulo completo do Bot Telegram
    ├── main.py            # Configuração e inicialização do bot
    ├── config.py          # Configurações específicas do bot
    ├── api_client.py      # Cliente HTTP para comunicação com a API
    ├── formatters.py      # Formatação de mensagens para Telegram
    ├── keyboards.py       # Teclados inline e reply keyboards
    ├── utils.py           # Utilitários do bot
    │
    ├── handlers/          # Handlers para comandos e conversações
    │   ├── __init__.py
    │   ├── anotacao.py    # Fluxo de criação/leitura de anotações
    │   ├── auxiliares.py  # Comandos auxiliares (/help, /start, etc.)
    │   ├── busca.py       # Busca de endereços via bot
    │   ├── callback.py    # Gerenciamento de callbacks inline
    │   ├── estatisticas.py# Estatísticas e relatórios
    │   └── listagem.py    # Listagem de resultados
    │
    └── services/          # Serviços específicos do bot
        ├── __init__.py
        ├── anotacao.py    # Lógica de anotações
        ├── auth.py        # Autenticação do bot
        └── endereco.py    # Operações com endereços
```

### 🗃️ Outros Arquivos Importantes

```
├── migrations/            # Scripts de migração do Alembic
├── tests/                 # Suíte de testes automatizados
├── docs/                  # Documentação completa do projeto
├── alembic.ini           # Configuração do Alembic
├── pyproject.toml        # Configuração do Poetry e ferramentas
├── docker-compose.yml    # Orquestração de containers
├── Dockerfile            # Imagem Docker para produção
└── configure_telegram_webhook.py  # Script de configuração do webhook
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