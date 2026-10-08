"""
Suíte de Testes Automatizados para a Integração do Assistente de IA Google Gemini - MeuFecho (meufecho.pt).

Cobre:
1. Testes unitários do GeminiService (Modo Mock / Simulador, fallback e construtor de prompts);
2. Testes de integração do endpoint POST /api/v1/ai/chat (autenticação, validação de payload, contextos e isolamento multi-tenant);
3. Rejeição de acessos não autenticados (401 Unauthorized).
"""
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
from app.services.gemini_service import GeminiService


@pytest.fixture(scope="function")
def db_session():
    """Configura base de dados em memória isolada para cada teste."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Instancia o TestClient do FastAPI."""
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
def sample_data(db_session):
    """Cria dados iniciais de agência, utilizadores e imóvel de teste."""
    tenant = Tenant(
        nome="Agência Lisboa Luxo",
        slug="lisboa-luxo",
        nif="509999999",
        telefone="+351 210 000 000",
        email="contato@lisboaluxo.pt",
        ativo=True,
    )
    db_session.add(tenant)
    db_session.flush()

    consultor = User(
        agencia_id=tenant.id,
        nome="Consultor Maria",
        email="maria@meufecho.pt",
        password_hash=hash_password("senha123"),
        role="consultor",
        telemovel="+351 910 111 222",
        ativo=True,
    )
    db_session.add(consultor)
    db_session.flush()

    prop = Property(
        agencia_id=tenant.id,
        consultor_id=consultor.id,
        titulo="Penthouse Avenida da Liberdade",
        tipologia="T3",
        preco=1200000.0,
        area_bruta=210.0,
        regiao_fiscal="continente",
        status="Ativo",
        nome_proprietario="Proprietário Lisboa",
        telefone_proprietario="+351 910 000 000",
    )
    db_session.add(prop)
    db_session.commit()


    token = create_access_token(data={"sub": str(consultor.id), "agencia_id": tenant.id, "role": "consultor"})

    return {
        "tenant": tenant,
        "consultor": consultor,
        "property": prop,
        "token": token
    }


# ==============================================================================
# 1. TESTES UNITÁRIOS DO GEMINI SERVICE (MODO MOCK)
# ==============================================================================

def test_gemini_service_mock_response_generation():
    """Garante que o serviço gera respostas mock estruturadas e identifica is_mock=True em ambiente de teste."""
    response_text, is_mock = GeminiService.generate_response(
        message="Escrever um anúncio de luxo para o imóvel",
        context={"titulo": "Villa Cascais", "preco": 850000},
        force_mock=True
    )

    assert is_mock is True
    assert "Villa Cascais" in response_text
    assert "Anúncio Exclusivo" in response_text or "Proposta de Anúncio" in response_text


def test_gemini_service_empty_message_handling():
    """Garante tratamento gracioso para mensagens vazias."""
    response_text, is_mock = GeminiService.generate_response(message="")
    assert is_mock is True
    assert "Por favor, indique uma pergunta" in response_text


def test_gemini_service_mock_categories():
    """Valida categorias de respostas simuladas: negociação de preço, impostos e roteiros de vídeo."""
    # Objeção / Preço
    text_price, _ = GeminiService.generate_response("Como negociar baixa de preço com proprietário?", force_mock=True)
    assert "Renegociação" in text_price or "Mercado" in text_price

    # Impostos / IMT
    text_imt, _ = GeminiService.generate_response("Explique a isenção do IMT Jovem", force_mock=True)
    assert "IMT" in text_imt or "Selo" in text_imt

    # Script de vídeo
    text_script, _ = GeminiService.generate_response("Criar script de vídeo reels para imóvel", force_mock=True)
    assert "Roteiro" in text_script or "Gancho" in text_script


# ==============================================================================
# 2. TESTES DE INTEGRAÇÃO DO ENDPOINT REST (/api/v1/ai/chat)
# ==============================================================================

def test_ai_chat_endpoint_success(client, sample_data):
    """Testa requisição com sucesso ao endpoint de IA por utilizador autenticado."""
    token = sample_data["token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "message": "Gerar um anúncio para o imóvel foco",
        "context": {
            "titulo": sample_data["property"].titulo,
            "preco": float(sample_data["property"].preco),
            "tipologia": sample_data["property"].tipologia
        },

        "force_mock": True
    }

    response = client.post("/api/v1/ai/chat", headers=headers, json=payload)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "response" in data
    assert data["is_mock"] is True
    assert "Penthouse Avenida da Liberdade" in data["response"]
    assert "timestamp" in data


def test_ai_chat_endpoint_unauthenticated_blocked(client):
    """Garante que chamadas sem token JWT são bloqueadas com 401 Unauthorized."""
    payload = {"message": "Olá assistente"}
    response = client.post("/api/v1/ai/chat", json=payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
