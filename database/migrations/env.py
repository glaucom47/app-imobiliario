import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Adiciona a raiz do projeto ao path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..")))

from config.config import settings
from database.connection import Base, engine as db_engine
import app.models  # Garante registro de todas as entidades ORM para autogenerate

# Configuração de logging do Alembic
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Executa migrações no modo offline."""
    url = str(db_engine.url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Executa migrações no modo online."""
    connectable = db_engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
