#!/bin/sh

echo "Aplicando migrações do banco de dados..."
ALEMBIC=1 poetry run alembic upgrade head

echo "Iniciando a aplicação com logging detalhado..."
poetry run uvicorn lima.app:app --host 0.0.0.0 --port 8000 --log-level debug --reload