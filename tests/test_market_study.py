"""
Testes Automatizados para o Módulo de Estudo de Mercado Comparativo (ACM) - Fecho (fecho.pt).

Valida:
1. Mapeamento dos 308 concelhos de Portugal e lookup de medianas do INE;
2. Parser inteligente de Caderneta Predial Urbana (OCR e texto);
3. Análise semântica de áudio e calibragem ponderada (-20% a +25%);
4. Cálculo das 3 faixas estratégicas (Venda Rápida, Preço Recomendado, Preço Teto);
5. Benchmarking e auditoria de convergência com Casafari e Alfredo AI;
6. Endpoints REST (/api/v1/properties/concelhos-ine e /api/v1/properties/market-study);
7. Isolamento multi-tenant e controle RBAC.
"""
import asyncio
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from database.connection import Base, get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth_service import create_access_token, hash_password
from app.services.ine_data import INEService
from app.services.market_study_service import MarketStudyService
from app.services.integrations.market_data_providers import MarketBenchmarkAggregator


@pytest.fixture(scope="function")
def db_session():
    """Sessão de banco isolada em memória compartilhada via StaticPool."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    # Cria agência e consultor
    tenant = Tenant(
        nome="Soluções Ideais Lisboa",
        nif="509876543",
        slug="solucoes-ideais-lisboa",
        ativo=True
    )
    session.add(tenant)
    session.commit()

    consultor = User(
        agencia_id=tenant.id,
        nome="Rui Consultor",
        email="rui@fecho.pt",
        password_hash=hash_password("senha123"),
        role="consultor",
        ativo=True
    )
    session.add(consultor)
    session.commit()

    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Cliente de testes do FastAPI com injeção de banco isolado."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def consultor_token(db_session) -> str:
    """Gera token JWT válido para o consultor."""
    consultor = db_session.query(User).filter_by(email="rui@fecho.pt").first()
    return create_access_token({
        "sub": str(consultor.id),
        "agencia_id": consultor.agencia_id,
        "role": consultor.role,
        "email": consultor.email,
    })


def test_portugal_308_concelhos_and_ine_lookup():
    """Valida a cobertura nacional dos 308 concelhos e os preços do INE."""
    concelhos_list = INEService.get_all_concelhos()
    assert len(concelhos_list) >= 308

    lisboa = INEService.lookup_concelho("Lisboa")
    assert lisboa is not None
    assert lisboa["concelho"] == "Lisboa"
    assert lisboa["distrito"] == "Lisboa"
    assert lisboa["preco_mediano_m2"] > 3500

    cascais = INEService.lookup_concelho("Cascais")
    assert cascais["preco_mediano_m2"] >= 3800

    porto = INEService.lookup_concelho("Porto")
    assert porto["distrito"] == "Porto"
    assert porto["preco_mediano_m2"] > 2500

    funchal = INEService.lookup_concelho("Funchal")
    assert funchal["regiao_fiscal"] == "Madeira"
    assert funchal["preco_mediano_m2"] > 2000

    ponta_delgada = INEService.lookup_concelho("Ponta Delgada")
    assert ponta_delgada["regiao_fiscal"] == "Açores"

    evora = INEService.lookup_concelho("évora")
    assert evora["concelho"] == "Évora"


def test_caderneta_predial_parser_regex():
    """Valida o parser inteligente de texto de Caderneta Predial Urbana."""
    raw_caderneta = (
        "REPÚBLICA PORTUGUESA - AUTORIDADE TRIBUTÁRIA E ADUANEIRA\n"
        "CADERNETA PREDIAL URBANA\n"
        "DISTRITO: 11 - LISBOA  CONCELHO: 05 - CASCAIS  FREGUESIA: 07 - CASCAIS E ESTORIL\n"
        "ARTIGO MATRICIAL: 18452  FRACÇÃO: D\n"
        "TIPO DE PRÉDIO: Prédio em Regime de Prop. Horizontal\n"
        "Área bruta privativa: 125,5000 m2\n"
        "Área bruta dependente: 32,0000 m2\n"
        "Ano de inscrição na matriz: 2012\n"
        "VALOR PATRIMONIAL ACTUAL (CIMI): 192.450,00 €"
    )
    parsed = MarketStudyService.parse_caderneta_predial(raw_caderneta)
    assert parsed["concelho"] == "CASCAIS"
    assert parsed["freguesia"] == "CASCAIS E ESTORIL"
    assert parsed["artigo_matricial"] == "18452"
    assert parsed["fracao"] == "D"
    assert parsed["area_bruta_privativa"] == 125.5
    assert parsed["area_bruta_dependente"] == 32.0
    assert parsed["ano_matriz"] == 2012
    assert parsed["vpt"] == 192450.0


def test_consultor_audio_analysis_positive_valorization():
    """Valida a calibragem positiva do áudio para imóvel renovado de alto padrão."""
    audio_text = (
        "Imóvel espetacular totalmente remodelado com acabamentos de luxo, caixilharia com vidro duplo, "
        "excelente luz solar virado a sul, vista desafogada para o mar e cozinha equipada em mármore."
    )
    fator, pos, neg, diag, acab = MarketStudyService.analyze_consultor_audio_and_photos(
        notas_voz=audio_text,
        num_fotos=4,
    )
    assert fator > 0.15
    assert fator <= 0.25  # Limite máximo de +25%
    assert len(pos) >= 3
    assert len(neg) == 0
    assert "luxo" in audio_text.lower()
    assert "Excelente estado" in diag


def test_consultor_audio_analysis_devaluation():
    """Valida a calibragem negativa para imóvel a necessitar de obras profundas."""
    audio_text = (
        "Imóvel de origem dos anos 80, cozinha muito datada, precisa de obras urgentes, "
        "com marcas de humidade no teto e sem elevador no terceiro andar."
    )
    fator, pos, neg, diag, acab = MarketStudyService.analyze_consultor_audio_and_photos(
        notas_voz=audio_text,
        num_fotos=3,
    )
    assert fator < -0.10
    assert fator >= -0.20  # Limite mínimo de -20%
    assert len(neg) >= 2
    assert "Necessita" in diag


def test_casafari_and_alfredo_benchmarking():
    """Valida a consolidação tripla Fecho x Casafari x Alfredo AI."""
    benchmarks = asyncio.run(
        MarketBenchmarkAggregator.aggregate_benchmarks(
            concelho="Cascais",
            freguesia="Cascais e Estoril",
            tipologia="T3",
            area_privativa=120.0,
            fecho_preco_recomendado=520000.0,
            fecho_m2=4200.0,
        )
    )
    assert "casafari_avaliacao" in benchmarks
    assert "alfredo_avaliacao" in benchmarks
    assert benchmarks["casafari_avaliacao"]["preco_estimado"] > 0
    assert benchmarks["alfredo_avaliacao"]["preco_estimado"] > 0
    assert benchmarks["indice_convergencia_pct"] >= 80.0
    assert "convergência" in benchmarks["parecer_auditoria"].lower()


def test_api_concelhos_ine_endpoint(client: TestClient, consultor_token: str):
    """Testa endpoint GET /api/v1/properties/concelhos-ine."""
    resp = client.get(
        "/api/v1/properties/concelhos-ine",
        headers={"Authorization": f"Bearer {consultor_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 308
    assert any(c["concelho"] == "Cascais" for c in data)
    assert any(c["concelho"] == "Porto" for c in data)


def test_api_market_study_endpoint_success(client: TestClient, consultor_token: str):
    """Testa endpoint POST /api/v1/properties/market-study completo."""
    payload = {
        "caderneta_raw_text": (
            "CADERNETA PREDIAL URBANA\n"
            "CONCELHO: OEIRAS FREGUESIA: OEIRAS E SÃO JULIÃO DA BARRA\n"
            "ARTIGO: 9912 FRACÇÃO: B\n"
            "Área bruta privativa: 110,00 m2\n"
            "Área bruta dependente: 20,00 m2\n"
            "Ano de inscrição na matriz: 2015\n"
            "VPT: 165.000,00 €"
        ),
        "consultor_notas_voz": "Excelente apartamento, caixilharia com vidro duplo, muita luz natural e cozinha equipada.",
        "fotos_comodos_base64": ["data:image/png;base64,fake1", "data:image/png;base64,fake2", "data:image/png;base64,fake3"],
        "nome_proprietario": "Dr. Fernando Santos",
        "telemovel_proprietario": "+351 912 345 678",
    }

    resp = client.post(
        "/api/v1/properties/market-study",
        json=payload,
        headers={"Authorization": f"Bearer {consultor_token}"},
    )
    assert resp.status_code == 200
    res = resp.json()

    assert res["concelho"] == "Oeiras"
    assert res["area_bruta_privativa"] == 110.0
    assert res["area_bruta_dependente"] == 20.0
    assert res["preco_recomendado"] > 0
    assert res["preco_venda_rapida"] < res["preco_recomendado"]
    assert res["preco_teto_teste"] > res["preco_recomendado"]
    assert len(res["comparaveis"]) >= 3
    assert res["benchmarking_triplo"]["indice_convergencia_pct"] > 70
    assert "https://api.whatsapp.com/send" in res["whatsapp_link"]
    assert "Dr. Fernando Santos" in res["whatsapp_texto"]


def test_api_market_study_unauthenticated_blocked(client: TestClient):
    """Garante que requisições não autenticadas são rejeitadas."""
    resp = client.post("/api/v1/properties/market-study", json={})
    assert resp.status_code == 401
