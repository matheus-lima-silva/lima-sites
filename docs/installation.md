# Guia de Instalação

Este guia explica como configurar o Projeto Lima para desenvolvimento local.

> ⚠️ **Atualização (Maio/2025)**: Este projeto está em desenvolvimento ativo e pode sofrer mudanças frequentes. Esta documentação foi atualizada em maio de 2025.

## Status de Implementação

- ✅ Sistema de autenticação e controle de acesso
- ✅ Gerenciamento de usuários e níveis de permissão
- ✅ CRUD completo de endereços
- ✅ Sistema de anotações em endereços
- ✅ Registro de alterações e histórico
- ✅ Sistema de sugestões
- ✅ Integração com Telegram
- 🚧 Integração com WhatsApp (em desenvolvimento)
- 🚧 Módulo de estatísticas de uso (em desenvolvimento)

## Pré-requisitos

- Python 3.10 ou superior
- [Poetry](https://python-poetry.org/) (gerenciador de dependências)
- [Git](https://git-scm.com/)
- PostgreSQL 14+ (para ambiente de produção)

## Instalação Passo a Passo

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/lima.git
cd lima
```

### 2. Instale as dependências com Poetry

```bash
# Instalar o Poetry (caso não tenha)
curl -sSL https://install.python-poetry.org | python3 -

# Instalar as dependências do projeto
poetry install
```

### 3. Configure o ambiente

```bash
# Crie um arquivo .env a partir do exemplo
cp .env.example .env

# Edite o arquivo .env com suas configurações
# Exemplo:
# DATABASE_URL=sqlite:///./dev.db
# SECRET_KEY=sua_chave_secreta_aqui
```

Variáveis de ambiente importantes:
- `DATABASE_URL`: URL de conexão com o banco de dados
- `SECRET_KEY`: Chave secreta para assinatura de tokens
- `DEBUG`: True para ambiente de desenvolvimento, False para produção
- `ADMIN_PHONE`: Telefone do administrador inicial
- `ADMIN_NAME`: Nome do administrador inicial

### 4. Execute as migrações do banco de dados

```bash
# Ative o ambiente virtual criado pelo Poetry
poetry shell

# Execute as migrações
alembic upgrade head
```

### 5. Iniciar o servidor de desenvolvimento

```bash
# Com o ambiente virtual ativado
uvicorn lima.app:app --reload

# Ou sem ativar o ambiente virtual
poetry run uvicorn lima.app:app --reload
```

O servidor estará disponível em `http://localhost:8000`.

### 6. Acessar a documentação da API

Com o servidor em execução, você pode acessar:

- Documentação Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Documentação ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Configuração da integração com WhatsApp (Em Desenvolvimento)

> 🚧 **Nota importante**: A integração com WhatsApp está em fase inicial de desenvolvimento (maio/2025) e não está completamente implementada.

A documentação preliminar para a integração com WhatsApp está disponível em:
[Configuração do WhatsApp](whatsapp-setup.md)

Quando disponível, esta integração permitirá a consulta e gerenciamento de endereços diretamente via mensagens de WhatsApp.

## Estrutura de Diretórios

```
lima/
├── app.py                 # Ponto de entrada da aplicação
├── models.py              # Modelos de dados
├── schemas.py             # Schemas Pydantic
├── settings.py            # Configurações
├── database.py            # Configuração do banco de dados
├── security.py            # Autenticação e segurança
├── routers/               # Endpoints da API
│   ├── auth.py            # Autenticação
│   ├── usuarios.py        # Gerenciamento de usuários
│   ├── enderecos.py       # CRUD de endereços
│   ├── sugestoes.py       # Sistema de sugestões
│   ├── alteracoes.py      # Registro de alterações
│   ├── anotacoes.py       # Sistema de anotações
│   └── ...                # Outros endpoints
└── services/              # Serviços externos e lógica de negócios
    ├── ai_service.py      # Serviço de IA para processamento
    ├── whatsapp.py        # Integração com WhatsApp
    └── telegram/          # Integração com Telegram
```

## Possíveis Problemas e Soluções

### Erro ao conectar ao banco de dados

**Problema**: `sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) unable to open database file`

**Solução**: Verifique se o caminho do banco de dados está correto e se você tem permissão para escrever no diretório.

### Erro ao executar migrações com Alembic

**Problema**: `sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called`

**Solução**: Se estiver usando SQLAlchemy assíncrono com Alembic, defina a variável de ambiente:
```bash
ALEMBIC=1 alembic revision --autogenerate -m "descrição da migração"
```

### Erro com dependências do Poetry

**Problema**: Conflitos de dependências ao instalar com Poetry

**Solução**: Atualize o Poetry e tente novamente com:
```bash
poetry update
poetry install --no-dev  # Para instalar apenas dependências de produção
```

## Próximos Passos

Após a instalação, você pode:

1. Acessar o sistema usando o usuário administrador criado automaticamente
   - Telefone: definido pela variável de ambiente `ADMIN_PHONE` (padrão: +5521982427418)
   - Nome: definido pela variável de ambiente `ADMIN_NAME` (padrão: Administrador)
   - Nível de acesso: super_usuario

2. Explorar a API através da interface Swagger

3. Configurar a integração com Telegram (já implementada) ou WhatsApp (em desenvolvimento)

## Configuração do Administrador

Por padrão, o sistema cria automaticamente um usuário administrador com os dados definidos nas variáveis de ambiente. Para personalizar estas informações, edite o arquivo `.env` antes de iniciar o sistema pela primeira vez:

```
# Administrador
ADMIN_PHONE=+5521982427418  # Substitua pelo número desejado
ADMIN_NAME=Administrador    # Substitua pelo nome desejado
```

**Nota**: O número de telefone deve estar no formato internacional (com o código do país).