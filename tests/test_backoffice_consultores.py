"""
Suíte de Testes Automatizados para RBAC: Gestão de Consultores pela Direção e Isolamento Multi-tenant.

Cenários Validados:
1. Criação de consultor pela direção com injeção automática de agencia_id e senha Bcrypt (rounds=12);
2. Bloqueio de e-mail duplicado na criação de consultor (HTTP 409 Conflict);
3. Listagem de consultores da agência pelo diretor (apenas consultores da mesma agência);
4. Ativação e desativação de consultor via PATCH /status com bloqueio de login para consultor inativo;
5. Isolamento multi-tenant estrito: diretor da Agência A não acede ou modifica consultores da Agência B (HTTP 404);
6. Bloqueio RBAC: consultor bloqueado de aceder a rotas de diretoria ou criar/gerir consultores (HTTP 403);
7. Bloqueio de acesso entre consultores: consultor não acede a contatos, visitas ou edição de imóveis de outro consultor;
8. Edição de dados cadastrais e redefinição de palavra-passe pela direção;
9. Bloqueio de auto-desativação da conta da direção.
"""
from datetime import date, datetime, timezone
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from database.connection import Base, get_db
from app.models.contact import Contact
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.user import User
from app.models.visit import Visit
from app.services.auth_service import create_access_token, hash_password, verify_password
from app.middleware.security import rate_limiter


@pytest.fixture(scope="function")
def db_session():
    """Sessão de banco isolada em memória com duas agências e utilizadores de teste."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    # 1. Agência A (Lisboa)
    tenant_a = Tenant(nome="Fecho Prime Lisboa", slug="fecho-prime-lisboa", nif="501234567", ativo=True)
    # 2. Agência B (Porto)
    tenant_b = Tenant(nome="Fecho Foz Porto", slug="fecho-foz-porto", nif="502345678", ativo=True)
    session.add_all([tenant_a, tenant_b])
    session.commit()

    # Utilizadores da Agência A
    diretor_a = User(
        agencia_id=tenant_a.id,
        nome="Dra. Marta Silva",
        email="marta.diretora@fecho.pt",
        password_hash=hash_password("senha_diretora_a"),
        role="diretor",
        ativo=True,
    )
    consultor_a1 = User(
        agencia_id=tenant_a.id,
        nome="João Santos",
        email="joao.consultor@fecho.pt",
        password_hash=hash_password("senha_consultor_a1"),
        role="consultor",
        telemovel="912345678",
        ativo=True,
    )
    consultor_a2 = User(
        agencia_id=tenant_a.id,
        nome="Ana Pereira",
        email="ana.consultora@fecho.pt",
        password_hash=hash_password("senha_consultor_a2"),
        role="consultor",
        telemovel="913456789",
        ativo=True,
    )

    # Utilizadores da Agência B
    diretor_b = User(
        agencia_id=tenant_b.id,
        nome="Dr. Carlos Porto",
        email="carlos.diretor@fecho.pt",
        password_hash=hash_password("senha_diretor_b"),
        role="diretor",
        ativo=True,
    )
    consultor_b1 = User(
        agencia_id=tenant_b.id,
        nome="Rui Costa",
        email="rui.consultor@fecho.pt",
        password_hash=hash_password("senha_consultor_b1"),
        role="consultor",
        telemovel="923456789",
        ativo=True,
    )

    session.add_all([diretor_a, consultor_a1, consultor_a2, diretor_b, consultor_b1])
    session.commit()

    # Imóveis de teste para avaliar restrições entre consultores
    prop_a1 = Property(
        agencia_id=tenant_a.id,
        consultor_id=consultor_a1.id,
        titulo="Apartamento T2 Chiado",
        tipologia="T2",
        preco=450000.00,
        regiao_fiscal="continente",
        status="Ativo",
        nome_proprietario="Sr. Manuel Chiado",
        telefone_proprietario="912000111",
    )
    prop_a2 = Property(
        agencia_id=tenant_a.id,
        consultor_id=consultor_a2.id,
        titulo="Moradia T4 Cascais",
        tipologia="T4",
        preco=950000.00,
        regiao_fiscal="continente",
        status="Ativo",
        nome_proprietario="Dra. Sofia Cascais",
        telefone_proprietario="912000222",
    )
    session.add_all([prop_a1, prop_a2])
    session.commit()

    # Contatos na Esfera de Influência
    contact_a1 = Contact(
        agencia_id=tenant_a.id,
        consultor_id=consultor_a1.id,
        property_id=prop_a1.id,
        nome="Cliente João Silva",
        telemovel="919999001",
        tipo="comprador",
        data_escritura=date(2023, 5, 10),
    )
    contact_a2 = Contact(
        agencia_id=tenant_a.id,
        consultor_id=consultor_a2.id,
        property_id=prop_a2.id,
        nome="Cliente Ana Costa",
        telemovel="919999002",
        tipo="comprador",
        data_escritura=date(2023, 8, 20),
    )
    session.add_all([contact_a1, contact_a2])
    session.commit()

    # Visitas realizadas
    visit_a1 = Visit(
        agencia_id=tenant_a.id,
        property_id=prop_a1.id,
        consultor_id=consultor_a1.id,
        cliente_nome="Potencial Comprador Chiado",
        nivel_interesse=4,
        notas_estruturadas="Cliente muito interessado no T2 do Chiado.",
        data_visita=datetime.now(timezone.utc),
    )
    session.add(visit_a1)
    session.commit()

    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Cliente de teste com injeção da sessão isolada em memória."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    rate_limiter.reset()
    with TestClient(app) as test_client:
        yield test_client
    rate_limiter.reset()
    app.dependency_overrides.clear()


def make_auth_headers(user: User) -> dict:
    """Gera cabeçalho HTTP Bearer com token JWT assinado."""
    token = create_access_token({
        "sub": str(user.id),
        "agencia_id": user.agencia_id,
        "role": user.role,
        "email": user.email,
    })
    return {"Authorization": f"Bearer {token}"}


# =====================================================================
# 1. CRIAÇÃO DE CONSULTORES PELA DIREÇÃO
# =====================================================================

def test_diretor_cria_consultor_sucesso_com_bcrypt_rounds_12(client, db_session):
    """Diretor cria novo consultor com injeção automática de agencia_id e hash Bcrypt rounds=12."""
    diretor_a = db_session.query(User).filter(User.email == "marta.diretora@fecho.pt").first()
    headers_dir = make_auth_headers(diretor_a)

    payload = {
        "nome": "Pedro Albuquerque",
        "email": "pedro.albuquerque@fecho.pt",
        "telemovel": "918765432",
        "password": "SenhaSegura123!",
    }

    resp = client.post("/api/v1/backoffice/consultores", json=payload, headers=headers_dir)
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    data = resp.json()

    assert data["nome"] == "Pedro Albuquerque"
    assert data["email"] == "pedro.albuquerque@fecho.pt"
    assert data["agencia_id"] == diretor_a.agencia_id
    assert data["role"] == "consultor"
    assert data["ativo"] is True
    assert data["telemovel"] == "918765432"

    # Valida no banco de dados o hash Bcrypt rounds=12
    db_user = db_session.query(User).filter(User.email == "pedro.albuquerque@fecho.pt").first()
    assert db_user is not None
    assert db_user.agencia_id == diretor_a.agencia_id
    assert db_user.password_hash.startswith("$2b$12$") or db_user.password_hash.startswith("$2a$12$")
    assert verify_password("SenhaSegura123!", db_user.password_hash) is True

    # Valida que o novo consultor consegue fazer login imediatamente
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "pedro.albuquerque@fecho.pt",
        "password": "SenhaSegura123!",
    })
    assert login_resp.status_code == status.HTTP_200_OK
    login_data = login_resp.json()
    assert "access_token" in login_data
    assert login_data["user"]["role"] == "consultor"


def test_diretor_cria_consultor_email_duplicado_rejeitado(client, db_session):
    """Tentativa de criar consultor com e-mail já registado retorna 409 Conflict."""
    diretor_a = db_session.query(User).filter(User.email == "marta.diretora@fecho.pt").first()
    headers_dir = make_auth_headers(diretor_a)

    payload = {
        "nome": "João Clonado",
        "email": "joao.consultor@fecho.pt",  # Já existe
        "telemovel": "919999999",
        "password": "outrasenha123",
    }

    resp = client.post("/api/v1/backoffice/consultores", json=payload, headers=headers_dir)
    assert resp.status_code == status.HTTP_409_CONFLICT
    assert "já existe um utilizador registado" in resp.json()["detail"].lower()


# =====================================================================
# 2. LISTAGEM DE CONSULTORES DA AGÊNCIA
# =====================================================================

def test_diretor_lista_apenas_consultores_da_sua_agencia(client, db_session):
    """Diretor lista apenas os consultores da sua agência (exclui diretores e consultores de outras agências)."""
    diretor_a = db_session.query(User).filter(User.email == "marta.diretora@fecho.pt").first()
    headers_dir_a = make_auth_headers(diretor_a)

    resp = client.get("/api/v1/backoffice/consultores", headers=headers_dir_a)
    assert resp.status_code == status.HTTP_200_OK
    consultores = resp.json()

    # Devem constar apenas os consultores da Agência A (João Santos e Ana Pereira)
    emails = [c["email"] for c in consultores]
    assert "joao.consultor@fecho.pt" in emails
    assert "ana.consultora@fecho.pt" in emails

    # Não deve incluir o diretor da agência
    assert "marta.diretora@fecho.pt" not in emails
    # Não deve incluir consultores da agência B
    assert "rui.consultor@fecho.pt" not in emails

    for c in consultores:
        assert c["agencia_id"] == diretor_a.agencia_id
        assert c["role"] == "consultor"


# =====================================================================
# 3. ATIVAÇÃO E DESATIVAÇÃO DE CONSULTORES (PATCH /status)
# =====================================================================

def test_diretor_ativa_e_desativa_consultor_com_bloqueio_de_login(client, db_session):
    """Desativação impede login e revoga acessos; reativação restaura operação."""
    diretor_a = db_session.query(User).filter(User.email == "marta.diretora@fecho.pt").first()
    consultor_a1 = db_session.query(User).filter(User.email == "joao.consultor@fecho.pt").first()
    headers_dir = make_auth_headers(diretor_a)

    # 1. Desativa o consultor
    resp = client.patch(
        f"/api/v1/backoffice/consultores/{consultor_a1.id}/status",
        json={"ativo": False},
        headers=headers_dir,
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["ativo"] is False

    # 2. Login de consultor inativo deve falhar com 401
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "joao.consultor@fecho.pt",
        "password": "senha_consultor_a1",
    })
    assert login_resp.status_code == status.HTTP_401_UNAUTHORIZED

    # 3. Tentativa de usar token existente deve falhar com 401 informando conta inativa
    headers_consultor = make_auth_headers(consultor_a1)
    req_resp = client.get("/api/v1/properties", headers=headers_consultor)
    assert req_resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert "inativa" in req_resp.json()["detail"].lower()

    # 4. Reativa o consultor
    resp_reativa = client.patch(
        f"/api/v1/backoffice/consultores/{consultor_a1.id}/status",
        json={"ativo": True},
        headers=headers_dir,
    )
    assert resp_reativa.status_code == status.HTTP_200_OK
    assert resp_reativa.json()["ativo"] is True

    # 5. Login volta a funcionar
    login_ok = client.post("/api/v1/auth/login", json={
        "email": "joao.consultor@fecho.pt",
        "password": "senha_consultor_a1",
    })
    assert login_ok.status_code == status.HTTP_200_OK


# =====================================================================
# 4. EDIÇÃO CADASTRAL DE CONSULTOR (PUT)
# =====================================================================

def test_diretor_edita_dados_e_redefine_senha_consultor(client, db_session):
    """Diretor pode atualizar nome, telemóvel e redefinir a palavra-passe."""
    diretor_a = db_session.query(User).filter(User.email == "marta.diretora@fecho.pt").first()
    consultor_a1 = db_session.query(User).filter(User.email == "joao.consultor@fecho.pt").first()
    headers_dir = make_auth_headers(diretor_a)

    update_payload = {
        "nome": "João Santos Atualizado",
        "telemovel": "919888777",
        "password": "NovaSenhaSegura456!",
    }

    resp = client.put(
        f"/api/v1/backoffice/consultores/{consultor_a1.id}",
        json=update_payload,
        headers=headers_dir,
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["nome"] == "João Santos Atualizado"
    assert data["telemovel"] == "919888777"

    # Confirma que a nova senha funciona
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "joao.consultor@fecho.pt",
        "password": "NovaSenhaSegura456!",
    })
    assert login_resp.status_code == status.HTTP_200_OK


# =====================================================================
# 5. ISOLAMENTO MULTI-TENANT ESTRITO (CROSS-AGENCY)
# =====================================================================

def test_tentativa_invasao_multi_tenant_entre_agencias(client, db_session):
    """Diretor da Agência A recebe 404 ao tentar aceder, desativar ou editar consultor da Agência B."""
    diretor_a = db_session.query(User).filter(User.email == "marta.diretora@fecho.pt").first()
    consultor_b1 = db_session.query(User).filter(User.email == "rui.consultor@fecho.pt").first()
    headers_dir_a = make_auth_headers(diretor_a)

    # 1. Tentativa de desativar consultor de outra agência
    resp_patch = client.patch(
        f"/api/v1/backoffice/consultores/{consultor_b1.id}/status",
        json={"ativo": False},
        headers=headers_dir_a,
    )
    assert resp_patch.status_code == status.HTTP_404_NOT_FOUND
    assert "não encontrado na sua agência" in resp_patch.json()["detail"].lower()

    # 2. Tentativa de editar consultor de outra agência
    resp_put = client.put(
        f"/api/v1/backoffice/consultores/{consultor_b1.id}",
        json={"nome": "Ataque Cross-Tenant"},
        headers=headers_dir_a,
    )
    assert resp_put.status_code == status.HTTP_404_NOT_FOUND


# =====================================================================
# 6. CONTROLE DE ACESSO RBAC (CONSULTORES BLOQUEADOS NO BACKOFFICE)
# =====================================================================

def test_bloqueio_rbac_consultor_bloqueado_em_todas_rotas_de_consultores(client, db_session):
    """Consultor recebe 403 Forbidden ao tentar invocar endpoints de gestão de consultores."""
    consultor_a1 = db_session.query(User).filter(User.email == "joao.consultor@fecho.pt").first()
    headers_cons = make_auth_headers(consultor_a1)

    # 1. GET /consultores
    resp_get = client.get("/api/v1/backoffice/consultores", headers=headers_cons)
    assert resp_get.status_code == status.HTTP_403_FORBIDDEN

    # 2. POST /consultores
    resp_post = client.post("/api/v1/backoffice/consultores", json={
        "nome": "Invasor",
        "email": "invasor@fecho.pt",
        "password": "senha123456",
    }, headers=headers_cons)
    assert resp_post.status_code == status.HTTP_403_FORBIDDEN

    # 3. PATCH /consultores/{id}/status
    resp_patch = client.patch(
        f"/api/v1/backoffice/consultores/{consultor_a1.id}/status",
        json={"ativo": False},
        headers=headers_cons,
    )
    assert resp_patch.status_code == status.HTTP_403_FORBIDDEN

    # 4. PUT /consultores/{id}
    resp_put = client.put(
        f"/api/v1/backoffice/consultores/{consultor_a1.id}",
        json={"nome": "Hack"},
        headers=headers_cons,
    )
    assert resp_put.status_code == status.HTTP_403_FORBIDDEN


# =====================================================================
# 7. ISOLAMENTO DE DADOS ENTRE CONSULTORES DA MESMA AGÊNCIA
# =====================================================================

def test_consultor_bloqueado_de_acessar_e_alterar_dados_de_outro_consultor(client, db_session):
    """Consultor não consegue editar contatos, visitas ou imóveis de colega da mesma agência."""
    consultor_a1 = db_session.query(User).filter(User.email == "joao.consultor@fecho.pt").first()
    consultor_a2 = db_session.query(User).filter(User.email == "ana.consultora@fecho.pt").first()
    prop_a1 = db_session.query(Property).filter(Property.consultor_id == consultor_a1.id).first()
    contact_a1 = db_session.query(Contact).filter(Contact.consultor_id == consultor_a1.id).first()
    visit_a1 = db_session.query(Visit).filter(Visit.consultor_id == consultor_a1.id).first()

    headers_cons2 = make_auth_headers(consultor_a2)

    # 1. Consultor 2 tenta consultar contato exclusivo do Consultor 1 -> 403 Forbidden
    resp_contact = client.get(f"/api/v1/contacts/{contact_a1.id}", headers=headers_cons2)
    assert resp_contact.status_code == status.HTTP_403_FORBIDDEN

    # 2. Consultor 2 tenta editar imóvel do Consultor 1 -> 403 Forbidden
    resp_prop_edit = client.put(
        f"/api/v1/properties/{prop_a1.id}",
        json={"titulo": "Tentativa de alteração não autorizada"},
        headers=headers_cons2,
    )
    assert resp_prop_edit.status_code == status.HTTP_403_FORBIDDEN

    # 3. Consultor 2 tenta transitar estado do imóvel do Consultor 1 -> 403 Forbidden
    resp_trans = client.post(
        f"/api/v1/properties/{prop_a1.id}/transition",
        json={"novo_status": "Reservado"},
        headers=headers_cons2,
    )
    assert resp_trans.status_code == status.HTTP_403_FORBIDDEN

    # 4. Consultor 2 tenta ver detalhes da visita do Consultor 1 -> 404 Not Found (visita não pertence a ele)
    resp_visit = client.get(f"/api/v1/visits/{visit_a1.id}", headers=headers_cons2)
    assert resp_visit.status_code == status.HTTP_404_NOT_FOUND


# =====================================================================
# 8. BLOQUEIO DE AUTO-DESATIVAÇÃO DA CONTA DA DIREÇÃO
# =====================================================================

def test_diretor_bloqueado_de_alterar_o_proprio_status(client, db_session):
    """Diretor não pode desativar a si próprio através do endpoint de consultores."""
    diretor_a = db_session.query(User).filter(User.email == "marta.diretora@fecho.pt").first()
    headers_dir = make_auth_headers(diretor_a)

    resp = client.patch(
        f"/api/v1/backoffice/consultores/{diretor_a.id}/status",
        json={"ativo": False},
        headers=headers_dir,
    )
    # Como o endpoint filtra User.role == "consultor", retorna 404 ou 400
    assert resp.status_code in (status.HTTP_404_NOT_FOUND, status.HTTP_400_BAD_REQUEST)
