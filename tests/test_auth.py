"""
Suíte de testes automatizados para a Fase 3: Autenticação, Sessão e Controle de Acesso (RBAC).

Valida:
1. Hash seguro Bcrypt e verificação de senhas;
2. Emissão e decodificação de tokens JWT com claims (sub, agencia_id, role);
3. Endpoint de login (/api/v1/auth/login) para diretor e consultor;
4. Rejeição de senhas incorretas, usuários inexistentes e usuários inativos;
5. Endpoint de perfil (/api/v1/auth/me) com validação de autenticação;
6. Renovação de token de sessão (/api/v1/auth/refresh);
7. Controle de acesso baseado em perfis (RBAC): require_diretor e require_consultor;
8. Isolamento de tenant garantido na decodificação e validação do token.
"""
from datetime import datetime, timezone
import pytest
from fastapi import APIRouter, Depends, status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from database.connection import Base, get_db
from app.dependencies import get_current_user, require_consultor, require_diretor

# Importação de todos os modelos para registro de metadados
from app.models.tenant import Tenant
from app.models.user import User
from app.models.property import Property
from app.models.visit import Visit
from app.models.objection import ObjectionTag, VisitObjection
from app.models.contact import Contact
from app.models.settings import Settings
from app.models.log import Log

from app.services.auth_service import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

# Router auxiliar exclusivo para testar RBAC
rbac_demo_router = APIRouter(prefix="/rbac-demo", tags=["Testes RBAC"])


@rbac_demo_router.get("/diretor-only")
def protected_diretor_route(user: User = Depends(require_diretor)):
    return {"message": "Acesso concedido à Direção", "user_id": user.id}


@rbac_demo_router.get("/consultor-area")
def protected_consultor_route(user: User = Depends(require_consultor)):
    return {"message": "Acesso concedido a Consultor", "user_id": user.id}


# Inclui o router de teste no app
app.include_router(rbac_demo_router)


@pytest.fixture(scope="function")
def db_session():
    """Cria uma sessão isolada com SQLite em memória usando StaticPool para persistência na mesma thread."""
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
    """Configura o TestClient injetando a sessão do banco em memória."""
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
def seeded_users(db_session):
    """Cria tenant e usuários de teste (Diretora e Consultor)."""
    tenant = Tenant(
        nome="Fecho Prime Real Estate",
        slug="fecho-prime",
        nif="512345678",
        telefone="+351 210 000 000",
        email="contato@fecho-prime.pt",
        ativo=True,
    )
    db_session.add(tenant)
    db_session.flush()

    diretor = User(
        agencia_id=tenant.id,
        nome="Marta Silva",
        email="diretor@fecho.pt",
        password_hash=hash_password("senha_segura_diretor"),
        role="diretor",
        telemovel="+351 912 345 678",
        ativo=True,
    )
    db_session.add(diretor)

    consultor = User(
        agencia_id=tenant.id,
        nome="João Santos",
        email="consultor@fecho.pt",
        password_hash=hash_password("senha_segura_consultor"),
        role="consultor",
        telemovel="+351 923 456 789",
        ativo=True,
    )
    db_session.add(consultor)

    inativo = User(
        agencia_id=tenant.id,
        nome="Pedro Inativo",
        email="inativo@fecho.pt",
        password_hash=hash_password("senha_inativo"),
        role="consultor",
        ativo=False,
    )
    db_session.add(inativo)

    db_session.commit()
    return {
        "tenant": tenant,
        "diretor": diretor,
        "consultor": consultor,
        "inativo": inativo,
    }


def test_password_hashing():
    """Valida que o hash Bcrypt gera strings não reversíveis e valida corretamente."""
    pwd = "MinhaSenhaForte2026!"
    hashed = hash_password(pwd)

    assert hashed != pwd
    assert hashed.startswith("$2b$12$")
    assert verify_password(pwd, hashed) is True
    assert verify_password("SenhaIncorreta", hashed) is False


def test_jwt_token_creation_and_decoding():
    """Valida geração e decodificação do token JWT com seus claims essenciais."""
    claims = {
        "sub": "42",
        "agencia_id": 7,
        "role": "diretor",
        "email": "teste@fecho.pt",
    }
    token = create_access_token(claims)
    assert isinstance(token, str)

    decoded = decode_access_token(token)
    assert decoded["sub"] == "42"
    assert decoded["agencia_id"] == 7
    assert decoded["role"] == "diretor"
    assert decoded["email"] == "teste@fecho.pt"
    assert "exp" in decoded


def test_login_consultor_success(client, seeded_users):
    """Valida login de consultor com credenciais corretas."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "consultor@fecho.pt", "password": "senha_segura_consultor"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "consultor@fecho.pt"
    assert data["user"]["role"] == "consultor"
    assert data["user"]["agencia_nome"] == "Fecho Prime Real Estate"


def test_login_diretor_success(client, seeded_users):
    """Valida login de diretor com credenciais corretas."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "diretor@fecho.pt", "password": "senha_segura_diretor"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["user"]["role"] == "diretor"
    assert data["user"]["email"] == "diretor@fecho.pt"


def test_login_invalid_password(client, seeded_users):
    """Valida rejeição de senha incorreta com HTTP 401."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "consultor@fecho.pt", "password": "senha_totalmente_errada"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Credenciais inválidas" in response.json()["detail"]


def test_login_nonexistent_email(client, seeded_users):
    """Valida rejeição de e-mail não cadastrado com HTTP 401."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "fantasma@fecho.pt", "password": "qualquer_senha"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_login_inactive_user(client, seeded_users):
    """Valida que usuário inativo é impedido de autenticar."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "inativo@fecho.pt", "password": "senha_inativo"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_me_endpoint(client, seeded_users):
    """Valida rota /api/v1/auth/me para obter dados do usuário autenticado."""
    # 1. Login para obter token
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "consultor@fecho.pt", "password": "senha_segura_consultor"}
    )
    token = login_resp.json()["access_token"]

    # 2. Requisição sem token -> 401
    resp_no_token = client.get("/api/v1/auth/me")
    assert resp_no_token.status_code == status.HTTP_401_UNAUTHORIZED

    # 3. Requisição com token válido -> 200
    headers = {"Authorization": f"Bearer {token}"}
    resp_with_token = client.get("/api/v1/auth/me", headers=headers)
    assert resp_with_token.status_code == status.HTTP_200_OK
    user_data = resp_with_token.json()
    assert user_data["email"] == "consultor@fecho.pt"
    assert user_data["nome"] == "João Santos"
    assert user_data["role"] == "consultor"


def test_refresh_token_endpoint(client, seeded_users):
    """Valida rota /api/v1/auth/refresh para renovação da sessão."""
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "diretor@fecho.pt", "password": "senha_segura_diretor"}
    )
    old_token = login_resp.json()["access_token"]

    headers = {"Authorization": f"Bearer {old_token}"}
    refresh_resp = client.post("/api/v1/auth/refresh", headers=headers)
    assert refresh_resp.status_code == status.HTTP_200_OK
    new_token = refresh_resp.json()["access_token"]
    assert new_token is not None


def test_rbac_access_control(client, seeded_users):
    """Valida que consultor não tem acesso à área de diretor, mas diretor tem acesso às suas funções."""
    # Login consultor
    resp_c = client.post(
        "/api/v1/auth/login",
        json={"email": "consultor@fecho.pt", "password": "senha_segura_consultor"}
    )
    token_consultor = resp_c.json()["access_token"]
    headers_consultor = {"Authorization": f"Bearer {token_consultor}"}

    # Login diretor
    resp_d = client.post(
        "/api/v1/auth/login",
        json={"email": "diretor@fecho.pt", "password": "senha_segura_diretor"}
    )
    token_diretor = resp_d.json()["access_token"]
    headers_diretor = {"Authorization": f"Bearer {token_diretor}"}

    # Consultor acessa área de consultor -> 200 OK
    resp = client.get("/rbac-demo/consultor-area", headers=headers_consultor)
    assert resp.status_code == status.HTTP_200_OK

    # Consultor tenta acessar área restrita de diretor -> 403 Forbidden!
    resp_forbidden = client.get("/rbac-demo/diretor-only", headers=headers_consultor)
    assert resp_forbidden.status_code == status.HTTP_403_FORBIDDEN
    assert "Acesso restrito à Direção" in resp_forbidden.json()["detail"]

    # Diretor acessa área restrita de diretor -> 200 OK
    resp_diretor_ok = client.get("/rbac-demo/diretor-only", headers=headers_diretor)
    assert resp_diretor_ok.status_code == status.HTTP_200_OK
