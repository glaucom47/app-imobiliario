"""
Suíte de Testes Automatizados para o Módulo de Captação e Angariação de Imóveis (Fontes Abertas & FSBO).
Conforme FSD (Seção 6):
- Monitorização de hasta pública (e-leiloes.pt) e anúncios de particulares (OLX);
- Estatísticas de captação e listagem com filtros;
- Conversão em 1 clique para 'Property' com status 'Ativo' na carteira;
- Governança RGPD: oposição expressa, blacklist de telefone e anonimização de dados;
- Isolamento multi-tenant rigoroso por agencia_id.
"""
from decimal import Decimal
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from database.connection import Base, get_db
from app.models.lead import LeadAngariacao, LeadBlacklist
from app.models.log import Log
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth_service import create_access_token, hash_password


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

    # Duas Agências para teste multi-tenant
    tenant_a = Tenant(nome="Agência Lisboa Centro", slug="agencia-lisboa-centro", nif="501000001", ativo=True)
    tenant_b = Tenant(nome="Agência Porto Boavista", slug="agencia-porto-boavista", nif="502000002", ativo=True)
    session.add_all([tenant_a, tenant_b])
    session.commit()

    # Usuários Agência A
    consultor_a = User(
        agencia_id=tenant_a.id,
        nome="Pedro Silva",
        email="pedro@fecho.pt",
        password_hash=hash_password("senha123"),
        role="consultor",
        ativo=True,
    )
    diretora_a = User(
        agencia_id=tenant_a.id,
        nome="Sofia Diretora",
        email="sofia@fecho.pt",
        password_hash=hash_password("senha123"),
        role="diretor",
        ativo=True,
    )

    # Usuário Agência B
    consultor_b = User(
        agencia_id=tenant_b.id,
        nome="Rui Costa",
        email="rui@porto.pt",
        password_hash=hash_password("senha123"),
        role="consultor",
        ativo=True,
    )
    session.add_all([consultor_a, diretora_a, consultor_b])
    session.commit()

    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Cliente HTTP com override do banco de dados de teste."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers_consultor_a(db_session):
    user = db_session.query(User).filter_by(email="pedro@fecho.pt").first()
    token = create_access_token({"sub": str(user.id), "agencia_id": user.agencia_id, "role": user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_diretora_a(db_session):
    user = db_session.query(User).filter_by(email="sofia@fecho.pt").first()
    token = create_access_token({"sub": str(user.id), "agencia_id": user.agencia_id, "role": user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_consultor_b(db_session):
    user = db_session.query(User).filter_by(email="rui@porto.pt").first()
    token = create_access_token({"sub": str(user.id), "agencia_id": user.agencia_id, "role": user.role})
    return {"Authorization": f"Bearer {token}"}


def test_criar_lead_manual_e_detalhe(client, auth_headers_consultor_a, db_session):
    """Criação manual de uma oportunidade de angariação e verificação de detalhe."""
    payload = {
        "fonte": "manual",
        "referencia_externa": "PLACA-CASCAIS-01",
        "url_origem": "https://meufecho.pt/manual/1",
        "titulo": "T2 com Terraço no Bairro do Rosário",
        "descricao": "Placa de particular na janela. Contacto direto.",
        "tipologia": "T2",
        "preco_solicitado": 320000.00,
        "concelho": "Cascais",
        "distrito": "Lisboa",
        "morada_aproximada": "Rua das Rosas",
        "nome_contacto": "Sr. Manuel Antunes",
        "telefone_contacto": "+351 912 345 999",
        "tipo_anunciante": "Particular",
    }
    response = client.post("/api/v1/leads/manual", json=payload, headers=auth_headers_consultor_a)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["id"] is not None
    assert data["titulo"] == payload["titulo"]
    assert data["status"] == "Novo"
    lead_id = data["id"]

    # Consulta de Detalhes
    res_detalhe = client.get(f"/api/v1/leads/{lead_id}", headers=auth_headers_consultor_a)
    assert res_detalhe.status_code == status.HTTP_200_OK
    assert res_detalhe.json()["referencia_externa"] == "PLACA-CASCAIS-01"


def test_executar_varredura_e_estatisticas(client, auth_headers_diretora_a):
    """Dispara a varredura nas fontes abertas (e-leilões e OLX) e valida KPIs."""
    scan_res = client.post(
        "/api/v1/leads/varredura",
        json={"concelho": "Lisboa", "fonte": "todos"},
        headers=auth_headers_diretora_a,
    )
    assert scan_res.status_code == status.HTTP_200_OK
    scan_data = scan_res.json()
    assert scan_data["status"] == "sucesso"
    assert scan_data["novas_oportunidades_captadas"] > 0

    # Verifica estatísticas do Backoffice
    stats_res = client.get("/api/v1/leads/stats", headers=auth_headers_diretora_a)
    assert stats_res.status_code == status.HTTP_200_OK
    stats_data = stats_res.json()
    assert stats_data["total_oportunidades"] >= 3
    assert stats_data["total_eleiloes"] >= 1
    assert stats_data["total_particulares_olx"] >= 1
    assert stats_data["taxa_conversao_pct"] == 0.0


def test_conversao_em_1_clique_para_imovel_carteira(client, auth_headers_consultor_a, db_session):
    """
    Testa a conversão em 1 clique:
    - Cria a oportunidade;
    - Executa POST /api/v1/leads/{id}/converter;
    - Valida que cria Property com status 'Ativo';
    - Valida transição da lead para 'Convertido';
    - Valida criação de registro de auditoria em audit_logs.
    """
    # 1. Cria a oportunidade
    lead_res = client.post(
        "/api/v1/leads/manual",
        json={
            "fonte": "olx",
            "referencia_externa": "OLX-CONV-001",
            "url_origem": "https://olx.pt/anuncio/olx-conv-001",
            "titulo": "T3 Vista Tejo em Marvila",
            "descricao": "Particular a vender T3 com vista desafogada.",
            "tipologia": "T3",
            "preco_solicitado": 450000.00,
            "concelho": "Lisboa",
            "distrito": "Lisboa",
            "morada_aproximada": "Rua do Açúcar, Marvila",
            "nome_contacto": "Tiago Ferreira",
            "telefone_contacto": "+351 922 888 777",
            "tipo_anunciante": "Particular",
        },
        headers=auth_headers_consultor_a,
    )
    assert lead_res.status_code == status.HTTP_201_CREATED
    lead_id = lead_res.json()["id"]

    # 2. Executa a conversão em 1 clique
    conv_res = client.post(
        f"/api/v1/leads/{lead_id}/converter",
        json={"regiao_fiscal": "continente"},
        headers=auth_headers_consultor_a,
    )
    assert conv_res.status_code == status.HTTP_201_CREATED
    imovel_data = conv_res.json()

    # Validações estritas do Imóvel criado conforme FSD
    assert imovel_data["id"] is not None
    assert imovel_data["status"] == "Ativo"
    assert imovel_data["titulo"] == "T3 Vista Tejo em Marvila"
    assert Decimal(str(imovel_data["preco"])) == Decimal("450000.00")
    assert imovel_data["nome_proprietario"] == "Tiago Ferreira"
    assert imovel_data["telefone_proprietario"] == "+351 922 888 777"
    assert imovel_data["regiao_fiscal"] == "continente"

    # 3. Valida atualização da lead no banco
    lead_db = db_session.query(LeadAngariacao).filter_by(id=lead_id).first()
    assert lead_db.status == "Convertido"
    assert lead_db.imovel_convertido_id == imovel_data["id"]

    # 4. Valida auditoria em audit_logs
    audit = db_session.query(Log).filter_by(acao="CONVERTER_LEAD_EM_IMOVEL").first()
    assert audit is not None
    assert f"Lead #{lead_id}" in audit.detalhes

    # 5. Tentativa de converter novamente deve ser rejeitada com HTTP 400
    conv_again = client.post(
        f"/api/v1/leads/{lead_id}/converter",
        headers=auth_headers_consultor_a,
    )
    assert conv_again.status_code == status.HTTP_400_BAD_REQUEST
    assert "já se encontra convertida" in conv_again.json()["detail"]


def test_extracao_rapida_via_url(client, auth_headers_consultor_a):
    """Testa a captura instantânea de oportunidade colando a URL de um portal."""
    # Teste com URL do e-leilões
    res_eleiloes = client.post(
        "/api/v1/leads/extrair-url",
        json={"url": "https://e-leiloes.pt/evento/LO-99881-sintra"},
        headers=auth_headers_consultor_a,
    )
    assert res_eleiloes.status_code == status.HTTP_201_CREATED
    data_eleiloes = res_eleiloes.json()
    assert data_eleiloes["fonte"] == "e-leiloes"
    assert "LO-99881-SINTRA" in data_eleiloes["referencia_externa"]

    # Teste com URL do OLX
    res_olx = client.post(
        "/api/v1/leads/extrair-url",
        json={"url": "https://www.olx.pt/d/anuncio/t2-remodelado-amadora-ID77112.html"},
        headers=auth_headers_consultor_a,
    )
    assert res_olx.status_code == status.HTTP_201_CREATED
    data_olx = res_olx.json()
    assert data_olx["fonte"] == "olx"
    assert data_olx["tipologia"] == "T2"


def test_atualizar_status_prospeccao(client, auth_headers_consultor_a):
    """Testa o avanço de status no pipeline comercial da lead."""
    lead_res = client.post(
        "/api/v1/leads/manual",
        json={
            "fonte": "manual",
            "referencia_externa": "MAN-STATUS-01",
            "url_origem": "https://meufecho.pt",
            "titulo": "T1 em Campolide",
            "tipologia": "T1",
            "preco_solicitado": 210000.00,
            "nome_contacto": "Sr. Jorge",
            "telefone_contacto": "+351 911 222 333",
        },
        headers=auth_headers_consultor_a,
    )
    lead_id = lead_res.json()["id"]

    # Altera para Em Prospecção com notas
    patch_res = client.patch(
        f"/api/v1/leads/{lead_id}/status",
        json={"status": "Em Prospeccao", "notas_prospeccao": "Primeiro contacto telefónico efetuado. Proprietário disponível para reunião amanhã."},
        headers=auth_headers_consultor_a,
    )
    assert patch_res.status_code == status.HTTP_200_OK
    assert patch_res.json()["status"] == "Em Prospeccao"
    assert "reunião amanhã" in patch_res.json()["notas_prospeccao"]


def test_oposicao_rgpd_e_bloqueio_blacklist(client, auth_headers_consultor_a, db_session):
    """
    Testa conformidade rigorosa com RGPD (Art. 21 - Direito de Oposição):
    - Registo de oposição formal;
    - Mascaramento definitivo dos dados pessoais na lead;
    - Inclusão do telefone na tabela de blacklist da agência;
    - Bloqueio de novas captações futuras com o mesmo telefone;
    - Bloqueio de conversão em imóvel da carteira.
    """
    telefone_alvo = "+351 969 999 111"
    lead_res = client.post(
        "/api/v1/leads/manual",
        json={
            "fonte": "olx",
            "referencia_externa": "OLX-RGPD-TEST",
            "url_origem": "https://olx.pt/anuncio/teste-rgpd",
            "titulo": "T2 em Odivelas Particular",
            "tipologia": "T2",
            "preco_solicitado": 230000.00,
            "nome_contacto": "Catarina Santos",
            "telefone_contacto": telefone_alvo,
        },
        headers=auth_headers_consultor_a,
    )
    lead_id = lead_res.json()["id"]

    # 1. Regista oposição formal de RGPD
    rgpd_res = client.post(
        f"/api/v1/leads/{lead_id}/oposicao-rgpd",
        json={"motivo": "Proprietário manifestou oposição expressa por chamada telefónica."},
        headers=auth_headers_consultor_a,
    )
    assert rgpd_res.status_code == status.HTTP_200_OK
    rgpd_data = rgpd_res.json()
    assert rgpd_data["status"] == "Oposicao_RGPD"
    assert rgpd_data["telefone_contacto"] == "000000000"
    assert "Proprietário com Oposição RGPD" in rgpd_data["nome_contacto"]

    # 2. Valida persistência na tabela LeadBlacklist da agência
    bl = db_session.query(LeadBlacklist).filter_by(telefone=telefone_alvo).first()
    assert bl is not None
    assert "oposição" in bl.motivo.lower()

    # 3. Tentar criar nova oportunidade com esse telefone deve ser bloqueado com HTTP 400
    tentativa_nova = client.post(
        "/api/v1/leads/manual",
        json={
            "fonte": "manual",
            "referencia_externa": "TENTATIVA-BLOQUEADA",
            "url_origem": "https://meufecho.pt",
            "titulo": "Outro Imóvel em Odivelas",
            "tipologia": "T2",
            "preco_solicitado": 240000.00,
            "telefone_contacto": telefone_alvo,
        },
        headers=auth_headers_consultor_a,
    )
    assert tentativa_nova.status_code == status.HTTP_400_BAD_REQUEST
    assert "oposição formal" in tentativa_nova.json()["detail"].lower()

    # 4. Tentar converter lead em oposição RGPD é bloqueado
    tentativa_conv = client.post(
        f"/api/v1/leads/{lead_id}/converter",
        headers=auth_headers_consultor_a,
    )
    assert tentativa_conv.status_code == status.HTTP_400_BAD_REQUEST
    assert "oposição de tratamento RGPD" in tentativa_conv.json()["detail"]


def test_multi_tenant_isolation_on_leads(client, auth_headers_consultor_a, auth_headers_consultor_b):
    """Garante que oportunidades de uma agência são inacessíveis para outras agências."""
    # Agência A cria oportunidade
    res_a = client.post(
        "/api/v1/leads/manual",
        json={
            "fonte": "manual",
            "referencia_externa": "REF-AGENCIA-A",
            "url_origem": "https://meufecho.pt",
            "titulo": "Penthouse Avenida da Liberdade",
            "tipologia": "T4",
            "preco_solicitado": 1200000.00,
            "nome_contacto": "Dr. Barreto",
            "telefone_contacto": "+351 910 123 456",
        },
        headers=auth_headers_consultor_a,
    )
    assert res_a.status_code == status.HTTP_201_CREATED
    lead_id_a = res_a.json()["id"]

    # Agência B tenta listar -> não deve conter a lead da Agência A
    list_b = client.get("/api/v1/leads", headers=auth_headers_consultor_b)
    assert list_b.status_code == status.HTTP_200_OK
    ids_b = [item["id"] for item in list_b.json()["items"]]
    assert lead_id_a not in ids_b

    # Agência B tenta aceder diretamente -> HTTP 404
    detail_b = client.get(f"/api/v1/leads/{lead_id_a}", headers=auth_headers_consultor_b)
    assert detail_b.status_code == status.HTTP_404_NOT_FOUND

    # Agência B tenta converter -> HTTP 404
    conv_b = client.post(f"/api/v1/leads/{lead_id_a}/converter", headers=auth_headers_consultor_b)
    assert conv_b.status_code == status.HTTP_400_BAD_REQUEST or conv_b.status_code == status.HTTP_404_NOT_FOUND
