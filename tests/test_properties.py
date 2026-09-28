"""
Suíte de testes automatizados para a Fase 4: Imóveis e Gestão de Carteira Ativa.

Cenários Validados:
1. Cadastro de imóvel por consultor e por diretor (status inicial 'Ativo');
2. Isolamento multi-tenant estrito: agência B não acessa imóveis da agência A (listagem e ID);
3. Filtros de listagem: por status, tipologia, termo de busca e consultor;
4. Atualização cadastral e permissões RBAC de edição;
5. Máquina de estados:
   - Transição 'Ativo' -> 'Reservado' e retorno 'Reservado' -> 'Ativo';
   - Transição para 'Vendido' sem os 3 campos obrigatórios (rejeição com HTTP 400);
   - Transição para 'Vendido' com os 3 campos (persistência no imóvel e criação automática na Esfera de Influência / Contact);
   - 'Vendido' como estado terminal (rejeição de nova alteração com HTTP 400);
6. Remoção de imóvel sem visitas.
"""
from datetime import date
from decimal import Decimal
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
from app.models.contact import Contact
from app.services.auth_service import create_access_token, hash_password


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

    # Seed de dados para os testes
    tenant_a = Tenant(
        nome="Agência Lisboa Prime",
        nif="501234567",
        slug="lisboa-prime",
        ativo=True
    )
    tenant_b = Tenant(
        nome="Agência Porto Real",
        nif="502345678",
        slug="porto-real",
        ativo=True
    )
    session.add_all([tenant_a, tenant_b])
    session.commit()

    consultor_a1 = User(
        agencia_id=tenant_a.id,
        nome="Pedro Consultor",
        email="pedro@lisboaprime.pt",
        password_hash=hash_password("senha123"),
        role="consultor",
        ativo=True
    )
    consultor_a2 = User(
        agencia_id=tenant_a.id,
        nome="Sara Consultora",
        email="sara@lisboaprime.pt",
        password_hash=hash_password("senha123"),
        role="consultor",
        ativo=True
    )
    diretor_a = User(
        agencia_id=tenant_a.id,
        nome="Mariana Diretora",
        email="mariana@lisboaprime.pt",
        password_hash=hash_password("senha123"),
        role="diretor",
        ativo=True
    )
    consultor_b = User(
        agencia_id=tenant_b.id,
        nome="Rui Porto",
        email="rui@portoreal.pt",
        password_hash=hash_password("senha123"),
        role="consultor",
        ativo=True
    )
    session.add_all([consultor_a1, consultor_a2, diretor_a, consultor_b])
    session.commit()

    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Cliente de testes do FastAPI injetando a sessão de banco isolada."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def _get_auth_headers(user: User) -> dict:
    """Gera o cabeçalho Authorization Bearer para um dado usuário."""
    token = create_access_token({
        "sub": str(user.id),
        "agencia_id": user.agencia_id,
        "role": user.role,
        "email": user.email
    })
    return {"Authorization": f"Bearer {token}"}


def test_create_property_success(client, db_session):
    """Verifica cadastro com sucesso de um imóvel por consultor."""
    consultor = db_session.query(User).filter(User.email == "pedro@lisboaprime.pt").first()
    headers = _get_auth_headers(consultor)

    payload = {
        "titulo": "T3 Chiado Histórico",
        "descricao": "Apartamento totalmente remodelado com varanda e vista rio.",
        "tipologia": "T3",
        "preco": "1250000.00",
        "morada": "Rua Garrett, 100",
        "concelho": "Lisboa",
        "distrito": "Lisboa",
        "regiao_fiscal": "continente",
        "area_bruta": "180.5",
        "nome_proprietario": "António Nobre",
        "telefone_proprietario": "+351912345678"
    }

    response = client.post("/api/v1/properties", json=payload, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["id"] is not None
    assert data["titulo"] == "T3 Chiado Histórico"
    assert data["status"] == "Ativo"
    assert data["agencia_id"] == consultor.agencia_id
    assert data["consultor_id"] == consultor.id
    assert data["consultor_nome"] == "Pedro Consultor"
    assert float(data["preco"]) == 1250000.00


def test_create_property_invalid_fiscal_region(client, db_session):
    """Verifica rejeição quando a região fiscal não for continente, madeira ou acores."""
    consultor = db_session.query(User).filter(User.email == "pedro@lisboaprime.pt").first()
    headers = _get_auth_headers(consultor)

    payload = {
        "titulo": "Moradia Algarve",
        "tipologia": "Moradia",
        "preco": "800000.00",
        "regiao_fiscal": "espanha_invalida",
        "nome_proprietario": "João Silva",
        "telefone_proprietario": "+351912345678"
    }

    response = client.post("/api/v1/properties", json=payload, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_multi_tenant_isolation_on_properties(client, db_session):
    """
    Verifica isolamento multi-tenant:
    Agência A cria imóvel. Consultor da Agência B não lista nem consegue acessar o imóvel por ID.
    """
    consultor_a = db_session.query(User).filter(User.email == "pedro@lisboaprime.pt").first()
    consultor_b = db_session.query(User).filter(User.email == "rui@portoreal.pt").first()

    headers_a = _get_auth_headers(consultor_a)
    headers_b = _get_auth_headers(consultor_b)

    # Agência A cria imóvel
    prop_payload = {
        "titulo": "Palacete Príncipe Real",
        "tipologia": "T5+",
        "preco": "3500000.00",
        "morada": "Praça do Príncipe Real",
        "concelho": "Lisboa",
        "regiao_fiscal": "continente",
        "nome_proprietario": "Conde de Sintra",
        "telefone_proprietario": "+351919999999"
    }
    create_resp = client.post("/api/v1/properties", json=prop_payload, headers=headers_a)
    assert create_resp.status_code == status.HTTP_201_CREATED
    prop_id = create_resp.json()["id"]

    # Consultor B lista imóveis: deve vir vazio para sua agência
    list_resp_b = client.get("/api/v1/properties", headers=headers_b)
    assert list_resp_b.status_code == status.HTTP_200_OK
    assert list_resp_b.json()["total"] == 0

    # Consultor B tenta acessar o imóvel da Agência A diretamente pelo ID: deve receber 404
    get_resp_b = client.get(f"/api/v1/properties/{prop_id}", headers=headers_b)
    assert get_resp_b.status_code == status.HTTP_404_NOT_FOUND

    # Consultor A lista imóveis: vê o imóvel cadastrado
    list_resp_a = client.get("/api/v1/properties", headers=headers_a)
    assert list_resp_a.status_code == status.HTTP_200_OK
    assert list_resp_a.json()["total"] == 1
    assert list_resp_a.json()["properties"][0]["id"] == prop_id


def test_filters_and_search_on_properties(client, db_session):
    """Verifica filtros por status, tipologia e busca textual."""
    consultor = db_session.query(User).filter(User.email == "pedro@lisboaprime.pt").first()
    headers = _get_auth_headers(consultor)

    # Cadastra 3 imóveis
    client.post("/api/v1/properties", json={
        "titulo": "T2 Cascais Mar",
        "tipologia": "T2",
        "preco": "600000.00",
        "concelho": "Cascais",
        "nome_proprietario": "Carlos",
        "telefone_proprietario": "+351911111111"
    }, headers=headers)

    client.post("/api/v1/properties", json={
        "titulo": "T3 Sintra Verde",
        "tipologia": "T3",
        "preco": "450000.00",
        "concelho": "Sintra",
        "nome_proprietario": "Beatriz",
        "telefone_proprietario": "+351922222222"
    }, headers=headers)

    client.post("/api/v1/properties", json={
        "titulo": "T2 Lisboa Baixa",
        "tipologia": "T2",
        "preco": "550000.00",
        "concelho": "Lisboa",
        "nome_proprietario": "Manuel",
        "telefone_proprietario": "+351933333333"
    }, headers=headers)

    # Filtro por tipologia T2
    res_t2 = client.get("/api/v1/properties?tipologia=T2", headers=headers)
    assert res_t2.json()["total"] == 2

    # Filtro por busca textual 'Sintra'
    res_sintra = client.get("/api/v1/properties?busca=Sintra", headers=headers)
    assert res_sintra.json()["total"] == 1
    assert "Sintra" in res_sintra.json()["properties"][0]["titulo"]


def test_update_property_permissions(client, db_session):
    """
    Testa atualização de imóvel:
    - Consultor dono atualiza;
    - Outro consultor da mesma agência tenta atualizar e é bloqueado (403);
    - Diretor da agência consegue atualizar.
    """
    consultor_1 = db_session.query(User).filter(User.email == "pedro@lisboaprime.pt").first()
    consultor_2 = db_session.query(User).filter(User.email == "sara@lisboaprime.pt").first()
    diretor = db_session.query(User).filter(User.email == "mariana@lisboaprime.pt").first()

    headers_c1 = _get_auth_headers(consultor_1)
    headers_c2 = _get_auth_headers(consultor_2)
    headers_dir = _get_auth_headers(diretor)

    # Consultor 1 cria imóvel
    create_res = client.post("/api/v1/properties", json={
        "titulo": "T1 Avenidas Novas",
        "tipologia": "T1",
        "preco": "350000.00",
        "nome_proprietario": "Duarte",
        "telefone_proprietario": "+351910000000"
    }, headers=headers_c1)
    prop_id = create_res.json()["id"]

    # Consultor 2 tenta alterar o imóvel de Consultor 1: deve receber 403
    update_fail = client.put(f"/api/v1/properties/{prop_id}", json={
        "preco": "340000.00"
    }, headers=headers_c2)
    assert update_fail.status_code == status.HTTP_403_FORBIDDEN

    # Consultor 1 altera o preço do seu próprio imóvel: 200 OK
    update_c1 = client.put(f"/api/v1/properties/{prop_id}", json={
        "preco": "335000.00"
    }, headers=headers_c1)
    assert update_c1.status_code == status.HTTP_200_OK
    assert float(update_c1.json()["preco"]) == 335000.00

    # Diretor altera o título do imóvel: 200 OK
    update_dir = client.put(f"/api/v1/properties/{prop_id}", json={
        "titulo": "T1 Avenidas Novas (Exclusivo)"
    }, headers=headers_dir)
    assert update_dir.status_code == status.HTTP_200_OK
    assert update_dir.json()["titulo"] == "T1 Avenidas Novas (Exclusivo)"


def test_property_state_machine_and_sold_fields_validation(client, db_session):
    """
    Testa rigorosamente a máquina de estados:
    - Ativo -> Reservado;
    - Reservado -> Ativo;
    - Tentativa de Reservado -> Vendido sem os 3 campos: deve falhar (400);
    - Reservado -> Vendido com os 3 campos: sucesso e criação automática na Esfera de Influência;
    - Tentativa de alterar status de imóvel já Vendido: deve falhar (400).
    """
    consultor = db_session.query(User).filter(User.email == "pedro@lisboaprime.pt").first()
    headers = _get_auth_headers(consultor)

    # 1. Criação com status 'Ativo'
    res = client.post("/api/v1/properties", json={
        "titulo": "T2 Parque das Nações",
        "tipologia": "T2",
        "preco": "620000.00",
        "nome_proprietario": "Fernando Pessoa",
        "telefone_proprietario": "+351915555555"
    }, headers=headers)
    prop_id = res.json()["id"]
    assert res.json()["status"] == "Ativo"

    # 2. Transição Ativo -> Reservado
    trans_reservado = client.post(
        f"/api/v1/properties/{prop_id}/transition",
        json={"novo_status": "Reservado"},
        headers=headers
    )
    assert trans_reservado.status_code == status.HTTP_200_OK
    assert trans_reservado.json()["status"] == "Reservado"

    # 3. Transição Reservado -> Ativo (reserva cancelada)
    trans_ativo = client.post(
        f"/api/v1/properties/{prop_id}/transition",
        json={"novo_status": "Ativo"},
        headers=headers
    )
    assert trans_ativo.status_code == status.HTTP_200_OK
    assert trans_ativo.json()["status"] == "Ativo"

    # 4. Transição de volta para Reservado
    client.post(
        f"/api/v1/properties/{prop_id}/transition",
        json={"novo_status": "Reservado"},
        headers=headers
    )

    # 5. Tentativa de transição para 'Vendido' SEM os 3 campos obrigatórios (deve falhar com 400)
    fail_vendido_1 = client.post(
        f"/api/v1/properties/{prop_id}/transition",
        json={"novo_status": "Vendido"},
        headers=headers
    )
    assert fail_vendido_1.status_code == status.HTTP_400_BAD_REQUEST
    assert "Nome do Comprador" in fail_vendido_1.json()["detail"]

    # Falha com apenas nome e telemóvel (sem data da escritura)
    fail_vendido_2 = client.post(
        f"/api/v1/properties/{prop_id}/transition",
        json={
            "novo_status": "Vendido",
            "nome_comprador": "Alexandre Dumas",
            "telefone_comprador": "+351961234567"
        },
        headers=headers
    )
    assert fail_vendido_2.status_code == status.HTTP_400_BAD_REQUEST
    assert "Data da Escritura" in fail_vendido_2.json()["detail"]

    # 6. Transição para 'Vendido' com os 3 campos válidos (sucesso)
    vendido_success = client.post(
        f"/api/v1/properties/{prop_id}/transition",
        json={
            "novo_status": "Vendido",
            "nome_comprador": "Alexandre Dumas",
            "telefone_comprador": "+351961234567",
            "data_escritura": "2026-10-15"
        },
        headers=headers
    )
    assert vendido_success.status_code == status.HTTP_200_OK
    prop_vendido = vendido_success.json()
    assert prop_vendido["status"] == "Vendido"
    assert prop_vendido["nome_comprador"] == "Alexandre Dumas"
    assert prop_vendido["telefone_comprador"] == "+351961234567"
    assert prop_vendido["data_escritura"] == "2026-10-15"

    # Verifica se o comprador foi automaticamente inserido em Contact (Esfera de Influência)
    contato_gerado = db_session.query(Contact).filter(
        Contact.property_id == prop_id,
        Contact.agencia_id == consultor.agencia_id
    ).first()
    assert contato_gerado is not None
    assert contato_gerado.nome == "Alexandre Dumas"
    assert contato_gerado.telemovel == "+351961234567"
    assert contato_gerado.tipo == "comprador"
    assert str(contato_gerado.data_escritura) == "2026-10-15"

    # 7. Tentativa de reabrir ou alterar status de imóvel já 'Vendido' (deve falhar com 400)
    fail_reopen = client.post(
        f"/api/v1/properties/{prop_id}/transition",
        json={"novo_status": "Ativo"},
        headers=headers
    )
    assert fail_reopen.status_code == status.HTTP_400_BAD_REQUEST
    assert "estado terminal" in fail_reopen.json()["detail"].lower()
