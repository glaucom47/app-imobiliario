"""
Suíte de Testes Automatizados para a Fase 6: Visitas, Feedback por Voz e Objeções (Human-in-the-Loop).

Cenários Validados:
1. SpeechService: Extração semântica de nível de interesse (1 a 5);
2. SpeechService: Mapeamento de termos para tags de objeção padronizadas;
3. SpeechService: Geração de notas estruturadas e texto editorial para WhatsApp com Deep Link;
4. Endpoints de Tags: Listagem isolada por agência e bloqueio não autenticado;
5. Endpoint de Processamento de Áudio / Voz: Análise semântica e retorno estruturado para o ecrã HITL;
6. Criação de Visita:
   - Persistência com vínculo ao imóvel e consultor;
   - Vínculo de múltiplas tags de objeção do catálogo corporativo;
   - Geração de mensagem formatada e URL Deep Link;
   - Bloqueio multi-tenant: rejeição de tentativa de registrar visita em imóvel de outra agência;
   - Validação de constraints: nível de interesse fora da faixa 1-5 rejeitado com 422;
7. Listagem de Visitas e RBAC:
   - Consultor visualiza apenas as suas próprias visitas;
   - Diretor visualiza todas as visitas da sua agência;
   - Isolamento total entre agências (Agência B não visualiza visitas da Agência A);
8. Atualização de status de envio de feedback ao proprietário (PATCH /feedback-sent);
9. Compatibilidade de carga da fila offline do PWA com o esquema de criação.
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
from app.models.objection import ObjectionTag
from app.models.visit import Visit
from app.services.auth_service import create_access_token, hash_password
from app.services.speech_service import SpeechService
from app.schemas.visit_schema import VisitCreate


# =============================================================================
# 1. TESTES UNITÁRIOS DO SPEECH SERVICE (NLP & SEMÂNTICA)
# =============================================================================

def test_speech_service_interest_level_detection():
    """Valida inferência precisa do nível de interesse (1 a 5) em português."""
    # Nível 5: Proposta Iminente
    n5, _, _, _ = SpeechService.analyze_transcript("O cliente adorou o imóvel e vai fazer proposta formal amanhã.")
    assert n5 == 5

    # Nível 4: Interesse Elevado
    n4, _, _, _ = SpeechService.analyze_transcript("A cliente gostou muito da cozinha e é uma forte candidata.")
    assert n4 == 4

    # Nível 3: Médio / Em Avaliação
    n3, _, _, _ = SpeechService.analyze_transcript("O visitante achou o apartamento razoável e vai comparar com outros que viu.")
    assert n3 == 3

    # Nível 2: Baixo / Reticente
    n2, _, _, _ = SpeechService.analyze_transcript("O comprador achou caro e ficou muito reticente quanto à zona.")
    assert n2 == 2

    # Nível 1: Descartado
    n1, _, _, _ = SpeechService.analyze_transcript("O cliente descartou completamente o imóvel, está fora de questão.")
    assert n1 == 1


def test_speech_service_objection_keywords_detection():
    """Valida mapeamento de termos orais para tags corporativas da agência."""
    catalog = [
        {"id": 10, "tag": "Preço Elevado", "categoria": "preco"},
        {"id": 11, "tag": "Ruído da Rua / Zona Movimentada", "categoria": "localizacao"},
        {"id": 12, "tag": "Necessita de Obras Profundas", "categoria": "estado"},
        {"id": 13, "tag": "Falta de Garagem / Estacionamento", "categoria": "caracteristica"},
    ]

    text = "O cliente gostou da planta, mas achou o preço alto e queixou-se do barulho da avenida. Além disso precisa de obras na casa de banho."
    nivel, det_names, det_ids, notas = SpeechService.analyze_transcript(text, available_tags=catalog)

    assert "Preço Elevado" in det_names
    assert "Ruído da Rua / Zona Movimentada" in det_names
    assert "Necessita de Obras Profundas" in det_names
    assert 10 in det_ids
    assert 11 in det_ids
    assert 12 in det_ids
    assert 13 not in det_ids  # Sem menção a garagem


def test_speech_service_whatsapp_formatting_and_deep_link():
    """Valida a geração da mensagem editorial e URL para WhatsApp do proprietário."""
    # Mock de Property e User
    class MockProperty:
        titulo = "T3 Chiado Histórico"
        tipologia = "T3"
        nome_proprietario = "Dra. Maria Castro"
        telefone_proprietario = "+351 912 345 678"

    class MockUser:
        nome = "Carlos Consultor"

    mensagem, link = SpeechService.format_whatsapp_feedback(
        propriedade=MockProperty(),
        consultor=MockUser(),
        nivel_interesse=4,
        notas_estruturadas="• Adorou a luz natural do terraço.\n• Teve boa impressão da remodelação.",
        objection_names=["Preço Elevado"],
    )

    assert "Estimado(a) Dra. Maria Castro" in mensagem
    assert "T3 • T3 Chiado Histórico" in mensagem
    assert "★ ★ ★ ★ ☆" in mensagem
    assert "Carlos Consultor" in mensagem
    assert "Preço Elevado" in mensagem
    assert "https://api.whatsapp.com/send?phone=351912345678&text=" in link


# =============================================================================
# 2. FIXTURES E SETUP PARA TESTES DE INTEGRAÇÃO / API REST
# =============================================================================

@pytest.fixture(scope="function")
def db_session():
    """Sessão de banco isolada em memória compartilhada via StaticPool."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    # Criação de duas agências (Multi-tenant)
    tenant_a = Tenant(nome="Agência Lisboa", slug="agencia-lisboa", nif="501111111", ativo=True)
    tenant_b = Tenant(nome="Agência Porto", slug="agencia-porto", nif="502222222", ativo=True)
    session.add_all([tenant_a, tenant_b])
    session.commit()

    # Usuários Agência A (Consultor e Diretora)
    consultor_a = User(
        agencia_id=tenant_a.id,
        nome="Consultor Lisboa",
        email="consultor.a@fecho.pt",
        password_hash=hash_password("senha123"),
        role="consultor",
        ativo=True,
    )
    diretora_a = User(
        agencia_id=tenant_a.id,
        nome="Diretora Lisboa",
        email="diretora.a@fecho.pt",
        password_hash=hash_password("senha123"),
        role="diretor",
        ativo=True,
    )

    # Usuário Agência B (Consultor B)
    consultor_b = User(
        agencia_id=tenant_b.id,
        nome="Consultor Porto",
        email="consultor.b@fecho.pt",
        password_hash=hash_password("senha123"),
        role="consultor",
        ativo=True,
    )
    session.add_all([consultor_a, diretora_a, consultor_b])
    session.commit()

    # Tags de Objeção para Agência A
    tag_preco = ObjectionTag(agencia_id=tenant_a.id, tag="Preço Elevado", categoria="preco", ativo=True)
    tag_ruido = ObjectionTag(agencia_id=tenant_a.id, tag="Ruído da Rua / Zona Movimentada", categoria="localizacao", ativo=True)
    tag_obras = ObjectionTag(agencia_id=tenant_a.id, tag="Necessita de Obras Profundas", categoria="estado", ativo=True)
    session.add_all([tag_preco, tag_ruido, tag_obras])

    # Tag de Objeção para Agência B
    tag_b = ObjectionTag(agencia_id=tenant_b.id, tag="Preço Elevado Porto", categoria="preco", ativo=True)
    session.add(tag_b)
    session.commit()

    # Imóvel na Agência A
    prop_a = Property(
        agencia_id=tenant_a.id,
        consultor_id=consultor_a.id,
        titulo="T2 Avenida da Liberdade",
        tipologia="T2",
        preco=750000.0,
        regiao_fiscal="continente",
        status="Ativo",
        nome_proprietario="Dr. Eduardo Nobre",
        telefone_proprietario="+351 961 222 333",
    )

    # Imóvel na Agência B
    prop_b = Property(
        agencia_id=tenant_b.id,
        consultor_id=consultor_b.id,
        titulo="Moradia Foz do Douro",
        tipologia="Moradia",
        preco=1400000.0,
        regiao_fiscal="continente",
        status="Ativo",
        nome_proprietario="Eng. Manuel Pires",
        telefone_proprietario="+351 933 444 555",
    )
    session.add_all([prop_a, prop_b])
    session.commit()

    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Cliente de teste do FastAPI com injeção da sessão isolada em memória."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def get_token_headers(user: User) -> dict:
    """Gera token de autenticação e cabeçalho Authorization."""
    token = create_access_token(
        data={
            "sub": str(user.id),
            "agencia_id": user.agencia_id,
            "role": user.role,
            "email": user.email,
        }
    )
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# 3. TESTES DE ENDPOINTS REST
# =============================================================================

def test_get_objection_tags(client, db_session):
    """Valida listagem de tags de objeção da agência."""
    consultor_a = db_session.query(User).filter_by(email="consultor.a@fecho.pt").first()
    headers_a = get_token_headers(consultor_a)

    response = client.get("/api/v1/visits/tags", headers=headers_a)
    assert response.status_code == status.HTTP_200_OK
    tags = response.json()
    assert len(tags) == 3
    tag_names = [t["tag"] for t in tags]
    assert "Preço Elevado" in tag_names
    assert "Preço Elevado Porto" not in tag_names  # Isolamento de agência

    # Rejeita requisição sem token
    res_unauth = client.get("/api/v1/visits/tags")
    assert res_unauth.status_code == status.HTTP_401_UNAUTHORIZED


def test_process_audio_endpoint(client, db_session):
    """Valida endpoint POST /api/v1/visits/audio para o ecrã Human-in-the-Loop."""
    consultor_a = db_session.query(User).filter_by(email="consultor.a@fecho.pt").first()
    prop_a = db_session.query(Property).filter_by(titulo="T2 Avenida da Liberdade").first()
    headers_a = get_token_headers(consultor_a)

    payload = {
        "raw_text": "O visitante adorou a luz da sala, mas achou o preço um pouco alto e queixou-se do barulho da rua. Forte hipótese de proposta.",
        "audio_duracao_segundos": 25,
        "property_id": prop_a.id,
    }

    response = client.post("/api/v1/visits/audio", json=payload, headers=headers_a)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["nivel_interesse"] in (4, 5)
    assert data["audio_duracao_segundos"] == 25
    assert "Preço Elevado" in data["detected_tags"]
    assert "Ruído da Rua / Zona Movimentada" in data["detected_tags"]
    assert len(data["detected_tag_ids"]) >= 2
    assert "•" in data["notas_estruturadas"]


def test_create_visit_success_with_objections_and_whatsapp(client, db_session):
    """Valida criação de visita, vínculo com tags e geração de link WhatsApp."""
    consultor_a = db_session.query(User).filter_by(email="consultor.a@fecho.pt").first()
    prop_a = db_session.query(Property).filter_by(titulo="T2 Avenida da Liberdade").first()
    tags_a = db_session.query(ObjectionTag).filter_by(agencia_id=consultor_a.agencia_id).all()
    headers_a = get_token_headers(consultor_a)

    tag_ids = [tags_a[0].id, tags_a[1].id]

    payload = {
        "property_id": prop_a.id,
        "cliente_nome": "Dr. Fernando Santos",
        "cliente_telefone": "+351 919 888 777",
        "audio_duracao_segundos": 28,
        "transcricao": "Cliente visitou o apartamento e gostou bastante da remodelação.",
        "notas_estruturadas": "• Gostou bastante da remodelação.\n• Considera o preço ligeiramente alto.",
        "nivel_interesse": 4,
        "objection_tag_ids": tag_ids,
        "feedback_enviado_proprietario": True,
    }

    response = client.post("/api/v1/visits", json=payload, headers=headers_a)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    assert data["property_id"] == prop_a.id
    assert data["consultor_id"] == consultor_a.id
    assert data["nivel_interesse"] == 4
    assert data["feedback_enviado_proprietario"] is True
    assert len(data["objections"]) == 2
    assert "whatsapp_feedback_text" in data
    assert "Estimado(a) Dr. Eduardo Nobre" in data["whatsapp_feedback_text"]
    assert "https://api.whatsapp.com/send?phone=351961222333" in data["whatsapp_deep_link"]


def test_create_visit_multi_tenant_rejection(client, db_session):
    """Garante que um consultor da Agência A NÃO pode criar visita em imóvel da Agência B."""
    consultor_a = db_session.query(User).filter_by(email="consultor.a@fecho.pt").first()
    prop_b = db_session.query(Property).filter_by(titulo="Moradia Foz do Douro").first()
    headers_a = get_token_headers(consultor_a)

    payload = {
        "property_id": prop_b.id,  # Imóvel da Agência B!
        "notas_estruturadas": "Tentativa de visita não autorizada",
        "nivel_interesse": 3,
        "objection_tag_ids": [],
    }

    response = client.post("/api/v1/visits", json=payload, headers=headers_a)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Imóvel não encontrado ou não pertence a esta agência" in response.json()["detail"]


def test_create_visit_invalid_interest_level_constraint(client, db_session):
    """Valida rejeição de nível de interesse fora da faixa 1 a 5."""
    consultor_a = db_session.query(User).filter_by(email="consultor.a@fecho.pt").first()
    prop_a = db_session.query(Property).filter_by(titulo="T2 Avenida da Liberdade").first()
    headers_a = get_token_headers(consultor_a)

    # Nível 6 (inválido)
    response = client.post(
        "/api/v1/visits",
        json={"property_id": prop_a.id, "nivel_interesse": 6},
        headers=headers_a,
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Nível 0 (inválido)
    response = client.post(
        "/api/v1/visits",
        json={"property_id": prop_a.id, "nivel_interesse": 0},
        headers=headers_a,
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_list_visits_rbac_and_multi_tenant(client, db_session):
    """Valida RBAC de consultor vs diretor e isolamento entre agências na listagem."""
    consultor_a = db_session.query(User).filter_by(email="consultor.a@fecho.pt").first()
    diretora_a = db_session.query(User).filter_by(email="diretora.a@fecho.pt").first()
    consultor_b = db_session.query(User).filter_by(email="consultor.b@fecho.pt").first()
    prop_a = db_session.query(Property).filter_by(titulo="T2 Avenida da Liberdade").first()

    # Cria uma visita para Consultor A
    v1 = Visit(
        agencia_id=consultor_a.agencia_id,
        property_id=prop_a.id,
        consultor_id=consultor_a.id,
        cliente_nome="Cliente A",
        nivel_interesse=4,
    )
    # Cria uma visita conduzida pela Diretora A
    v2 = Visit(
        agencia_id=consultor_a.agencia_id,
        property_id=prop_a.id,
        consultor_id=diretora_a.id,
        cliente_nome="Cliente Diretora",
        nivel_interesse=5,
    )
    db_session.add_all([v1, v2])
    db_session.commit()

    # 1. Consultor A lista: vê apenas a sua própria visita (total 1)
    res_ca = client.get("/api/v1/visits", headers=get_token_headers(consultor_a))
    assert res_ca.status_code == status.HTTP_200_OK
    assert res_ca.json()["total"] == 1
    assert res_ca.json()["visits"][0]["id"] == v1.id

    # 2. Diretora A lista: vê todas as visitas da agência (total 2)
    res_da = client.get("/api/v1/visits", headers=get_token_headers(diretora_a))
    assert res_da.status_code == status.HTTP_200_OK
    assert res_da.json()["total"] == 2

    # 3. Consultor B (outra agência) lista: vê 0 visitas (isolamento multi-tenant estrito)
    res_cb = client.get("/api/v1/visits", headers=get_token_headers(consultor_b))
    assert res_cb.status_code == status.HTTP_200_OK
    assert res_cb.json()["total"] == 0


def test_mark_visit_feedback_sent(client, db_session):
    """Valida endpoint PATCH /api/v1/visits/{id}/feedback-sent."""
    consultor_a = db_session.query(User).filter_by(email="consultor.a@fecho.pt").first()
    prop_a = db_session.query(Property).filter_by(titulo="T2 Avenida da Liberdade").first()
    headers_a = get_token_headers(consultor_a)

    visit = Visit(
        agencia_id=consultor_a.agencia_id,
        property_id=prop_a.id,
        consultor_id=consultor_a.id,
        nivel_interesse=3,
        feedback_enviado_proprietario=False,
    )
    db_session.add(visit)
    db_session.commit()

    # Atualiza para enviado
    response = client.patch(f"/api/v1/visits/{visit.id}/feedback-sent", headers=headers_a)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["feedback_enviado_proprietario"] is True

    # Reinspeciona no banco
    db_session.refresh(visit)
    assert visit.feedback_enviado_proprietario is True


def test_offline_queue_payload_compatibility():
    """Garante que a estrutura gerada pela fila offline valida perfeitamente no schema VisitCreate."""
    offline_item = {
        "property_id": 1,
        "cliente_nome": "Comprador Offline",
        "cliente_telefone": "+351912000000",
        "audio_duracao_segundos": 22,
        "transcricao": "Relato recolhido sem rede móvel.",
        "notas_estruturadas": "• Visita concluída.\n• Interesse moderado.",
        "nivel_interesse": 3,
        "objection_tag_ids": [1, 2],
        "feedback_enviado_proprietario": True,
    }

    # Deserialização e validação Pydantic
    obj = VisitCreate(**offline_item)
    assert obj.property_id == 1
    assert obj.audio_duracao_segundos == 22
    assert obj.nivel_interesse == 3
    assert len(obj.objection_tag_ids) == 2
