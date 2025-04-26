from logging.config import fileConfig
import sys
import os

# Adiciona o diretório raiz do projeto ao path do Python
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Imports atualizados para a nova estrutura de pacotes
from lima.models import table_registry
from lima.settings import DATABASE_URL

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Converte URL assíncrona para síncrona para o Alembic
sync_url = DATABASE_URL
if sync_url.startswith('sqlite+aiosqlite:'):
    sync_url = sync_url.replace('sqlite+aiosqlite:', 'sqlite:')
elif sync_url.startswith('postgresql+asyncpg:'):
    sync_url = sync_url.replace('postgresql+asyncpg:', 'postgresql+psycopg:')

# Sobrescreve a URL do banco de dados definida no alembic.ini
config.set_main_option("sqlalchemy.url", sync_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = table_registry.metadata

# Configurações específicas para PostgreSQL
postgres_config = {
    # Usar transações para DDL (mais seguro em produção)
    "transaction_per_migration": True,
    # Forçar o uso de schema qualificado nos comandos de migração
    "include_schemas": True,
}

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **postgres_config,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            **postgres_config,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
