"""
Gerenciamento de conexões e sessões de banco de dados via SQLAlchemy.
Suporta PostgreSQL corporativo com pool de conexões (produção e dev)
e fallback resiliente para SQLite local de desenvolvimento caso o PostgreSQL
local não esteja configurado ou ocorra falha de autenticação.
"""
import logging
import os
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker

from config.config import settings

logger = logging.getLogger("fecho.database")

Base = declarative_base()


def _init_engine():
    db_url = settings.DATABASE_URL
    is_postgres = db_url.startswith("postgresql")

    if is_postgres:
        try:
            # Tenta estabelecer conexão de teste com PostgreSQL
            pg_engine = create_engine(
                db_url,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
                connect_args={"connect_timeout": 3},
            )
            with pg_engine.connect() as conn:
                pass
            return pg_engine
        except (OperationalError, Exception) as exc:
            logger.warning(
                "Aviso: Não foi possível conectar ao PostgreSQL em '%s' (%s). "
                "Ativando fallback automático para base de dados local SQLite (database/fecho_dev.db) para desenvolvimento.",
                db_url,
                exc,
            )

    # Fallback para SQLite local de desenvolvimento
    sqlite_file = os.path.join(settings.BASE_DIR, "database", "fecho_dev.db")
    sqlite_url = f"sqlite:///{sqlite_file}"
    sqlite_engine = create_engine(
        sqlite_url,
        connect_args={"check_same_thread": False},
    )
    return sqlite_engine


engine = _init_engine()

# Fábrica de sessões do banco de dados
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


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


def ensure_initialized():
    """
    Garante que as tabelas existem e executa o seed inicial de demonstração
    caso a base de dados ainda não possua nenhum utilizador.
    """
    from app.models.tenant import Tenant
    from app.models.user import User
    from app.models.property import Property
    from app.models.visit import Visit
    from app.models.objection import ObjectionTag, VisitObjection
    from app.models.contact import Contact
    from app.models.settings import Settings
    from app.models.log import Log

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            from database.seed import seed_database
            seed_database(db=db)
    except Exception as e:
        logger.warning("Aviso durante a inicialização automática do banco: %s", e)
    finally:
        db.close()
