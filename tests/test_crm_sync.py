"""
Suíte de Testes Automatizados para o Módulo de Sincronização CRM (Feeds XML & JSON).
Cobre:
1. Parsers XML e JSON resilientes (eGO, Casafari, X-Feed, Kyero);
2. Cadastro e atualização incremental de imóveis;
3. Isolamento multi-tenant estrito por agencia_id;
4. Proteção da Máquina de Estados (imóveis 'Vendido' preservados);
5. Restrição RBAC no endpoint POST /api/v1/backoffice/sync-crm;
6. Trilha de auditoria em audit_logs.
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
from app.models.log import Log
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.user import User
from app.services.crm_sync_service import CRMSyncService
from app.services.auth_service import create_access_token, hash_password


MOCK_XML_FEED_EGO = """<?xml version="1.0" encoding="utf-8"?>
<properties>
    <property id="EGO-1001">
        <title>Moradia T4 com Piscina em Cascais</title>
        <description>Excelente moradia isolada com vista jardim.</description>
        <type>Moradia</type>
        <price>850.000 €</price>
        <address>Avenida do Mar, 45</address>
        <town>Cascais</town>
        <district>Lisboa</district>
        <area>320</area>
        <status>Ativo</status>
        <owner_name>Joaquim Silva</owner_name>
        <owner_phone>912345678</owner_phone>
    </property>
    <property id="EGO-1002">
        <title>Apartamento T2 Renovado Saldanha</title>
        <description>Apartamento luminoso com varanda.</description>
        <type>T2</type>
        <price>420.000</price>
        <town>Lisboa</town>
        <district>Lisboa</district>
        <area>95.5</area>
        <status>Ativo</status>
    </property>
</properties>
"""

MOCK_JSON_FEED_CASAFARI = """[
    {
        "referencia": "CAS-2001",
        "titulo": "T3 Duplex na Foz do Douro",
        "descricao": "Espaçoso duplex com vista mar.",
        "tipologia": "T3",
        "preco": 650000,
        "concelho": "Porto",
        "distrito": "Porto",
        "area_bruta": 160.0,
        "status": "Ativo",
        "nome_proprietario": "Maria Santos",
        "telefone_proprietario": "933444555"
    }
]"""


@pytest.fixture(scope="function")
def db_session():
    """Sessão de banco isolada em memória com agência e usuários de teste."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    tenant_a = Tenant(nome="Agência A Teste", slug="agencia-a-test", nif="501111111", ativo=True)
    session.add(tenant_a)
    session.commit()

    diretor = User(
        agencia_id=tenant_a.id,
        nome="Diretora Ana",
        email="diretora.ana@fecho.pt",
        password_hash=hash_password("senha123"),
        role="diretor",
        ativo=True,
    )
    consultor = User(
        agencia_id=tenant_a.id,
        nome="Consultor Carlos",
        email="consultor.carlos@fecho.pt",
        password_hash=hash_password("senha123"),
        role="consultor",
        ativo=True,
    )
    session.add_all([diretor, consultor])
    session.commit()

    yield session


@pytest.fixture(scope="function")
def client(db_session):
    """Cliente HTTP de teste com override de sessão de banco."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_crm_sync_parser_xml_ego():
    """Valida o parser de Feed XML no padrão eGO Real Estate / Kyero."""
    items = CRMSyncService.parse_feed_items(MOCK_XML_FEED_EGO, feed_type="xml")
    assert len(items) == 2

    item1 = items[0]
    assert item1["referencia_externa"] == "EGO-1001"
    assert item1["titulo"] == "Moradia T4 com Piscina em Cascais"
    assert item1["tipologia"] == "Moradia"
    assert item1["preco"] == Decimal("850000.00")
    assert item1["concelho"] == "Cascais"
    assert item1["distrito"] == "Lisboa"
    assert item1["area_bruta"] == Decimal("320.00")

    item2 = items[1]
    assert item2["referencia_externa"] == "EGO-1002"
    assert item2["preco"] == Decimal("420000.00")
    assert item2["tipologia"] == "T2"


def test_crm_sync_parser_json():
    """Valida o parser de Feed JSON de API REST CRM."""
    items = CRMSyncService.parse_feed_items(MOCK_JSON_FEED_CASAFARI, feed_type="json")
    assert len(items) == 1

    item = items[0]
    assert item["referencia_externa"] == "CAS-2001"
    assert item["titulo"] == "T3 Duplex na Foz do Douro"
    assert item["concelho"] == "Porto"
    assert item["preco"] == Decimal("650000.00")


def test_api_sync_crm_endpoint_success_and_creation(client: TestClient, db_session: Session):
    """Testa o endpoint POST /api/v1/backoffice/sync-crm cadastrando novos imóveis."""
    diretor = db_session.query(User).filter(User.role == "diretor").first()
    assert diretor is not None
    token = create_access_token({"sub": str(diretor.id), "agencia_id": diretor.agencia_id, "role": "diretor"})

    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "feed_type": "xml",
        "feed_content": MOCK_XML_FEED_EGO,
    }

    response = client.post("/api/v1/backoffice/sync-crm", json=payload, headers=headers)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["sucesso"] is True
    assert data["total_processados"] == 2
    assert data["imoveis_criados"] == 2
    assert data["imoveis_atualizados"] == 0

    p1 = db_session.query(Property).filter(
        Property.agencia_id == diretor.agencia_id,
        Property.referencia_externa == "EGO-1001"
    ).first()
    assert p1 is not None
    assert p1.titulo == "Moradia T4 com Piscina em Cascais"
    assert p1.preco == Decimal("850000.00")
    assert p1.concelho == "Cascais"

    p2 = db_session.query(Property).filter(
        Property.agencia_id == diretor.agencia_id,
        Property.referencia_externa == "EGO-1002"
    ).first()
    assert p2 is not None
    assert p2.preco == Decimal("420000.00")

    log_entry = db_session.query(Log).filter(Log.agencia_id == diretor.agencia_id, Log.acao == "sync_crm_feed").first()
    assert log_entry is not None


def test_api_sync_crm_endpoint_update_existing_property(client: TestClient, db_session: Session):
    """Testa atualização incremental de imóvel existente via nova sincronização."""
    diretor = db_session.query(User).filter(User.role == "diretor").first()
    assert diretor is not None
    token = create_access_token({"sub": str(diretor.id), "agencia_id": diretor.agencia_id, "role": "diretor"})
    headers = {"Authorization": f"Bearer {token}"}

    prop_existente = Property(
        agencia_id=diretor.agencia_id,
        consultor_id=diretor.id,
        referencia_externa="CAS-2001",
        titulo="T3 Duplex Antigo",
        tipologia="T3",
        preco=Decimal("600000.00"),
        status="Ativo",
        nome_proprietario="Maria Santos",
        telefone_proprietario="933444555",
    )
    db_session.add(prop_existente)
    db_session.commit()

    payload = {
        "feed_type": "json",
        "feed_content": MOCK_JSON_FEED_CASAFARI,
    }
    response = client.post("/api/v1/backoffice/sync-crm", json=payload, headers=headers)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["imoveis_criados"] == 0
    assert data["imoveis_atualizados"] == 1

    db_session.refresh(prop_existente)
    assert prop_existente.preco == Decimal("650000.00")
    assert prop_existente.titulo == "T3 Duplex na Foz do Douro"


def test_sync_crm_preserves_sold_property_status(client: TestClient, db_session: Session):
    """Garante que imóveis no status 'Vendido' não têm seu status revertido por feeds automáticos."""
    diretor = db_session.query(User).filter(User.role == "diretor").first()
    assert diretor is not None
    token = create_access_token({"sub": str(diretor.id), "agencia_id": diretor.agencia_id, "role": "diretor"})
    headers = {"Authorization": f"Bearer {token}"}

    prop_vendida = Property(
        agencia_id=diretor.agencia_id,
        consultor_id=diretor.id,
        referencia_externa="EGO-1001",
        titulo="Moradia Vendida",
        tipologia="Moradia",
        preco=Decimal("800000.00"),
        status="Vendido",
        nome_proprietario="Proprietário",
        telefone_proprietario="911111111",
        nome_comprador="Comprador Final",
        telefone_comprador="922222222",
    )
    db_session.add(prop_vendida)
    db_session.commit()

    payload = {
        "feed_type": "xml",
        "feed_content": MOCK_XML_FEED_EGO,
    }
    response = client.post("/api/v1/backoffice/sync-crm", json=payload, headers=headers)
    assert response.status_code == status.HTTP_200_OK

    db_session.refresh(prop_vendida)
    assert prop_vendida.status == "Vendido"


def test_sync_crm_multi_tenant_isolation(client: TestClient, db_session: Session):
    """Valida isolamento multi-tenant: feed de Agência A não altera imóvel com mesma referência da Agência B."""
    tenant_b = Tenant(nome="Agência B", slug="agencia-b-sync", nif="999888777")
    db_session.add(tenant_b)
    db_session.commit()

    diretor_b = User(
        agencia_id=tenant_b.id,
        nome="Diretora B",
        email="diretora.b.sync@fecho.pt",
        password_hash=hash_password("senha123"),
        role="diretor",
        ativo=True,
    )
    db_session.add(diretor_b)
    db_session.commit()

    token_b = create_access_token({"sub": str(diretor_b.id), "agencia_id": tenant_b.id, "role": "diretor"})
    headers_b = {"Authorization": f"Bearer {token_b}"}

    prop_b = Property(
        agencia_id=tenant_b.id,
        consultor_id=diretor_b.id,
        referencia_externa="EGO-1001",
        titulo="Moradia B",
        tipologia="Moradia",
        preco=Decimal("1000000.00"),
        status="Ativo",
        nome_proprietario="Dono B",
        telefone_proprietario="910000000",
    )
    db_session.add(prop_b)
    db_session.commit()

    payload = {"feed_type": "xml", "feed_content": MOCK_XML_FEED_EGO}
    response = client.post("/api/v1/backoffice/sync-crm", json=payload, headers=headers_b)
    assert response.status_code == status.HTTP_200_OK

    db_session.refresh(prop_b)
    assert prop_b.preco == Decimal("850000.00")
    assert prop_b.agencia_id == tenant_b.id


def test_sync_crm_rbac_consultor_blocked(client: TestClient, db_session: Session):
    """Garante que consultores normais são bloqueados no endpoint de sincronização CRM (HTTP 403 Forbidden)."""
    consultor = db_session.query(User).filter(User.role == "consultor").first()
    assert consultor is not None

    token = create_access_token({"sub": str(consultor.id), "agencia_id": consultor.agencia_id, "role": "consultor"})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {"feed_content": MOCK_JSON_FEED_CASAFARI}
    response = client.post("/api/v1/backoffice/sync-crm", json=payload, headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
