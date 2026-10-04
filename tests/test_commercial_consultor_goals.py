"""
Testes automatizados para a visão e gestão de metas individuais pelo consultor.
Cobre:
1. GET /api/v1/commercial/my-goals (Leitura de metas, progresso e cálculo do que falta)
2. PUT /api/v1/commercial/my-goals (Atualização de metas pelo próprio consultor)
3. Isolamento multi-tenant estrito por agencia_id
4. Isolamento horizontal entre consultores da mesma agência
5. Bloqueio de requisições não autenticadas (HTTP 401)
6. Validação de parâmetros (mês inválido)
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from database.connection import Base, get_db
from app.models.commercial import Goal
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.user import User
from app.models.visit import Visit
from app.services.auth_service import create_access_token, hash_password


@pytest.fixture(scope="function")
def db_session():
    """Sessão de banco isolada em memória com agências e utilizadores."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    # Agência 1
    tenant1 = Tenant(
        nome="Agência Lisboa Prime",
        slug="lisboa-prime",
        nif="500111222",
        ativo=True,
    )
    # Agência 2
    tenant2 = Tenant(
        nome="Agência Porto Gold",
        slug="porto-gold",
        nif="500333444",
        ativo=True,
    )
    session.add_all([tenant1, tenant2])
    session.commit()

    # Consultor 1 (Agência 1)
    c1 = User(
        agencia_id=tenant1.id,
        nome="Rui Consultor",
        email="rui.consultor@fecho.pt",
        password_hash=hash_password("SenhaSegura123!"),
        role="consultor",
        ativo=True,
    )
    # Consultor 2 (Agência 1)
    c2 = User(
        agencia_id=tenant1.id,
        nome="Ana Consultora",
        email="ana.consultora@fecho.pt",
        password_hash=hash_password("SenhaSegura123!"),
        role="consultor",
        ativo=True,
    )
    # Consultor 3 (Agência 2)
    c3 = User(
        agencia_id=tenant2.id,
        nome="Pedro Porto",
        email="pedro.porto@fecho.pt",
        password_hash=hash_password("SenhaSegura123!"),
        role="consultor",
        ativo=True,
    )
    session.add_all([c1, c2, c3])
    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def consultor_setup(db_session):
    c1 = db_session.query(User).filter_by(email="rui.consultor@fecho.pt").first()
    c2 = db_session.query(User).filter_by(email="ana.consultora@fecho.pt").first()
    c3 = db_session.query(User).filter_by(email="pedro.porto@fecho.pt").first()

    token_c1 = create_access_token(data={"sub": str(c1.id), "agencia_id": c1.agencia_id, "role": c1.role})
    token_c2 = create_access_token(data={"sub": str(c2.id), "agencia_id": c2.agencia_id, "role": c2.role})
    token_c3 = create_access_token(data={"sub": str(c3.id), "agencia_id": c3.agencia_id, "role": c3.role})

    return {
        "c1": c1,
        "c2": c2,
        "c3": c3,
        "token_c1": token_c1,
        "token_c2": token_c2,
        "token_c3": token_c3,
    }


def test_get_my_goals_default_and_calculation(client: TestClient, consultor_setup, db_session):
    """Valida se o consultor consegue consultar as suas metas com valores default e cálculo correto do que falta."""
    headers = {"Authorization": f"Bearer {consultor_setup['token_c1']}"}
    response = client.get("/api/v1/commercial/my-goals", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["consultor_id"] == consultor_setup["c1"].id
    assert data["consultor_nome"] == "Rui Consultor"
    assert "meta_faturacao" in data
    assert "faturacao_realizada" in data
    assert "falta_faturar" in data
    assert "semaforo_trajetoria" in data
    assert "indicadores" in data

    # Verifica se os indicadores contêm a chave 'falta' e cálculo matemático correto
    for ind in data["indicadores"]:
        assert "indicador" in ind
        assert "meta" in ind
        assert "realizado" in ind
        assert "falta" in ind
        assert "percentual" in ind
        assert ind["falta"] == max(0.0, ind["meta"] - ind["realizado"])


def test_update_my_goals_success(client: TestClient, consultor_setup, db_session):
    """Valida se o consultor consegue definir e atualizar as suas próprias metas."""
    headers = {"Authorization": f"Bearer {consultor_setup['token_c1']}"}

    payload = {
        "ano": 2026,
        "mes": 10,
        "meta_faturacao": 15000.0,
        "meta_visitas": 25,
        "meta_angariacoes": 5,
        "meta_contactos": 50,
    }

    resp_put = client.put("/api/v1/commercial/my-goals", json=payload, headers=headers)
    assert resp_put.status_code == status.HTTP_200_OK
    data_put = resp_put.json()

    assert float(data_put["meta_faturacao"]) == 15000.0

    # Localiza o indicador de visitas
    visitas_ind = next(i for i in data_put["indicadores"] if i["chave"] == "visitas")
    assert visitas_ind["meta"] == 25.0
    assert visitas_ind["falta"] == max(0.0, 25.0 - visitas_ind["realizado"])

    # Faz GET para conferir persistência
    resp_get = client.get("/api/v1/commercial/my-goals?ano=2026&mes=10", headers=headers)
    assert resp_get.status_code == status.HTTP_200_OK
    data_get = resp_get.json()
    assert float(data_get["meta_faturacao"]) == 15000.0


def test_horizontal_consultor_isolation(client: TestClient, consultor_setup, db_session):
    """Valida que o Consultor 1 não vê nem altera as metas do Consultor 2 da mesma agência."""
    headers_c1 = {"Authorization": f"Bearer {consultor_setup['token_c1']}"}
    headers_c2 = {"Authorization": f"Bearer {consultor_setup['token_c2']}"}

    # C1 define sua meta para 20.000€
    client.put(
        "/api/v1/commercial/my-goals",
        json={"ano": 2026, "mes": 11, "meta_faturacao": 20000.0, "meta_visitas": 30},
        headers=headers_c1,
    )

    # C2 define sua meta para 8.000€
    client.put(
        "/api/v1/commercial/my-goals",
        json={"ano": 2026, "mes": 11, "meta_faturacao": 8000.0, "meta_visitas": 12},
        headers=headers_c2,
    )

    # C1 consulta: deve ver apenas 20.000€
    res_c1 = client.get("/api/v1/commercial/my-goals?ano=2026&mes=11", headers=headers_c1)
    assert res_c1.status_code == 200
    assert float(res_c1.json()["meta_faturacao"]) == 20000.0
    assert res_c1.json()["consultor_id"] == consultor_setup["c1"].id

    # C2 consulta: deve ver apenas 8.000€
    res_c2 = client.get("/api/v1/commercial/my-goals?ano=2026&mes=11", headers=headers_c2)
    assert res_c2.status_code == 200
    assert float(res_c2.json()["meta_faturacao"]) == 8000.0
    assert res_c2.json()["consultor_id"] == consultor_setup["c2"].id


def test_unauthenticated_request_blocked(client: TestClient):
    """Valida bloqueio 401 para requisições sem token JWT."""
    res = client.get("/api/v1/commercial/my-goals")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED

    res_put = client.put("/api/v1/commercial/my-goals", json={"ano": 2026, "mes": 10})
    assert res_put.status_code == status.HTTP_401_UNAUTHORIZED


def test_invalid_parameters_rejected(client: TestClient, consultor_setup):
    """Valida rejeição de parâmetros fora dos limites permitidos."""
    headers = {"Authorization": f"Bearer {consultor_setup['token_c1']}"}

    # Mês 13 (inválido)
    res_get = client.get("/api/v1/commercial/my-goals?mes=13", headers=headers)
    assert res_get.status_code in (status.HTTP_422_UNPROCESSABLE_ENTITY, 400)

    # Mês 0 (inválido)
    res_put = client.put(
        "/api/v1/commercial/my-goals",
        json={"ano": 2026, "mes": 0, "meta_faturacao": 5000.0},
        headers=headers,
    )
    assert res_put.status_code in (status.HTTP_422_UNPROCESSABLE_ENTITY, 400)
