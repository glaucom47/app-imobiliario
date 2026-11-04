"""
Gerenciamento de conexões e sessões de banco de dados via SQLAlchemy.
Suporta PostgreSQL corporativo com pool de conexões (produção e dev)
e fallback resiliente para SQLite local de desenvolvimento caso o PostgreSQL
local não esteja configurado ou ocorra falha de autenticação.
"""
import logging
import os
from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker

from config.config import normalize_database_url, settings

logger = logging.getLogger("fecho.database")

Base = declarative_base()


def _redact_db_url(raw_url: str) -> str:
    """Oculta credenciais da URL de banco de dados antes de registrar em logs."""
    try:
        return make_url(raw_url).render_as_string(hide_password=True)
    except Exception:
        return "<database_url_redacted>"


def _init_engine():
    db_url = normalize_database_url(settings.DATABASE_URL)
    safe_url = _redact_db_url(db_url)
    is_postgres = db_url.startswith("postgresql")

    if is_postgres:
        try:
            # Tenta estabelecer conexão de teste com PostgreSQL
            pg_engine = create_engine(
                db_url,
                pool_pre_ping=True,
                pool_use_lifo=True,
                pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
                max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "5")),
                pool_recycle=1800,
                connect_args={
                    "connect_timeout": 5,
                    "keepalives": 1,
                    "keepalives_idle": 30,
                    "keepalives_interval": 10,
                    "keepalives_count": 5,
                },
            )
            with pg_engine.connect() as conn:
                pass
            return pg_engine
        except (OperationalError, Exception) as exc:
            if settings.ENVIRONMENT == "production":
                # Durante a fase de Build de containers PaaS (ex: Railway Nixpacks),
                # o host interno 'postgres.railway.internal' ainda não está acessível
                # na rede privada (só fica disponível na fase de Deploy/Start).
                if "railway.internal" in db_url and "alembic" in " ".join(os.sys.argv).lower():
                    logger.warning(
                        "Build PaaS detectado: host privado '%s' indisponível durante a construção da imagem. "
                        "A migração Alembic será executada no arranque do container (Start Command).",
                        safe_url,
                    )
                    return pg_engine

                logger.error(
                    "Erro Crítico: Não foi possível conectar ao PostgreSQL de produção em '%s': %s. "
                    "O fallback para SQLite está estritamente bloqueado em ambiente de produção.",
                    safe_url,
                    exc,
                )
                raise RuntimeError(
                    f"Falha de conexão com o banco de dados PostgreSQL gerenciado em produção: {exc}"
                ) from exc

            logger.warning(
                "Aviso: Não foi possível conectar ao PostgreSQL em '%s' (%s). "
                "Ativando fallback automático para base de dados local SQLite (database/fecho_dev.db) para desenvolvimento.",
                safe_url,
                exc,
            )

    if settings.ENVIRONMENT == "production":
        raise RuntimeError(
            "Configuração Insegura: O ambiente de produção (ENVIRONMENT=production) exige banco de dados "
            "PostgreSQL configurado na variável DATABASE_URL."
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

    # Em produção PaaS (Railway/Render), se o build-stage do Alembic foi pulado porque
    # a rede privada estava desligada no Build, garante que as migrações Alembic rodem no arranque.
    if settings.ENVIRONMENT == "production":
        try:
            from sqlalchemy import inspect
            inspector = inspect(engine)
            if not inspector.has_table("users"):
                from alembic.config import Config
                from alembic import command
                alembic_cfg = Config(os.path.join(settings.BASE_DIR, "alembic.ini"))
                command.upgrade(alembic_cfg, "head")
        except Exception as exc:
            logger.warning("Aviso ao verificar/aplicar migrações Alembic no arranque: %s", exc)
        return

    Base.metadata.create_all(bind=engine)

    if not settings.SEED_DEMO:
        return

    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            from database.seed import seed_database
            seed_database(db=db)
    except Exception as e:
        logger.warning("Aviso durante a inicialização automática do banco: %s", e)
    finally:
        db.close()
