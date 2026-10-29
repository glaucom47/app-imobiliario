"""
Testes da Fase A de faturação: trial de 7 dias, modo só leitura e limite de utilizadores.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from database.connection import Base, get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services import billing_service
from app.services.auth_service import create_access_token, hash_password

API = "/api/v1"


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _registar(client, email="dir@agencia-a.pt", termos=True):
    return client.post(f"{API}/auth/register-agency", json={
        "nome_agencia": "Agência A", "nome_diretor": "Diretora A",
        "email_diretor": email, "password": "SenhaForte#1", "aceita_termos": termos,
    })


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _novo_consultor(client, token, n):
    return client.post(f"{API}/backoffice/consultores", headers=_auth(token), json={
        "nome": f"Consultor {n}", "email": f"c{n}@agencia-a.pt", "password": "SenhaForte#1",
    })


def test_registo_exige_termos(client):
    assert _registar(client, termos=False).status_code == 422


def test_registo_inicia_trial_de_7_dias(client, db_session):
    r = _registar(client)
    assert r.status_code == 201
    token = r.json()["access_token"]

    tenant = db_session.query(Tenant).one()
    assert tenant.plano_status == "trial"
    assert tenant.termos_aceites_em is not None

    st = client.get(f"{API}/billing/status", headers=_auth(token)).json()
    assert st["plano_status"] == "trial"
    assert st["escrita_permitida"] is True
    assert st["dias_restantes_trial"] == 7
    assert st["precos"]["mensal"] == {"base": 29.0, "iva_pct": 23}


def test_trial_expirado_fica_so_leitura(client, db_session):
    token = _registar(client).json()["access_token"]
    assert _novo_consultor(client, token, 1).status_code == 201

    tenant = db_session.query(Tenant).one()
    tenant.trial_termina_em = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    # Escrita bloqueada com 402
    r = _novo_consultor(client, token, 2)
    assert r.status_code == 402
    assert "consulta" in r.json()["detail"]
    # Leitura continua disponível
    assert client.get(f"{API}/backoffice/consultores", headers=_auth(token)).status_code == 200
    # Estado e autenticação continuam acessíveis
    st = client.get(f"{API}/billing/status", headers=_auth(token)).json()
    assert st["escrita_permitida"] is False and st["dias_restantes_trial"] == 0
    assert client.post(f"{API}/auth/refresh", headers=_auth(token)).status_code != 402

    # Reativação (ex.: pagamento confirmado) devolve a escrita
    tenant.plano_status = "ativo"
    db_session.commit()
    assert _novo_consultor(client, token, 3).status_code == 201


def test_limite_de_utilizadores_no_trial(client):
    token = _registar(client).json()["access_token"]  # diretor = 1
    assert _novo_consultor(client, token, 1).status_code == 201
    assert _novo_consultor(client, token, 2).status_code == 201
    r = _novo_consultor(client, token, 3)  # 4.º utilizador
    assert r.status_code == 402
    assert "Limite de utilizadores" in r.json()["detail"]


def test_agencias_legadas_nao_sao_afetadas(client, db_session):
    tenant = Tenant(nome="Legada", slug="legada", ativo=True)
    db_session.add(tenant)
    db_session.flush()
    diretor = User(agencia_id=tenant.id, nome="D", email="d@legada.pt", role="diretor",
                   password_hash=hash_password("SenhaForte#1"), ativo=True)
    db_session.add(diretor)
    db_session.commit()
    assert tenant.plano_status == "ativo"

    token = create_access_token({"sub": str(diretor.id), "agencia_id": tenant.id, "role": "diretor"})
    for n in range(1, 5):  # sem limite para agências legadas
        assert _novo_consultor(client, token, f"leg{n}").status_code == 201


def test_isolamento_entre_agencias(client, db_session):
    tok_a = _registar(client, "dir@a.pt").json()["access_token"]
    tok_b = _registar(client, "dir@b.pt").json()["access_token"]
    ta = db_session.query(Tenant).filter(Tenant.email == "dir@a.pt").one()
    ta.trial_termina_em = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.commit()
    assert client.get(f"{API}/billing/status", headers=_auth(tok_a)).json()["escrita_permitida"] is False
    assert client.get(f"{API}/billing/status", headers=_auth(tok_b)).json()["escrita_permitida"] is True


def test_escrita_permitida_por_estado():
    agora = datetime.now(timezone.utc)
    t = Tenant(nome="x", slug="x")
    for status, esperado in (("ativo", True), ("pendente", True), ("suspenso", False), ("cancelado", False)):
        t.plano_status = status
        assert billing_service.escrita_permitida(t, agora) is esperado
    t.plano_status = "trial"
    t.trial_termina_em = None
    assert billing_service.escrita_permitida(t, agora) is False
