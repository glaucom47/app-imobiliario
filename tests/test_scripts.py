"""
Suíte de Testes Automatizados para a Fase 7: Conteúdo e Scripts de Vídeo Curto com Teleprompter.
Fecho (fecho.pt)

Cenários Validados:
1. ScriptService: Listagem dos 3 objetivos comerciais oficiais (Angariação, Baixa de Preço, Open House);
2. ScriptService: Cálculo preciso de tempo de leitura oral e contagem de palavras;
3. ScriptService: Geração em 3 blocos obrigatórios (Gancho, 2 Destaques e CTA) para cada objetivo;
4. ScriptService: Incorporação de dados reais do imóvel (preço formatado em euros, tipologia, localização, área);
5. ScriptService & Endpoints: Isolamento estrito multi-tenant (rejeição de imóvel pertencente a outra agência com 404);
6. Endpoints REST (/api/v1/scripts):
   - GET /scripts/objectives com autenticação de consultor (200 OK);
   - Rejeição de requisição sem token (401 Unauthorized);
   - POST /scripts/generate com payload válido e retorno estruturado;
   - GET /scripts/property/{id} com parâmetros de query;
   - Validação de parâmetros inválidos (422 Unprocessable Content);
7. Teleprompter (static/js/teleprompter.js):
   - Geração offline em 3 blocos via motor client-side executado em Node.js;
   - Cobertura dos 3 objetivos offline com formatação de contingência;
   - Compatibilidade com o formato de exibição do leitor de teleprompter.
"""
import json
import subprocess
from pathlib import Path
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from database.connection import Base, get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.models.property import Property
from app.services.auth_service import create_access_token, hash_password
from app.services.script_service import ScriptService
from app.schemas.script_schema import ScriptObjectiveEnum, ScriptGenerateRequest


TELEPROMPTER_JS_PATH = Path("static/js/teleprompter.js").resolve()


# =============================================================================
# FIXTURES DE BANCO DE DADOS EM MEMÓRIA E CLIENTE HTTP
# =============================================================================

@pytest.fixture(scope="function")
def db_session():
    """Cria uma base SQLite em memória compartilhada para cada teste."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()

    # Criação do Tenant A (Agência Principal)
    tenant_a = Tenant(
        nome="Fecho Lisboa Premium",
        slug="fecho-lisboa",
        nif="500100200",
        ativo=True
    )
    session.add(tenant_a)
    session.flush()

    # Criação do Tenant B (Outra Agência - Isolamento)
    tenant_b = Tenant(
        nome="Fecho Porto Exclusivo",
        slug="fecho-porto",
        nif="500300400",
        ativo=True
    )
    session.add(tenant_b)
    session.flush()

    # Consultor da Agência A
    consultor_a = User(
        agencia_id=tenant_a.id,
        nome="Rui Consultor",
        email="rui@fecho.pt",
        password_hash=hash_password("senha123"),
        role="consultor",
        ativo=True
    )
    session.add(consultor_a)
    session.flush()

    # Consultor da Agência B
    consultor_b = User(
        agencia_id=tenant_b.id,
        nome="Tiago Porto",
        email="tiago@fecho.pt",
        password_hash=hash_password("senha123"),
        role="consultor",
        ativo=True
    )
    session.add(consultor_b)
    session.flush()

    # Imóvel da Agência A
    prop_a = Property(
        agencia_id=tenant_a.id,
        consultor_id=consultor_a.id,
        titulo="Penthouse na Avenida da Liberdade",
        tipologia="T3 Duplex",
        preco=850000.00,
        morada="Avenida da Liberdade, 100",
        concelho="Lisboa",
        distrito="Lisboa",
        regiao_fiscal="continente",
        area_bruta=180.0,
        status="Ativo",
        nome_proprietario="Dr. António Antunes",
        telefone_proprietario="+351910000001"
    )
    session.add(prop_a)

    # Imóvel da Agência B
    prop_b = Property(
        agencia_id=tenant_b.id,
        consultor_id=consultor_b.id,
        titulo="Moradia Foz do Douro",
        tipologia="T4",
        preco=1200000.00,
        morada="Rua do Passeio Alegre",
        concelho="Porto",
        distrito="Porto",
        regiao_fiscal="continente",
        area_bruta=260.0,
        status="Ativo",
        nome_proprietario="Eng. Carlos",
        telefone_proprietario="+351920000002"
    )
    session.add(prop_b)
    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Cliente de testes FastAPI injetando a sessão de banco em memória."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def token_consultor_a(db_session):
    user = db_session.query(User).filter(User.email == "rui@fecho.pt").first()
    return create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "agencia_id": user.agencia_id,
        "role": user.role
    })


@pytest.fixture(scope="function")
def token_consultor_b(db_session):
    user = db_session.query(User).filter(User.email == "tiago@fecho.pt").first()
    return create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "agencia_id": user.agencia_id,
        "role": user.role
    })


# =============================================================================
# 1. TESTES UNITÁRIOS DO SCRIPT SERVICE
# =============================================================================

def test_script_service_objectives_list():
    """Valida o catálogo com os 3 objetivos comerciais oficiais."""
    objectives = ScriptService.get_objectives()
    assert len(objectives) == 3
    ids = [o.id for o in objectives]
    assert "angariacao" in ids
    assert "baixa_preco" in ids
    assert "open_house" in ids


def test_script_service_reading_time_calculation():
    """Valida estimativa de tempo oral a 140 WPM."""
    assert ScriptService.calculate_reading_time_seconds("") == 0
    # 70 palavras a 140 WPM = 0.5 min = 30 segundos
    text_70 = " ".join(["palavra"] * 70)
    assert ScriptService.calculate_reading_time_seconds(text_70) == 30
    # Texto muito curto respeita mínimo de 5 segundos
    text_short = "Apenas uma frase."
    assert ScriptService.calculate_reading_time_seconds(text_short) == 5


def test_script_service_generation_angariacao(db_session):
    """Valida geração do roteiro de Angariação com os 3 blocos obrigatórios."""
    user = db_session.query(User).filter(User.email == "rui@fecho.pt").first()
    prop = db_session.query(Property).filter(Property.agencia_id == user.agencia_id).first()

    req = ScriptGenerateRequest(
        property_id=prop.id,
        objetivo=ScriptObjectiveEnum.ANGARIACAO
    )
    resp = ScriptService.generate_script(db=db_session, request=req, current_user=user)

    assert resp.property_id == prop.id
    assert resp.objetivo == ScriptObjectiveEnum.ANGARIACAO
    assert "Angariação" in resp.objetivo_label

    # Validação dos 3 blocos obrigatórios
    assert len(resp.gancho) > 20
    assert len(resp.destaque_1) > 20
    assert len(resp.destaque_2) > 20
    assert len(resp.cta) > 20

    # Verifica incorporação dos atributos reais do imóvel
    assert "T3 Duplex" in resp.gancho or "T3 Duplex" in resp.destaque_1
    assert "Lisboa" in resp.gancho or "Lisboa" in resp.destaque_1
    assert "850.000 €" in resp.destaque_2

    # Verifica blocos tipados e texto consolidado
    assert len(resp.blocos) == 3
    assert "[1. GANCHO]" in resp.texto_completo
    assert "[2. DESTAQUES]" in resp.texto_completo
    assert "[3. CHAMADA PARA AÇÃO]" in resp.texto_completo
    assert resp.total_palavras > 30
    assert resp.tempo_estimado_segundos >= 15


def test_script_service_generation_baixa_preco(db_session):
    """Valida geração do roteiro de Baixa de Preço / Oportunidade."""
    user = db_session.query(User).filter(User.email == "rui@fecho.pt").first()
    prop = db_session.query(Property).filter(Property.agencia_id == user.agencia_id).first()

    req = ScriptGenerateRequest(
        property_id=prop.id,
        objetivo=ScriptObjectiveEnum.BAIXA_PRECO
    )
    resp = ScriptService.generate_script(db=db_session, request=req, current_user=user)

    assert resp.objetivo == ScriptObjectiveEnum.BAIXA_PRECO
    assert "ajuste" in resp.gancho.lower() or "novidade" in resp.gancho.lower()
    assert "850.000 €" in resp.gancho
    assert "WhatsApp" in resp.cta


def test_script_service_generation_open_house(db_session):
    """Valida geração do roteiro de Open House / Portas Abertas."""
    user = db_session.query(User).filter(User.email == "rui@fecho.pt").first()
    prop = db_session.query(Property).filter(Property.agencia_id == user.agencia_id).first()

    req = ScriptGenerateRequest(
        property_id=prop.id,
        objetivo=ScriptObjectiveEnum.OPEN_HOUSE
    )
    resp = ScriptService.generate_script(db=db_session, request=req, current_user=user)

    assert resp.objetivo == ScriptObjectiveEnum.OPEN_HOUSE
    assert "open house" in resp.gancho.lower() or "portas" in resp.gancho.lower()
    assert "IMT" in resp.destaque_2
    assert "confirmação" in resp.cta.lower() or "reservar" in resp.cta.lower()


def test_script_service_additional_highlights(db_session):
    """Valida enriquecimento com destaques opcionais fornecidos pelo consultor."""
    user = db_session.query(User).filter(User.email == "rui@fecho.pt").first()
    prop = db_session.query(Property).filter(Property.agencia_id == user.agencia_id).first()

    req = ScriptGenerateRequest(
        property_id=prop.id,
        objetivo=ScriptObjectiveEnum.ANGARIACAO,
        destaques_adicionais=["Garagem box para 3 carros", "Vista panorâmica de rio"]
    )
    resp = ScriptService.generate_script(db=db_session, request=req, current_user=user)

    assert "Garagem box para 3 carros" in resp.destaque_2
    assert "Vista panorâmica de rio" in resp.destaque_2


def test_script_service_multi_tenant_isolation(db_session):
    """Garante que um consultor não consegue gerar scripts para imóvel de outro tenant."""
    consultor_b = db_session.query(User).filter(User.email == "tiago@fecho.pt").first()
    prop_a = db_session.query(Property).filter(Property.titulo.contains("Penthouse")).first()

    req = ScriptGenerateRequest(
        property_id=prop_a.id,
        objetivo=ScriptObjectiveEnum.ANGARIACAO
    )

    with pytest.raises(Exception) as exc_info:
        ScriptService.generate_script(db=db_session, request=req, current_user=consultor_b)

    assert "404" in str(exc_info.value) or "não encontrado" in str(exc_info.value)


# =============================================================================
# 2. TESTES DE ENDPOINTS REST (FASTAPI TESTCLIENT)
# =============================================================================

def test_get_objectives_endpoint_authenticated(client, token_consultor_a):
    """GET /api/v1/scripts/objectives retorna os objetivos com 200 OK."""
    headers = {"Authorization": f"Bearer {token_consultor_a}"}
    response = client.get("/api/v1/scripts/objectives", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3
    assert data[0]["id"] == "angariacao"


def test_get_objectives_endpoint_unauthenticated(client):
    """GET /api/v1/scripts/objectives rejeita requisições anônimas com 401."""
    response = client.get("/api/v1/scripts/objectives")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_generate_script_endpoint_success(client, db_session, token_consultor_a):
    """POST /api/v1/scripts/generate gera roteiro completo via API."""
    prop = db_session.query(Property).filter(Property.titulo.contains("Penthouse")).first()
    headers = {"Authorization": f"Bearer {token_consultor_a}"}
    payload = {
        "property_id": prop.id,
        "objetivo": "baixa_preco",
        "tom": "urgente"
    }

    response = client.post("/api/v1/scripts/generate", json=payload, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["property_id"] == prop.id
    assert data["objetivo"] == "baixa_preco"
    assert "850.000 €" in data["preco_formatado"]
    assert len(data["blocos"]) == 3
    assert len(data["gancho"]) > 10
    assert len(data["destaque_1"]) > 10
    assert len(data["destaque_2"]) > 10
    assert len(data["cta"]) > 10


def test_generate_script_endpoint_multi_tenant_rejection(client, db_session, token_consultor_a):
    """POST /api/v1/scripts/generate rejeita imóvel de outra agência com 404."""
    prop_b = db_session.query(Property).filter(Property.titulo.contains("Moradia Foz")).first()
    headers = {"Authorization": f"Bearer {token_consultor_a}"}
    payload = {
        "property_id": prop_b.id,
        "objetivo": "angariacao"
    }

    response = client.post("/api/v1/scripts/generate", json=payload, headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_property_script_get_endpoint(client, db_session, token_consultor_a):
    """GET /api/v1/scripts/property/{id} gera roteiro via query string."""
    prop = db_session.query(Property).filter(Property.titulo.contains("Penthouse")).first()
    headers = {"Authorization": f"Bearer {token_consultor_a}"}

    response = client.get(
        f"/api/v1/scripts/property/{prop.id}?objetivo=open_house",
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["objetivo"] == "open_house"
    assert "Open House" in data["objetivo_label"]


def test_generate_script_invalid_objective(client, db_session, token_consultor_a):
    """POST /api/v1/scripts/generate com objetivo inexistente retorna 422."""
    prop = db_session.query(Property).filter(Property.titulo.contains("Penthouse")).first()
    headers = {"Authorization": f"Bearer {token_consultor_a}"}
    payload = {
        "property_id": prop.id,
        "objetivo": "objetivo_invalido_inexistente"
    }

    response = client.post("/api/v1/scripts/generate", json=payload, headers=headers)
    assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, 422]


# =============================================================================
# 3. TESTES DO GERADOR CLIENT-SIDE / OFFLINE (TELEPROMPTER.JS VIA NODE.JS)
# =============================================================================

def run_teleprompter_offline_gen(prop_dict: dict, objective: str):
    """Invoca generateOfflineScript diretamente de static/js/teleprompter.js via Node.js."""
    prop_json = json.dumps(prop_dict)
    js_code = f"""
    const Teleprompter = require({json.dumps(str(TELEPROMPTER_JS_PATH).replace('\\\\', '/'))});
    const result = Teleprompter.generateOfflineScript({prop_json}, {json.dumps(objective)});
    console.log(JSON.stringify(result));
    """
    proc = subprocess.run(
        ["node", "-e", js_code],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True
    )
    return json.loads(proc.stdout.strip())


def test_teleprompter_js_offline_generation_angariacao():
    """Valida gerador offline de Angariação em JavaScript puro."""
    prop = {
        "id": 101,
        "titulo": "Apartamento Chiado",
        "tipologia": "T2",
        "preco": 620000,
        "concelho": "Lisboa",
        "area_bruta": 115
    }
    res = run_teleprompter_offline_gen(prop, "angariacao")
    assert res["property_id"] == 101
    assert res["objetivo"] == "angariacao"
    assert "Chiado" in res["gancho"] or "Lisboa" in res["gancho"]
    assert "T2" in res["gancho"]
    assert "620.000 €" in res["destaque_2"]
    assert len(res["blocos"]) == 3
    assert res["total_palavras"] > 25
    assert res["tempo_estimado_segundos"] > 10


def test_teleprompter_js_offline_generation_baixa_preco():
    """Valida gerador offline de Baixa de Preço em JavaScript puro."""
    prop = {
        "id": 102,
        "titulo": "Moradia Cascais",
        "tipologia": "T4",
        "preco": 950000,
        "concelho": "Cascais",
        "area_bruta": 240
    }
    res = run_teleprompter_offline_gen(prop, "baixa_preco")
    assert res["objetivo"] == "baixa_preco"
    assert "ajuste" in res["gancho"].lower() or "oportunidade" in res["gancho"].lower()
    assert "WhatsApp" in res["cta"]


def test_teleprompter_js_offline_generation_open_house():
    """Valida gerador offline de Open House em JavaScript puro."""
    prop = {
        "id": 103,
        "titulo": "Palacete Sintra",
        "tipologia": "Moradia",
        "preco": 1800000,
        "concelho": "Sintra",
        "area_bruta": 450
    }
    res = run_teleprompter_offline_gen(prop, "open_house")
    assert res["objetivo"] == "open_house"
    assert "open house" in res["gancho"].lower() or "portas" in res["gancho"].lower()
    assert "IMT" in res["destaque_2"]
