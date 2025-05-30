# Projeto Lima - API de Endereços e Bot Telegram

![Status](https://img.shields.io/badge/Status-Em%20Desenvolvimento-yellow)
![Versão](https://img.shields.io/badge/Versão-0.2.0-blue)
![Python](https://img.shields.io/badge/Python-3.12+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green)
![Documentação](https://img.shields.io/badge/Documentação-95%25-brightgreen)

## 📋 Descrição

O **Projeto Lima** é uma solução completa para gestão inteligente de endereços com interface dual: **API REST** profissional e **Bot Telegram** intuitivo. Oferece funcionalidades avançadas como sistema de sugestões colaborativo, anotações personalizadas, auditoria completa e autenticação hierárquica.

### 🎯 **Casos de Uso Principais**
- **Empresas de logística**: Gestão centralizada de endereços de entrega
- **Prestadores de serviço**: Base organizada de locais de atendimento  
- **Administração pública**: Catalogação sistemática de endereços municipais
- **Condomínios e prédios**: Registro estruturado de unidades e moradores

### ✨ Principais Diferenciais

- **🤖 Interface Dual**: API REST completa + Bot Telegram conversacional
- **📝 Sistema de Anotações**: Observações personalizadas vinculadas a endereços
- **🔐 Autenticação Hierárquica**: JWT com 3 níveis de acesso (básico, intermediário, super)
- **💡 Sugestões Colaborativas**: Workflow completo de propostas e aprovação
- **📊 Auditoria Completa**: Rastreamento detalhado de alterações e consultas
- **🔍 Busca Avançada**: Filtros por operadora, tipo, região e campos customizados
- **📋 Logs Inteligentes**: Histórico detalhado com políticas de retenção
- **🏗️ Arquitetura Modular**: Design extensível e bem documentado

> ⚠️ **Status**: Projeto em desenvolvimento ativo (última atualização: maio/2025). **Não recomendado para produção.**

## 🚀 Funcionalidades

### ✅ **Implementadas e Documentadas**

#### 🏗️ **API REST Completa**
- **41 endpoints** documentados com exemplos práticos
- **6 módulos principais**: Usuários, Endereços, Anotações, Sugestões, Buscas, Alterações
- **Autenticação JWT** com refresh tokens e expiração configurável
- **Documentação OpenAPI** interativa (Swagger/ReDoc)

#### 👥 **Sistema de Usuários**
- **3 níveis hierárquicos**: Básico, Intermediário, Super Usuário
- **Gestão completa**: CRUD, ativação, permissões granulares
- **Auditoria**: Histórico de ações por usuário

#### 🏠 **Gestão de Endereços**
- **CRUD completo** com validações robustas
- **Busca avançada** por operadora, região, tipo
- **Sistema de operadoras** configurável
- **Geocodificação** e normalização de dados

#### 📝 **Sistema de Anotações**
- **Anotações vinculadas** a endereços específicos
- **Controle de autoria** e histórico de edições
- **Tipos configuráveis**: observação, alerta, nota técnica

#### 💡 **Sistema de Sugestões**
- **Workflow completo**: proposta → revisão → aprovação/rejeição
- **3 tipos**: novos endereços, alterações, correções
- **Controle de permissões** para aprovar/rejeitar
- **Histórico detalhado** de decisões

#### 🔍 **Auditoria e Logs**
- **Rastreamento completo** de alterações (who, what, when)
- **Logs de consulta** com estatísticas detalhadas
- **Políticas de retenção** configuráveis
- **Relatórios gerenciais** para administradores

#### 🤖 **Bot Telegram**
- **Interface conversacional** intuitiva
- **Comandos especializados** por funcionalidade
- **Teclados inline** para navegação
- **Autenticação integrada** com a API

### 🔄 **Em Desenvolvimento**

- **Sistema de notificações** push
- **Interface web administrativa** (dashboard)
- **Exportação de dados** (CSV, Excel, JSON)
- **Integração com WhatsApp Business**
- **Sistema de backup** automatizado
- **API de geolocalização** avançada

## 📊 **Status do Projeto**

### 📈 **Progresso Geral: 95%** ⭐

| Categoria | Progresso | Status |
|-----------|-----------|--------|
| **🏗️ Arquitetura** | 100% | ✅ Completa |
| **🔌 API REST** | 100% | ✅ 41 endpoints documentados |
| **🤖 Bot Telegram** | 90% | 🟡 Funcional, melhorias em andamento |
| **📚 Documentação** | 95% | ✅ Documentação enterprise completa |
| **🧪 Testes** | 75% | 🟡 Cobertura expandindo |
| **🚀 Deploy** | 85% | 🟡 Docker pronto, CI/CD em implementação |

### 📋 **Métricas Técnicas**

- **🎯 18 documentos** técnicos criados
- **📡 41 endpoints** da API documentados  
- **🏗️ 6 módulos** principais implementados
- **📝 150+ exemplos** práticos incluídos
- **🔐 3 níveis** de autenticação hierárquica
- **📊 6 tipos** de relatórios de auditoria

## 🛠️ **Tecnologias Utilizadas**

### **Backend & API**

- **FastAPI**: Framework web assíncrono de alta performance
- **SQLAlchemy 2.0**: ORM moderno com suporte total a async/await
- **Pydantic V2**: Validação rigorosa de dados e serialização
- **Alembic**: Sistema de migração de banco de dados
- **APScheduler**: Agendamento de tarefas e jobs periódicos

### **Banco de Dados**

- **SQLite**: Desenvolvimento e testes locais
- **PostgreSQL**: Ambiente de produção (via AsyncPG)

### **Integrações & Comunicação**

- **python-telegram-bot**: SDK oficial para API do Telegram
- **HTTPX**: Cliente HTTP assíncrono moderno
- **PyJWT**: Manipulação segura de tokens JWT

### **Ferramentas de Desenvolvimento**

- **Poetry**: Gerenciamento moderno de dependências
- **Ruff**: Linting ultra-rápido e formatação de código
- **Pytest**: Framework de testes com fixtures avançadas
- **Coverage.py**: Análise detalhada de cobertura de testes
- **Docker & Docker Compose**: Containerização e orquestração

## 📦 **Estrutura do Projeto**

```text
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

### 🗃️ **Outros Arquivos Importantes**

```text
├── migrations/            # Scripts de migração do Alembic
├── tests/                 # Suíte de testes automatizados
├── docs/                  # Documentação completa do projeto
├── alembic.ini           # Configuração do Alembic
├── pyproject.toml        # Configuração do Poetry e ferramentas
├── docker-compose.yml    # Orquestração de containers
├── Dockerfile            # Imagem Docker para produção
└── configure_telegram_webhook.py  # Script de configuração do webhook
```

## 🚀 **Instalação Rápida**

### **📋 Pré-requisitos**

- **Python 3.12+**
- **Poetry** (gerenciador de dependências)
- **Bot do Telegram** configurado (obtenha o token via [@BotFather](https://t.me/botfather))

### **⚡ Método 1: Docker (Recomendado)**

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/lima.git
cd lima

# 2. Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com seus tokens e configurações

# 3. Suba os serviços
docker-compose up -d

# 4. Verifique os logs
docker-compose logs -f
```

### **🛠️ Método 2: Desenvolvimento Local**

```bash
# 1. Clone e acesse o diretório
git clone https://github.com/seu-usuario/lima.git
cd lima

# 2. Instale dependências
poetry install

# 3. Configure variáveis de ambiente
cp .env.example .env
# Edite com suas configurações

# 4. Execute migrações
poetry run alembic upgrade head

# 5. Inicie o servidor
poetry run uvicorn lima.app:app --reload

# 6. Configure webhook do Telegram (opcional)
poetry run python configure_telegram_webhook.py
```

### **⚙️ Configuração Essencial**

Edite o arquivo `.env` com suas configurações:

```env
# Telegram
TELEGRAM_BOT_TOKEN=seu_token_aqui
TELEGRAM_WEBHOOK_URL=https://seudominio.com/webhook/telegram
TELEGRAM_SECRET_TOKEN=token_secreto_opcional

# Banco de Dados
DATABASE_URL=sqlite:///./app.db  # Para desenvolvimento
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost/lima  # Para produção

# API
SECRET_KEY=sua_chave_secreta_jwt
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## 📚 **Documentação Completa**

> 🎯 **95% da documentação está completa!** Acesse o índice completo em [`docs/README.md`](docs/README.md)

### **🚀 Para Começar**
- [⚡ Guia de Início Rápido](docs/getting-started/quick-start.md)
- [❓ FAQ - Perguntas Frequentes](docs/troubleshooting/faq.md)
- [🔧 Configuração Detalhada](docs/getting-started/configuration.md)

### **🏗️ Para Desenvolvedores**
- [📡 API REST Completa](docs/api/overview.md) - 41 endpoints documentados
- [🏗️ Arquitetura do Sistema](docs/architecture/overview.md)
- [🤖 Documentação do Bot](docs/bot/workflows.md)
- [🧪 Guia de Testes](docs/development/testing-guide.md)
- [🐳 Deploy com Docker](docs/deployment/docker.md)

### **🔌 Endpoints da API**
- [👥 Usuários](docs/api/endpoints/users.md)
- [🏠 Endereços](docs/api/endpoints/addresses.md)  
- [📝 Anotações](docs/api/endpoints/annotations.md)
- [💡 Sugestões](docs/api/endpoints/suggestions.md)
- [🔍 Buscas/Logs](docs/api/endpoints/searches.md)
- [📋 Alterações/Auditoria](docs/api/endpoints/changes.md)

## 🤝 **Contribuição**

Quer contribuir? Fantástico! Consulte nosso [Guia de Contribuição](docs/contributing.md) para instruções detalhadas.

### **🐛 Encontrou um Bug?**
- Abra uma **Issue** descrevendo o problema
- Inclua detalhes do ambiente (OS, Python, versões)
- Se possível, inclua logs e passos para reproduzir

### **💡 Tem uma Ideia?**
- Abra uma **Issue** com tag de `enhancement`
- Descreva a funcionalidade proposta
- Discuta a implementação antes de criar um PR

## 📄 **Licença**

Este projeto está licenciado sob a **Licença MIT** - veja o arquivo [LICENSE](LICENSE) para detalhes.

## ✒️ **Autor**

**Desenvolvido com ❤️ por [Matheus Lima](https://github.com/matheus-lima-silva)**

---

<div align="center">

**⭐ Se este projeto foi útil, considere dar uma estrela!**

[![GitHub stars](https://img.shields.io/github/stars/seu-usuario/lima.svg?style=social&label=Star)](https://github.com/seu-usuario/lima)
[![GitHub forks](https://img.shields.io/github/forks/seu-usuario/lima.svg?style=social&label=Fork)](https://github.com/seu-usuario/lima/fork)

</div>