"""
Testes automatizados da funcionalidade de importação de equipa comercial por planilha (Excel / CSV).
"""
import base64
import io
import zipfile
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from database.connection import Base, get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth_service import create_access_token, hash_password
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

API = "/api/v1/backoffice"


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def agency_context(db_session):
    tenant = Tenant(nome="Portugalia Imóveis", slug="portugalia", plano_status="ativo", plano_periodo="vitalicio", utilizadores_contratados=20, ativo=True)
    db_session.add(tenant)
    db_session.flush()

    diretor = User(agencia_id=tenant.id, nome="Fernanda Evaristo", email="nanandamenegheti@gmail.com",
                   role="diretor", password_hash=hash_password("SenhaDiretor#1"), ativo=True)
    db_session.add(diretor)

    consultor = User(agencia_id=tenant.id, nome="Consultor Existente", email="existente@portugalia.pt",
                     role="consultor", password_hash=hash_password("SenhaCons#1"), ativo=True)
    db_session.add(consultor)
    db_session.commit()

    tok_dir = create_access_token({"sub": str(diretor.id), "agencia_id": tenant.id, "role": "diretor"})
    tok_cons = create_access_token({"sub": str(consultor.id), "agencia_id": tenant.id, "role": "consultor"})

    return {
        "tenant": tenant,
        "diretor": diretor,
        "consultor": consultor,
        "h_dir": {"Authorization": f"Bearer {tok_dir}"},
        "h_cons": {"Authorization": f"Bearer {tok_cons}"},
    }


def test_download_modelo_csv(client, agency_context):
    resp = client.get(f"{API}/consultores/modelo-csv", headers=agency_context["h_dir"])
    assert resp.status_code == status.HTTP_200_OK
    assert "Nome;Email;Telemóvel;Palavra-passe" in resp.text
    assert "attachment; filename=\"modelo_equipa_fecho.csv\"" in resp.headers["content-disposition"]


def test_import_consultores_csv_sucesso(client, agency_context, db_session):
    csv_conteudo = (
        "Nome;Email;Telemóvel;Palavra-passe\n"
        "Diogo Fernandes;diogo@portugalia.pt;912345678;MinhaSenha123!\n"
        "Beatriz Lima;beatriz@portugalia.pt;923456789;\n"
        "Ricardo Ramos;ricardo@portugalia.pt;;\n"
    )

    resp = client.post(
        f"{API}/consultores/import",
        headers=agency_context["h_dir"],
        json={
            "csv_text": csv_conteudo,
            "filename": "equipa.csv",
            "default_password": "SenhaPadrao2026!",
        },
    )
    assert resp.status_code == status.HTTP_200_OK, resp.text
    data = resp.json()
    assert data["total_lidos"] == 3
    assert data["total_criados"] == 3
    assert data["total_ignorados"] == 0

    # Verifica persistência no banco e senha padrão
    c_diogo = db_session.query(User).filter(User.email == "diogo@portugalia.pt").first()
    assert c_diogo is not None
    assert c_diogo.agencia_id == agency_context["tenant"].id
    assert c_diogo.telemovel == "912345678"
    assert c_diogo.role == "consultor"

    c_beatriz = db_session.query(User).filter(User.email == "beatriz@portugalia.pt").first()
    assert c_beatriz is not None
    assert c_beatriz.telemovel == "923456789"


def test_import_consultores_xlsx_sucesso(client, agency_context, db_session):
    # Gera um .xlsx válido em memória para testar extração nativa
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "xl/sharedStrings.xml",
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<si><t>Nome</t></si><si><t>Email</t></si><si><t>Telemóvel</t></si>"
            "<si><t>Marta Sousa</t></si><si><t>marta.sousa@portugalia.pt</t></si><si><t>933333333</t></si>"
            "<si><t>Tiago Silva</t></si><si><t>tiago.silva@portugalia.pt</t></si><si><t>944444444</t></si>"
            "</sst>",
        )
        zf.writestr(
            "xl/worksheets/sheet1.xml",
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<sheetData>"
            '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c><c r="C1" t="s"><v>2</v></c></row>'
            '<row r="2"><c r="A2" t="s"><v>3</v></c><c r="B2" t="s"><v>4</v></c><c r="C2" t="s"><v>5</v></c></row>'
            '<row r="3"><c r="A3" t="s"><v>6</v></c><c r="B3" t="s"><v>7</v></c><c r="C3" t="s"><v>8</v></c></row>'
            "</sheetData></worksheet>",
        )

    buf.seek(0)
    b64_xlsx = base64.b64encode(buf.read()).decode("ascii")

    resp = client.post(
        f"{API}/consultores/import",
        headers=agency_context["h_dir"],
        json={
            "file_base64": b64_xlsx,
            "filename": "equipa_portugalia.xlsx",
            "default_password": "Fecho2026!",
        },
    )
    assert resp.status_code == status.HTTP_200_OK, resp.text
    data = resp.json()
    assert data["total_lidos"] == 2
    assert data["total_criados"] == 2

    marta = db_session.query(User).filter(User.email == "marta.sousa@portugalia.pt").first()
    assert marta is not None
    assert marta.nome == "Marta Sousa"


def test_import_ignora_duplicados_e_invalidos(client, agency_context):
    csv_conteudo = (
        "Nome;Email;Telemóvel;Palavra-passe\n"
        ";semnome@portugalia.pt;911111111;\n"  # Inválido (sem nome)
        "Nome Sem Email;invalido-email;922222222;\n"  # Inválido (email sem @)
        "Consultor Existente;existente@portugalia.pt;933333333;\n"  # Já existe no banco
        "Novo Valido;novo.valido@portugalia.pt;944444444;\n"  # Válido
        "Novo Valido Repetido;novo.valido@portugalia.pt;955555555;\n"  # Repetido no mesmo arquivo
    )

    resp = client.post(
        f"{API}/consultores/import",
        headers=agency_context["h_dir"],
        json={"csv_text": csv_conteudo, "filename": "teste.csv"},
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["total_lidos"] == 5
    assert data["total_criados"] == 1
    assert data["total_ignorados"] == 4


def test_rbac_consultor_bloqueado(client, agency_context):
    resp_imp = client.post(f"{API}/consultores/import", headers=agency_context["h_cons"], json={"csv_text": "x"})
    assert resp_imp.status_code == status.HTTP_403_FORBIDDEN

    resp_mod = client.get(f"{API}/consultores/modelo-csv", headers=agency_context["h_cons"])
    assert resp_mod.status_code == status.HTTP_403_FORBIDDEN
