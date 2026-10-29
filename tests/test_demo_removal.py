"""
Testes da remoção do acesso demo e da flag explícita SEED_DEMO.

Valida:
1. index.html, backoffice.html e app.js não expõem botões/credenciais demo nem auto-login;
2. seed_database recusa correr sem SEED_DEMO=true ou em produção;
3. validate_production_settings recusa SEED_DEMO=true em produção;
4. Script administrativo desativa as contas demo (simulação por omissão, --confirm aplica)
   e as credenciais públicas deixam de autenticar.
"""
import importlib.util
import pathlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from database.connection import Base, get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth_service import hash_password

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load_admin_script():
    spec = importlib.util.spec_from_file_location(
        "disable_demo_accounts", ROOT / "scripts" / "disable_demo_accounts.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("rel", ["static/index.html", "static/backoffice.html", "static/js/app.js"])
def test_frontend_sem_acesso_demo(rel):
    txt = (ROOT / rel).read_text(encoding="utf-8")
    for proibido in ("btn-demo-consultor", "btn-demo-diretor", "bo-btn-demo-",
                     "demo-credentials-box", "senha_segura_", "Acesso de Teste"):
        assert proibido not in txt, f"{rel} ainda contém '{proibido}'"


def test_seed_bloqueado_sem_flag_e_em_producao():
    from config.config import settings
    from database.seed import seed_database

    orig_env, orig_seed = settings.ENVIRONMENT, settings.SEED_DEMO
    try:
        settings.ENVIRONMENT, settings.SEED_DEMO = "development", False
        with pytest.raises(RuntimeError, match="SEED_DEMO"):
            seed_database(db=object())
        settings.ENVIRONMENT, settings.SEED_DEMO = "production", True
        with pytest.raises(RuntimeError, match="SEED_DEMO"):
            seed_database(db=object())
    finally:
        settings.ENVIRONMENT, settings.SEED_DEMO = orig_env, orig_seed


def test_producao_recusa_seed_demo():
    from config.config import Settings

    orig = (Settings.ENVIRONMENT, Settings.SECRET_KEY, Settings.SEED_DEMO)
    try:
        Settings.ENVIRONMENT = "production"
        Settings.SECRET_KEY = "x" * 64
        Settings.SEED_DEMO = True
        with pytest.raises(ValueError, match="SEED_DEMO"):
            Settings.validate_production_settings()
        Settings.SEED_DEMO = False
        Settings.validate_production_settings()
    finally:
        Settings.ENVIRONMENT, Settings.SECRET_KEY, Settings.SEED_DEMO = orig


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    tenant = Tenant(nome="Demo", slug="demo", nif="500000000", ativo=True)
    session.add(tenant)
    session.flush()
    for email, role, pwd in (("diretor@fecho.pt", "diretor", "senha_segura_diretor"),
                             ("consultor@fecho.pt", "consultor", "senha_segura_consultor"),
                             ("real@agencia.pt", "diretor", "OutraSenha#2026")):
        session.add(User(agencia_id=tenant.id, nome=email, email=email,
                         password_hash=hash_password(pwd), role=role, ativo=True))
    session.commit()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_script_desativa_contas_demo(db_session):
    mod = _load_admin_script()

    # Simulação: não altera nada
    afetados = mod.disable_demo_accounts(db_session, confirm=False)
    assert sorted(afetados) == ["consultor@fecho.pt", "diretor@fecho.pt"]
    assert all(u.ativo for u in db_session.query(User).all())

    # Aplicação real
    mod.disable_demo_accounts(db_session, confirm=True)
    estado = {u.email: u.ativo for u in db_session.query(User).all()}
    assert estado == {"diretor@fecho.pt": False, "consultor@fecho.pt": False, "real@agencia.pt": True}

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            r = client.post("/api/v1/auth/login",
                            json={"email": "diretor@fecho.pt", "password": "senha_segura_diretor"})
            assert r.status_code in (401, 403)
            ok = client.post("/api/v1/auth/login",
                             json={"email": "real@agencia.pt", "password": "OutraSenha#2026"})
            assert ok.status_code == 200
    finally:
        app.dependency_overrides.clear()
