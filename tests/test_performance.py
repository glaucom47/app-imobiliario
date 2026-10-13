"""
Testes de performance (regressão N+1, compressão e cache HTTP).

1. Nº de consultas SQL dos endpoints agregados ≤ limite e IGUAL para 3 e 20 consultores;
2. GZip ativo em respostas grandes;
3. Cache-Control: estáticos versionados imutáveis, sw.js revalidado, API no-store.
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.middleware.security import rate_limiter
from app.models.commercial import Goal, PipelineDeal
from app.models.objection import ObjectionTag, VisitObjection
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.user import User
from app.models.visit import Visit
from app.services.auth_service import create_access_token
from config.config import settings
from database.connection import Base, get_db

API = settings.API_V1_STR
ENDPOINTS_LIMITES = {
    f"{API}/backoffice/kpis": 10,
    f"{API}/backoffice/objections-analytics": 10,
    f"{API}/backoffice/consultores-performance": 20,
    f"{API}/backoffice/commercial-dashboard": 40,
}


def _montar_agencia(n_consultores: int):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    tenant = Tenant(nome="Perf", slug="perf", nif="509999999", ativo=True)
    session.add(tenant)
    session.commit()
    diretor = User(agencia_id=tenant.id, nome="Diretora", email="dir@perf.pt", password_hash="x", role="diretor", ativo=True)
    tag = ObjectionTag(agencia_id=tenant.id, tag="Preço", categoria="preco")
    session.add_all([diretor, tag])
    session.commit()
    hoje = date.today()
    agora = datetime.now(timezone.utc)
    for i in range(n_consultores):
        c = User(agencia_id=tenant.id, nome=f"Consultor {i:02d}", email=f"c{i}@perf.pt",
                 password_hash="x", role="consultor", ativo=True)
        session.add(c)
        session.commit()
        session.add(Goal(agencia_id=tenant.id, consultor_id=c.id, ano=hoje.year, mes=hoje.month,
                         meta_faturacao=Decimal("12000.00")))
        p = Property(agencia_id=tenant.id, consultor_id=c.id, titulo=f"Imóvel {i}", tipologia="T2",
                     preco=Decimal("250000.00"), status="Vendido" if i % 2 else "Ativo",
                     nome_proprietario="Prop", telefone_proprietario="912345678",
                     nome_comprador="Comp" if i % 2 else None, telefone_comprador="913333333" if i % 2 else None,
                     data_escritura=hoje if i % 2 else None)
        session.add(p)
        session.commit()
        v = Visit(agencia_id=tenant.id, property_id=p.id, consultor_id=c.id,
                  data_visita=agora - timedelta(days=1), nivel_interesse=3)
        session.add(v)
        session.commit()
        session.add(VisitObjection(agencia_id=tenant.id, visit_id=v.id, property_id=p.id, tag_id=tag.id))
        session.add(PipelineDeal(agencia_id=tenant.id, consultor_id=c.id, property_id=p.id,
                                 cliente_nome="Cliente Perf", cliente_telefone="914444444", tipo_negocio="Venda",
                                 valor_imovel=Decimal("250000.00"), comissao_estimada=Decimal("6000.00"),
                                 fase="Proposta", probabilidade=50, data_prevista_fecho=hoje))
        session.commit()
    token = create_access_token({"sub": str(diretor.id), "agencia_id": tenant.id, "role": "diretor"})
    return engine, session, token


def _contar_consultas(n_consultores: int) -> dict:
    engine, session, token = _montar_agencia(n_consultores)

    def _override():
        yield session

    app.dependency_overrides[get_db] = _override
    contador = {"n": 0}

    def _cb(*_args, **_kwargs):
        contador["n"] += 1

    event.listen(engine, "before_cursor_execute", _cb)
    resultado = {}
    try:
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {token}"}
        for ep in ENDPOINTS_LIMITES:
            session.expire_all()
            contador["n"] = 0
            resp = client.get(ep, headers=headers)
            assert resp.status_code == 200, (ep, resp.text)
            resultado[ep] = contador["n"]
    finally:
        event.remove(engine, "before_cursor_execute", _cb)
        app.dependency_overrides.clear()
        session.close()
    return resultado


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    if hasattr(rate_limiter, "requests"):
        rate_limiter.requests.clear()
    yield


def test_endpoints_agregados_sem_n_mais_1():
    pequeno = _contar_consultas(3)
    grande = _contar_consultas(20)
    for ep, limite in ENDPOINTS_LIMITES.items():
        assert pequeno[ep] <= limite, f"{ep}: {pequeno[ep]} consultas (limite {limite})"
        assert pequeno[ep] == grande[ep], f"{ep}: N+1 detetado ({pequeno[ep]} vs {grande[ep]} consultas)"


def test_gzip_em_respostas_grandes():
    client = TestClient(app)
    resp = client.get("/static/js/api.js?v=15", headers={"Accept-Encoding": "gzip"})
    assert resp.status_code == 200
    assert resp.headers.get("content-encoding") == "gzip"


def test_cache_control_estaticos_e_api():
    client = TestClient(app)
    versionado = client.get("/static/css/style.css?v=15")
    assert "immutable" in versionado.headers.get("Cache-Control", "")
    assert "max-age=31536000" in versionado.headers.get("Cache-Control", "")

    sem_versao = client.get("/static/css/style.css")
    assert sem_versao.headers.get("Cache-Control") == "public, max-age=3600"

    sw = client.get("/static/sw.js")
    assert sw.headers.get("Cache-Control") == "no-cache"

    api = client.get(f"{API}/backoffice/kpis")
    assert "no-store" in api.headers.get("Cache-Control", "")
