# Guia de Instalação

Este guia explica como configurar o Projeto Lima para desenvolvimento local.

> ⚠️ **Aviso**: Este projeto ainda está em desenvolvimento e não é recomendado para uso em produção.

## Pré-requisitos

- Python 3.10 ou superior
- [Poetry](https://python-poetry.org/) (gerenciador de dependências)
- [Git](https://git-scm.com/)

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

## Configuração da integração com WhatsApp (Opcional)

Para configurar a integração com WhatsApp, consulte o guia específico:
[Configuração do WhatsApp](whatsapp-setup.md)

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
└── services/              # Serviços externos e lógica de negócios
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

## Próximos Passos

Após a instalação, você pode:

1. Acessar o sistema usando o usuário administrador criado automaticamente
   - Telefone: definido pela variável de ambiente `ADMIN_PHONE` (padrão: +5521982427418)
   - Nome: definido pela variável de ambiente `ADMIN_NAME` (padrão: Administrador)
   - Nível de acesso: super_usuario

2. Explorar a API através da interface Swagger

3. Configurar a integração com WhatsApp para testes

## Configuração do Administrador

Por padrão, o sistema cria automaticamente um usuário administrador com os dados definidos nas variáveis de ambiente. Para personalizar estas informações, edite o arquivo `.env` antes de iniciar o sistema pela primeira vez:

```
# Administrador
ADMIN_PHONE=+5521982427418  # Substitua pelo número desejado
ADMIN_NAME=Administrador    # Substitua pelo nome desejado
```

**Nota**: O número de telefone deve estar no formato internacional (com o código do país).