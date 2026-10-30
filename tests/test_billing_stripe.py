"""
Testes da Fase B de faturação (Stripe), sem acesso à rede:
checkout/portal simulados e webhooks assinados localmente com o segredo de teste.
"""
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from config.config import settings
from database.connection import Base, get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services import stripe_service
from app.services.auth_service import create_access_token, hash_password

API = "/api/v1"
WHSEC = "whsec_teste_local_123"


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def stripe_cfg(monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_x")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", WHSEC)
    monkeypatch.setattr(settings, "STRIPE_PRICE_MENSAL", "price_mensal")
    monkeypatch.setattr(settings, "STRIPE_PRICE_ANUAL", "price_anual")
    monkeypatch.setattr(settings, "STRIPE_TAX_RATE_ID", "txr_iva23")
    monkeypatch.setattr(settings, "APP_BASE_URL", "https://meufecho.pt")


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _agencia(db, slug, expirada=False):
    t = Tenant(nome=slug, slug=slug, ativo=True, plano_status="trial",
               trial_termina_em=datetime.now(timezone.utc) + timedelta(days=-1 if expirada else 7))
    db.add(t)
    db.flush()
    d = User(agencia_id=t.id, nome="D", email=f"d@{slug}.pt", role="diretor",
             password_hash=hash_password("SenhaForte#1"), ativo=True)
    c = User(agencia_id=t.id, nome="C", email=f"c@{slug}.pt", role="consultor",
             password_hash=hash_password("SenhaForte#1"), ativo=True)
    db.add_all([d, c])
    db.commit()
    tok = lambda u: {"Authorization": "Bearer " + create_access_token(
        {"sub": str(u.id), "agencia_id": t.id, "role": u.role})}
    return t, tok(d), tok(c)


def _assinar(evento: dict, segredo=WHSEC):
    payload = json.dumps(evento)
    ts = int(time.time())
    sig = hmac.new(segredo.encode(), f"{ts}.{payload}".encode(), hashlib.sha256).hexdigest()
    return payload, {"Stripe-Signature": f"t={ts},v1={sig}", "Content-Type": "application/json"}


def _webhook(client, tipo, obj, segredo=WHSEC):
    payload, headers = _assinar({"id": "evt_1", "type": tipo, "data": {"object": obj}}, segredo)
    return client.post(f"{API}/billing/webhook", content=payload, headers=headers)


def test_sem_configuracao_responde_503(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "")
    _, h_dir, _ = _agencia(db_session, "a")
    assert client.post(f"{API}/billing/checkout", json={"periodo": "mensal"}, headers=h_dir).status_code == 503
    st = client.get(f"{API}/billing/status", headers=h_dir).json()
    assert st["pagamento_online_disponivel"] is False


def test_checkout_so_diretor_e_parametros_definidos_pelo_servidor(client, db_session, stripe_cfg, monkeypatch):
    t, h_dir, h_cons = _agencia(db_session, "a", expirada=True)
    capturado = {}

    def fake_create(**params):
        capturado.update(params)
        return {"url": "https://checkout.stripe.com/c/pay/cs_test_1"}

    monkeypatch.setattr(stripe_service.stripe.checkout.Session, "create", staticmethod(fake_create))

    assert client.post(f"{API}/billing/checkout", json={"periodo": "anual"}, headers=h_cons).status_code == 403
    # Mesmo com trial expirado (modo só leitura), o checkout continua acessível
    r = client.post(f"{API}/billing/checkout", json={"periodo": "anual"}, headers=h_dir)
    assert r.status_code == 200
    assert r.json()["url"].startswith("https://checkout.stripe.com/")
    assert capturado["client_reference_id"] == str(t.id)
    assert capturado["line_items"] == [{"price": "price_anual", "quantity": 1, "tax_rates": ["txr_iva23"]}]
    assert capturado["mode"] == "subscription"
    assert capturado["customer_email"] == "d@a.pt"
    assert capturado["success_url"].startswith("https://meufecho.pt/")


def test_checkout_rejeita_periodo_invalido(client, db_session, stripe_cfg):
    _, h_dir, _ = _agencia(db_session, "a")
    assert client.post(f"{API}/billing/checkout", json={"periodo": "vitalicio"}, headers=h_dir).status_code == 422


def test_webhook_rejeita_assinatura_invalida(client, stripe_cfg):
    r = _webhook(client, "checkout.session.completed", {"client_reference_id": "1"}, segredo="whsec_errado")
    assert r.status_code == 400
    r2 = client.post(f"{API}/billing/webhook", content="{}", headers={"Content-Type": "application/json"})
    assert r2.status_code == 400


def test_ciclo_de_vida_da_subscricao(client, db_session, stripe_cfg):
    t, h_dir, _ = _agencia(db_session, "a", expirada=True)
    novo = {"nome": "Novo", "email": "n@a.pt", "password": "SenhaForte#1"}
    assert client.post(f"{API}/backoffice/consultores", json=novo, headers=h_dir).status_code == 402

    # Pagamento concluído -> ativo
    r = _webhook(client, "checkout.session.completed", {
        "client_reference_id": str(t.id), "customer": "cus_A", "subscription": "sub_A",
        "metadata": {"agencia_id": str(t.id), "periodo": "anual"},
    })
    assert r.status_code == 200
    db_session.refresh(t)
    assert (t.plano_status, t.stripe_customer_id, t.plano_periodo) == ("ativo", "cus_A", "anual")
    assert client.post(f"{API}/backoffice/consultores", json=novo, headers=h_dir).status_code == 201

    # Reenvio do mesmo evento é idempotente
    assert _webhook(client, "checkout.session.completed", {
        "client_reference_id": str(t.id), "customer": "cus_A", "subscription": "sub_A",
        "metadata": {"periodo": "anual"}}).status_code == 200
    db_session.refresh(t)
    assert t.plano_status == "ativo"

    # Fatura paga -> validade atualizada
    fim = int((datetime.now(timezone.utc) + timedelta(days=365)).timestamp())
    _webhook(client, "invoice.paid", {"customer": "cus_A", "lines": {"data": [{"period": {"end": fim}}]}})
    db_session.refresh(t)
    assert t.subscricao_valida_ate is not None

    # Falha de pagamento -> pendente (escrita mantida durante as novas tentativas do Stripe)
    _webhook(client, "invoice.payment_failed", {"customer": "cus_A"})
    db_session.refresh(t)
    assert t.plano_status == "pendente"

    # Stripe esgota tentativas -> unpaid -> suspenso (só leitura)
    _webhook(client, "customer.subscription.updated", {"id": "sub_A", "customer": "cus_A", "status": "unpaid"})
    db_session.refresh(t)
    assert t.plano_status == "suspenso"
    assert client.post(f"{API}/backoffice/consultores",
                       json={**novo, "email": "n2@a.pt"}, headers=h_dir).status_code == 402

    # Cancelamento
    _webhook(client, "customer.subscription.deleted", {"id": "sub_A", "customer": "cus_A"})
    db_session.refresh(t)
    assert t.plano_status == "cancelado"


def test_webhook_nao_afeta_outra_agencia(client, db_session, stripe_cfg):
    ta, _, _ = _agencia(db_session, "a")
    tb, _, _ = _agencia(db_session, "b")
    ta.stripe_customer_id = "cus_A"
    tb.stripe_customer_id = "cus_B"
    ta.plano_status = tb.plano_status = "ativo"
    db_session.commit()
    _webhook(client, "customer.subscription.deleted", {"id": "sub_A", "customer": "cus_A"})
    db_session.refresh(ta)
    db_session.refresh(tb)
    assert (ta.plano_status, tb.plano_status) == ("cancelado", "ativo")
    # Customer desconhecido é ignorado sem erro
    assert _webhook(client, "invoice.paid", {"customer": "cus_desconhecido"}).status_code == 200


def test_portal(client, db_session, stripe_cfg, monkeypatch):
    t, h_dir, h_cons = _agencia(db_session, "a")
    assert client.post(f"{API}/billing/portal", headers=h_dir).status_code == 400  # sem subscrição
    t.stripe_customer_id = "cus_A"
    db_session.commit()
    monkeypatch.setattr(stripe_service.stripe.billing_portal.Session, "create",
                        staticmethod(lambda **p: {"url": "https://billing.stripe.com/p/session/x"}))
    assert client.post(f"{API}/billing/portal", headers=h_cons).status_code == 403
    r = client.post(f"{API}/billing/portal", headers=h_dir)
    assert r.status_code == 200 and r.json()["url"].startswith("https://billing.stripe.com/")
    assert client.get(f"{API}/billing/status", headers=h_dir).json()["tem_subscricao"] is True
