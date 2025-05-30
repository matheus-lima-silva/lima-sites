FROM python:3.12-slim

WORKDIR /app

# Copiando arquivos de dependência primeiro para melhor cache
COPY pyproject.toml poetry.lock* ./

# Instalando dependências do sistema necessárias para o psycopg
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
        build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instalando o Poetry
RUN pip install poetry==1.8.2 wheel

# Configurando o Poetry para não criar um ambiente virtual
RUN poetry config virtualenvs.create false

# Instalando as dependências principais (sem dev)
RUN poetry install --no-interaction --no-ansi --without dev

# Copiando o resto do código (após dependências para cache)
COPY . .

# Garantir que o entrypoint.sh seja executável
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]