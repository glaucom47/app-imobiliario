"""
Gerenciamento de conexões e sessões do PostgreSQL via SQLAlchemy.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from config.config import settings

# Configuração do Engine com pool de conexões
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Fábrica de sessões do banco de dados
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base declarativa para todos os modelos ORM
Base = declarative_base()


def get_db():
    """
    Dependência injetável do FastAPI para obter sessão do banco de dados.
    Garante fechamento correto após cada requisição.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
