"""
Testes da Reunião de Equipa (coletiva) com Presença e Atividade lançada pelo Diretor.
Cobre: criação com pré-carga, gravação em lote, histórico sem substituição, cálculo de
assiduidade (justificadas fora do denominador), RBAC (403), isolamento multi-tenant,
bloqueio após 24h com edição excecional auditada e consolidação sem duplicação nos KPIs.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.log import Log
from app.models.property import Property
from app.models.team_meeting import TeamMeeting
from app.models.tenant import Tenant
from app.models.user import User
from app.models.visit import Visit
from app.services.auth_service import create_access_token, hash_password
from database.connection import Base, get_db

BASE = "/api/v1/backoffice"


@pytest.fixture()
def ctx():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()

    ta = Tenant(nome="Tartaruga Imobiliária", slug="tartaruga", nif="509000001", ativo=True)
    tb = Tenant(nome="Outra Agência", slug="outra", nif="509000002", ativo=True)
    db.add_all([ta, tb])
    db.commit()

    def user(tenant, nome, email, role, ativo=True):
        u = User(agencia_id=tenant.id, nome=nome, email=email, password_hash=hash_password("senha123"), role=role, ativo=ativo)
        db.add(u)
        return u

    dir_a = user(ta, "Diretora A", "dir.a@t.pt", "diretor")
    c1 = user(ta, "Ana Consultora", "ana@t.pt", "consultor")
    c2 = user(ta, "Bruno Consultor", "bruno@t.pt", "consultor")
    user(ta, "Inativo", "inativo@t.pt", "consultor", ativo=False)
    dir_b = user(tb, "Diretora B", "dir.b@o.pt", "diretor")
    cb = user(tb, "Consultor B", "cb@o.pt", "consultor")
    db.commit()

    def get_db_override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = get_db_override

    def hdr(u):
        tok = create_access_token({"sub": str(u.id), "agencia_id": u.agencia_id, "role": u.role})
        return {"Authorization": f"Bearer {tok}"}

    yield {
        "client": TestClient(app), "db": db, "c1": c1, "c2": c2, "cb": cb,
        "h_dir_a": hdr(dir_a), "h_c1": hdr(c1), "h_dir_b": hdr(dir_b),
    }
    app.dependency_overrides.clear()
    db.close()


def _linha(consultor_id, presenca, **atividade):
    return {"consultor_id": consultor_id, "presenca": presenca, **atividade}


def _criar(ctx, tipo="diaria"):
    r = ctx["client"].post(f"{BASE}/team-meetings", json={"tipo": tipo}, headers=ctx["h_dir_a"])
    assert r.status_code == 201, r.text
    return r.json()


def test_criacao_pre_carrega_apenas_consultores_ativos_da_agencia(ctx):
    data = _criar(ctx)
    ids = {l["consultor_id"] for l in data["linhas"]}
    assert ids == {ctx["c1"].id, ctx["c2"].id}
    assert all(l["presenca"] == "Ausente" and l["visitas"] == 0 for l in data["linhas"])
    assert data["tipo"] == "diaria" and data["bloqueada"] is False


def test_post_sem_corpo_usa_tipo_diario(ctx):
    r = ctx["client"].post(f"{BASE}/team-meetings", headers=ctx["h_dir_a"])
    assert r.status_code == 201
    assert r.json()["tipo"] == "diaria"


def test_gravacao_em_lote_de_presenca_e_atividade(ctx):
    m = _criar(ctx)
    payload = {
        "notas_gerais": "Foco em exclusivos",
        "linhas": [
            _linha(ctx["c1"].id, "Presente", contactos=12, visitas=2, exclusivos=1, nota="Boa semana"),
            _linha(ctx["c2"].id, "Atraso", propostas=1),
        ],
    }
    r = ctx["client"].put(f"{BASE}/team-meetings/{m['id']}", json=payload, headers=ctx["h_dir_a"])
    assert r.status_code == 200, r.text
    data = r.json()
    linhas = {l["consultor_id"]: l for l in data["linhas"]}
    assert linhas[ctx["c1"].id]["contactos"] == 12
    assert linhas[ctx["c1"].id]["nota"] == "Boa semana"
    assert linhas[ctx["c2"].id]["presenca"] == "Atraso"
    assert data["total_presentes"] == 2
    assert data["notas_gerais"] == "Foco em exclusivos"


def test_valores_negativos_e_presenca_invalida_sao_rejeitados(ctx):
    m = _criar(ctx)
    url = f"{BASE}/team-meetings/{m['id']}"
    r = ctx["client"].put(url, json={"linhas": [_linha(ctx["c1"].id, "Presente", visitas=-1)]}, headers=ctx["h_dir_a"])
    assert r.status_code == 422
    r = ctx["client"].put(url, json={"linhas": [_linha(ctx["c1"].id, "Talvez")]}, headers=ctx["h_dir_a"])
    assert r.status_code == 422


def test_historico_nunca_substitui_reuniao_guardada(ctx):
    m1 = _criar(ctx)
    ctx["client"].put(f"{BASE}/team-meetings/{m1['id']}",
                      json={"linhas": [_linha(ctx["c1"].id, "Presente", visitas=4)]}, headers=ctx["h_dir_a"])
    m2 = _criar(ctx)
    assert m2["id"] != m1["id"]
    hist = ctx["client"].get(f"{BASE}/team-meetings", headers=ctx["h_dir_a"]).json()
    assert len(hist) == 2
    antiga = next(h for h in hist if h["id"] == m1["id"])
    assert next(l for l in antiga["linhas"] if l["consultor_id"] == ctx["c1"].id)["visitas"] == 4


def test_calculo_de_assiduidade_exclui_ausencias_justificadas(ctx):
    sequencia_c1 = ["Presente", "Atraso", "Ausente", "AusenciaJustificada"]
    for presenca_c1 in sequencia_c1:
        m = _criar(ctx)
        ctx["client"].put(f"{BASE}/team-meetings/{m['id']}", json={"linhas": [
            _linha(ctx["c1"].id, presenca_c1),
            _linha(ctx["c2"].id, "AusenciaJustificada" if presenca_c1 == "Ausente" else "Presente"),
        ]}, headers=ctx["h_dir_a"])

    r = ctx["client"].get(f"{BASE}/attendance-stats?dias=30", headers=ctx["h_dir_a"])
    assert r.status_code == 200
    stats = {s["consultor_id"]: s for s in r.json()["consultores"]}
    # c1: (1 Presente + 1 Atraso) / (4 - 1 justificada) = 66.7%
    assert stats[ctx["c1"].id]["assiduidade_pct"] == 66.7
    assert stats[ctx["c1"].id]["justificadas"] == 1
    # c2: 3 presentes / (4 - 1 justificada) = 100%
    assert stats[ctx["c2"].id]["assiduidade_pct"] == 100.0
    assert r.json()["total_reunioes"] == 4

    perf = ctx["client"].get(f"{BASE}/consultores-performance", headers=ctx["h_dir_a"]).json()
    perf_map = {p["consultor_id"]: p for p in perf["consultores"]}
    assert perf_map[ctx["c1"].id]["assiduidade_reunioes_pct"] == 66.7


def test_assiduidade_sem_reunioes_e_dias_invalidos(ctx):
    r = ctx["client"].get(f"{BASE}/attendance-stats?dias=7", headers=ctx["h_dir_a"])
    assert r.status_code == 200
    assert all(s["assiduidade_pct"] is None for s in r.json()["consultores"])
    assert ctx["client"].get(f"{BASE}/attendance-stats?dias=15", headers=ctx["h_dir_a"]).status_code == 422


def test_consultor_recebe_403_em_todos_os_endpoints(ctx):
    m = _criar(ctx)
    c, h = ctx["client"], ctx["h_c1"]
    assert c.post(f"{BASE}/team-meetings", json={}, headers=h).status_code == 403
    assert c.get(f"{BASE}/team-meetings", headers=h).status_code == 403
    assert c.get(f"{BASE}/team-meetings/{m['id']}", headers=h).status_code == 403
    assert c.put(f"{BASE}/team-meetings/{m['id']}", json={"linhas": []}, headers=h).status_code == 403
    assert c.get(f"{BASE}/attendance-stats", headers=h).status_code == 403


def test_isolamento_entre_agencias(ctx):
    m = _criar(ctx)
    c, hb = ctx["client"], ctx["h_dir_b"]
    assert c.get(f"{BASE}/team-meetings/{m['id']}", headers=hb).status_code == 404
    assert c.put(f"{BASE}/team-meetings/{m['id']}", json={"linhas": []}, headers=hb).status_code == 404
    assert c.get(f"{BASE}/team-meetings", headers=hb).json() == []
    stats_b = c.get(f"{BASE}/attendance-stats", headers=hb).json()
    assert {s["consultor_id"] for s in stats_b["consultores"]} == {ctx["cb"].id}


def test_nao_permite_lancar_consultor_de_outra_agencia(ctx):
    m = _criar(ctx)
    r = ctx["client"].put(f"{BASE}/team-meetings/{m['id']}",
                          json={"linhas": [_linha(ctx["cb"].id, "Presente")]}, headers=ctx["h_dir_a"])
    assert r.status_code == 422


def test_bloqueio_apos_24h_exige_edicao_excecional_auditada(ctx):
    m = _criar(ctx)
    db = ctx["db"]
    reuniao = db.get(TeamMeeting, m["id"])
    reuniao.created_at = datetime.now(timezone.utc) - timedelta(hours=25)
    db.commit()

    url = f"{BASE}/team-meetings/{m['id']}"
    body = {"linhas": [_linha(ctx["c1"].id, "Presente", visitas=1)]}
    r = ctx["client"].put(url, json=body, headers=ctx["h_dir_a"])
    assert r.status_code == 409

    r = ctx["client"].put(url, json={**body, "confirmar_edicao_excecional": True}, headers=ctx["h_dir_a"])
    assert r.status_code == 200
    assert r.json()["bloqueada"] is True
    assert r.json()["updated_by"] is not None
    assert db.query(Log).filter(Log.acao == "reuniao_equipa_edicao_excecional").count() == 1


def test_atividade_declarada_alimenta_funil_sem_duplicar(ctx):
    db, c1 = ctx["db"], ctx["c1"]
    prop = Property(agencia_id=c1.agencia_id, consultor_id=c1.id, titulo="T2 Centro", tipologia="T2",
                    preco=250000, nome_proprietario="Sr. Silva", telefone_proprietario="912000000")
    db.add(prop)
    db.commit()
    db.add(Visit(agencia_id=c1.agencia_id, property_id=prop.id, consultor_id=c1.id, nivel_interesse=3))
    db.commit()

    m = _criar(ctx)
    url_funil = f"{BASE}/sales-funnel?filtro=este_mes&consultor_id={c1.id}"

    # Visita gravada no PWA E declarada na reunião: conta 1 vez (máximo, não soma).
    ctx["client"].put(f"{BASE}/team-meetings/{m['id']}", json={"linhas": [
        _linha(c1.id, "Presente", visitas=1, contactos=40, reunioes_angariacao=6),
    ]}, headers=ctx["h_dir_a"])
    etapas = {e["etapa"]: e["quantidade"] for e in ctx["client"].get(url_funil, headers=ctx["h_dir_a"]).json()["etapas"]}
    assert etapas["Visitas"] == 1
    assert etapas["Contactos"] == 40
    assert etapas["Reuniões"] == 6

    # Diretor declara mais do que o sistema registou: prevalece o valor declarado.
    ctx["client"].put(f"{BASE}/team-meetings/{m['id']}", json={"linhas": [
        _linha(c1.id, "Presente", visitas=3, contactos=40, reunioes_angariacao=6),
    ]}, headers=ctx["h_dir_a"])
    etapas = {e["etapa"]: e["quantidade"] for e in ctx["client"].get(url_funil, headers=ctx["h_dir_a"]).json()["etapas"]}
    assert etapas["Visitas"] == 3

    # Snapshot da reunião semanal também reflete a atividade declarada.
    start = ctx["client"].post(f"{BASE}/meetings/start", json={"consultor_id": c1.id}, headers=ctx["h_dir_a"])
    if start.status_code == 422:  # contrato alternativo via query string
        start = ctx["client"].post(f"{BASE}/meetings/start?consultor_id={c1.id}", headers=ctx["h_dir_a"])
    assert start.status_code == 200, start.text
    assert start.json()["visitas_semana"] == 3
    assert start.json()["contactos_semana"] == 40
