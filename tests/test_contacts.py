"""
Suíte de Testes Automatizados para a Fase 8: Pós-Venda, Esfera de Influência e Notificações de Aniversário.

Cenários Validados:
1. Validação dos 3 campos obrigatórios ao transitar imóvel para 'Vendido' (*Nome*, *Telemóvel*, *Data da Escritura*);
2. Alimentação automática do comprador na Esfera de Influência (Contact) ao concretizar a venda;
3. Cadastro manual e listagem de contatos com filtros (por tipo, pesquisa textual e aniversariantes);
4. Detecção precisa de aniversariantes da data de escritura e contagem de anos;
5. Geração de mensagens dinâmicas de pós-venda para WhatsApp em 1 clique (Deep Link formatado);
6. Rotina de conformidade estrita com o RGPD (Direito ao Apagamento: 'Cliente Anonimizado' e trilha em audit_logs);
7. Bloqueio de alteração ou disparo de mensagens para contatos anonimizados;
8. Isolamento multi-tenant rigoroso por agencia_id.
"""
from datetime import date, timedelta
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from database.connection import Base, get_db
from app.models.contact import Contact
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

    # Criação de duas agências (Multi-tenant)
    tenant_a = Tenant(nome="Agência Lisboa Norte", slug="agencia-lisboa-norte", nif="501111111", ativo=True)
    tenant_b = Tenant(nome="Agência Porto Foz", slug="agencia-porto-foz", nif="502222222", ativo=True)
    session.add_all([tenant_a, tenant_b])
    session.commit()

    # Usuários Agência A (Consultor e Diretora)
    consultor_a = User(
        agencia_id=tenant_a.id,
        nome="Gonçalo Ramos",
        email="goncalo@fecho.pt",
        password_hash=hash_password("senha123"),
        role="consultor",
        ativo=True,
    )
    diretora_a = User(
        agencia_id=tenant_a.id,
        nome="Dra. Mariana Silva",
        email="mariana@fecho.pt",
        password_hash=hash_password("senha123"),
        role="diretor",
        ativo=True,
    )

    # Usuário Agência B (Consultor B)
    consultor_b = User(
        agencia_id=tenant_b.id,
        nome="Rui Vitória",
        email="rui@porto-fecho.pt",
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


def test_property_transition_to_sold_requires_three_fields(client: TestClient, db_session: Session):
    """
    Valida que a transição para 'Vendido' exige estritamente:
    1. Nome do Comprador
    2. Telemóvel do Comprador
    3. Data da Escritura
    E que a transição bem-sucedida gera automaticamente o registro em Contact.
    """
    consultor = db_session.query(User).filter(User.email == "goncalo@fecho.pt").first()
    headers = get_token_headers(consultor)

    # Cadastra um imóvel ativo
    prop = Property(
        agencia_id=consultor.agencia_id,
        consultor_id=consultor.id,
        titulo="Apartamento T2 em Alvalade",
        tipologia="T2",
        preco=320000.00,
        regiao_fiscal="continente",
        status="Ativo",
        nome_proprietario="António Barata",
        telefone_proprietario="912345678",
    )
    db_session.add(prop)
    db_session.commit()
    db_session.refresh(prop)

    # 1. Tentativa sem nenhum dos 3 campos
    resp = client.post(
        f"/api/v1/properties/{prop.id}/transition",
        headers=headers,
        json={"novo_status": "Vendido"}
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Nome do Comprador é obrigatório" in resp.json()["detail"]
    assert "Telemóvel do Comprador é obrigatório" in resp.json()["detail"]
    assert "Data da Escritura é obrigatória" in resp.json()["detail"]

    # 2. Tentativa com apenas nome e telemóvel (sem data)
    resp = client.post(
        f"/api/v1/properties/{prop.id}/transition",
        headers=headers,
        json={
            "novo_status": "Vendido",
            "nome_comprador": "Dr. Fernando Santos",
            "telefone_comprador": "918889900"
        }
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Data da Escritura é obrigatória" in resp.json()["detail"]

    # 3. Transição bem-sucedida fornecendo os 3 campos
    data_escritura_str = date.today().isoformat()
    resp_success = client.post(
        f"/api/v1/properties/{prop.id}/transition",
        headers=headers,
        json={
            "novo_status": "Vendido",
            "nome_comprador": "Dr. Fernando Santos",
            "telefone_comprador": "918889900",
            "data_escritura": data_escritura_str
        }
    )
    assert resp_success.status_code == status.HTTP_200_OK
    data = resp_success.json()
    assert data["status"] == "Vendido"
    assert data["nome_comprador"] == "Dr. Fernando Santos"
    assert data["telefone_comprador"] == "918889900"
    assert data["data_escritura"] == data_escritura_str

    # 4. Verifica se gerou automaticamente o comprador na Esfera de Influência
    contact = db_session.query(Contact).filter(
        Contact.property_id == prop.id,
        Contact.agencia_id == consultor.agencia_id
    ).first()
    assert contact is not None
    assert contact.nome == "Dr. Fernando Santos"
    assert contact.telemovel == "918889900"
    assert contact.tipo == "comprador"
    assert contact.data_escritura == date.today()


def test_create_and_list_contacts_in_sphere_of_influence(client: TestClient, db_session: Session):
    """
    Testa cadastro manual e listagem de contatos com filtros.
    """
    consultor = db_session.query(User).filter(User.email == "goncalo@fecho.pt").first()
    headers_c = get_token_headers(consultor)

    # Cadastro manual via API
    resp_create = client.post(
        "/api/v1/contacts",
        headers=headers_c,
        json={
            "nome": "Eng. Paulo Bento",
            "telemovel": "931234567",
            "email": "paulo.bento@email.pt",
            "tipo": "esfera",
            "notas": "Cliente investidor interessado em T1/T2 para arrendamento."
        }
    )
    assert resp_create.status_code == status.HTTP_201_CREATED
    contact_data = resp_create.json()
    assert contact_data["id"] is not None
    assert contact_data["nome"] == "Eng. Paulo Bento"
    assert contact_data["consultor_id"] == consultor.id
    assert contact_data["tipo"] == "esfera"

    # Listagem de contatos
    resp_list = client.get("/api/v1/contacts", headers=headers_c)
    assert resp_list.status_code == status.HTTP_200_OK
    list_data = resp_list.json()
    assert list_data["total"] >= 1
    assert any(c["nome"] == "Eng. Paulo Bento" for c in list_data["items"])

    # Filtro de pesquisa textual
    resp_search = client.get("/api/v1/contacts?q=Bento", headers=headers_c)
    assert resp_search.status_code == status.HTTP_200_OK
    assert len(resp_search.json()["items"]) == 1

    # Filtro por tipo
    resp_type = client.get("/api/v1/contacts?tipo=comprador", headers=headers_c)
    assert resp_type.status_code == status.HTTP_200_OK
    assert all(c["tipo"] == "comprador" for c in resp_type.json()["items"])


def test_anniversary_detection_and_years_calculation(client: TestClient, db_session: Session):
    """
    Valida a identificação de aniversariantes da celebração da escritura às 09:00,
    calculando com precisão os anos completados.
    """
    consultor = db_session.query(User).filter(User.email == "goncalo@fecho.pt").first()
    headers = get_token_headers(consultor)
    hoje = date.today()

    # Contato 1: Escritura celebrada exatamente há 2 anos atrás na mesma data de hoje
    data_escritura_2_anos = date(hoje.year - 2, hoje.month, hoje.day)
    c1 = Contact(
        agencia_id=consultor.agencia_id,
        consultor_id=consultor.id,
        nome="Bernardo Silva",
        telemovel="923334455",
        tipo="comprador",
        data_escritura=data_escritura_2_anos,
        notas="Comprador de moradia em Cascais."
    )

    # Contato 2: Escritura celebrada há 1 ano mas em outro dia/mês
    data_escritura_outro_dia = hoje - timedelta(days=40)
    c2 = Contact(
        agencia_id=consultor.agencia_id,
        consultor_id=consultor.id,
        nome="Diogo Jota",
        telemovel="915556677",
        tipo="comprador",
        data_escritura=data_escritura_outro_dia,
    )

    db_session.add_all([c1, c2])
    db_session.commit()

    # Chama o endpoint de aniversariantes
    resp = client.get("/api/v1/contacts/anniversaries", headers=headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["total"] == 1
    aniversariante = data["items"][0]
    assert aniversariante["nome"] == "Bernardo Silva"
    assert aniversariante["is_aniversario_hoje"] is True
    assert aniversariante["anos_escritura"] == 2


def test_whatsapp_message_generation_dynamic_templates(client: TestClient, db_session: Session):
    """
    Testa a geração de mensagens dinâmicas para WhatsApp em 1 clique
    nos 4 formatos: aniversario_escritura, pos_venda_geral, valorizacao_patrimonial, convite_cafe.
    """
    consultor = db_session.query(User).filter(User.email == "goncalo@fecho.pt").first()
    headers = get_token_headers(consultor)
    hoje = date.today()

    prop = Property(
        agencia_id=consultor.agencia_id,
        consultor_id=consultor.id,
        titulo="Penthouse Parque das Nações",
        tipologia="T3",
        preco=750000.00,
        regiao_fiscal="continente",
        status="Vendido",
        nome_proprietario="João Felix",
        telefone_proprietario="910000000",
    )
    db_session.add(prop)
    db_session.commit()
    db_session.refresh(prop)

    data_escritura = date(hoje.year - 1, hoje.month, hoje.day)
    contact = Contact(
        agencia_id=consultor.agencia_id,
        consultor_id=consultor.id,
        property_id=prop.id,
        nome="Cristiano Aveiro",
        telemovel="912345678",  # Português com 9 dígitos
        tipo="comprador",
        data_escritura=data_escritura,
    )
    db_session.add(contact)
    db_session.commit()
    db_session.refresh(contact)

    # 1. Mensagem de Aniversário de Escritura
    resp_ani = client.post(
        f"/api/v1/contacts/{contact.id}/whatsapp",
        headers=headers,
        json={"tipo_mensagem": "aniversario_escritura"}
    )
    assert resp_ani.status_code == status.HTTP_200_OK
    data_ani = resp_ani.json()
    assert "Cristiano Aveiro" in data_ani["texto"]
    assert "Penthouse Parque das Nações" in data_ani["texto"]
    assert "1 ano" in data_ani["texto"]
    assert "wa.me/351912345678" in data_ani["whatsapp_url"]

    # 2. Mensagem de Pós-Venda Geral
    resp_pos = client.post(
        f"/api/v1/contacts/{contact.id}/whatsapp",
        headers=headers,
        json={"tipo_mensagem": "pos_venda_geral"}
    )
    assert resp_pos.status_code == status.HTTP_200_OK
    assert "adaptação a Penthouse Parque das Nações" in resp_pos.json()["texto"]

    # 3. Mensagem de Valorização Patrimonial
    resp_val = client.post(
        f"/api/v1/contacts/{contact.id}/whatsapp",
        headers=headers,
        json={"tipo_mensagem": "valorizacao_patrimonial"}
    )
    assert resp_val.status_code == status.HTTP_200_OK
    assert "avaliação patrimonial estimada" in resp_val.json()["texto"]

    # 4. Convite para Café
    resp_cafe = client.post(
        f"/api/v1/contacts/{contact.id}/whatsapp",
        headers=headers,
        json={"tipo_mensagem": "convite_cafe"}
    )
    assert resp_cafe.status_code == status.HTTP_200_OK
    assert "café breve" in resp_cafe.json()["texto"]


def test_rgpd_anonymization_and_audit_trail(client: TestClient, db_session: Session):
    """
    Testa o procedimento estrito de anonimização conforme RGPD:
    - Nome substituído por 'Cliente Anonimizado'
    - Telemóvel zerado ('000000000')
    - Email nulo
    - Flag anonimizado = True
    - Registro de trilha de auditoria em audit_logs
    - Bloqueio de novas alterações ou envios de WhatsApp
    """
    consultor = db_session.query(User).filter(User.email == "goncalo@fecho.pt").first()
    headers = get_token_headers(consultor)

    contact = Contact(
        agencia_id=consultor.agencia_id,
        consultor_id=consultor.id,
        nome="Manuel Fernandes",
        telemovel="961112233",
        email="manuel.fernandes@privado.pt",
        tipo="comprador",
        data_escritura=date(2023, 5, 10),
        notas="Notas confidenciais de negócio."
    )
    db_session.add(contact)
    db_session.commit()
    db_session.refresh(contact)

    # Executa a anonimização
    resp_anon = client.post(f"/api/v1/contacts/{contact.id}/anonymize", headers=headers)
    assert resp_anon.status_code == status.HTTP_200_OK
    anon_data = resp_anon.json()
    assert anon_data["status"] == "anonimizado_com_sucesso"
    assert anon_data["nome"] == "Cliente Anonimizado"
    assert anon_data["anonimizado"] is True

    # Verifica no banco de dados
    db_session.refresh(contact)
    assert contact.nome == "Cliente Anonimizado"
    assert contact.telemovel == "000000000"
    assert contact.email is None
    assert contact.anonimizado is True

    # Verifica log de auditoria
    audit_log = db_session.query(Log).filter(
        Log.acao == "RGPD_ANONIMIZACAO",
        Log.entidade_id == contact.id,
        Log.agencia_id == consultor.agencia_id
    ).first()
    assert audit_log is not None
    assert audit_log.user_id == consultor.id

    # Tentativa de atualizar contato anonimizado deve ser rejeitada
    resp_update = client.put(
        f"/api/v1/contacts/{contact.id}",
        headers=headers,
        json={"nome": "Tentativa de Reidentificação"}
    )
    assert resp_update.status_code == status.HTTP_400_BAD_REQUEST
    assert "anonimizado" in resp_update.json()["detail"]

    # Tentativa de gerar WhatsApp para contato anonimizado deve ser rejeitada
    resp_wa = client.post(
        f"/api/v1/contacts/{contact.id}/whatsapp",
        headers=headers,
        json={"tipo_mensagem": "pos_venda_geral"}
    )
    assert resp_wa.status_code == status.HTTP_400_BAD_REQUEST
    assert "anonimizado" in resp_wa.json()["detail"]


def test_multi_tenant_isolation_on_contacts(client: TestClient, db_session: Session):
    """
    Garante que uma agência jamais acessa, altera ou anonimiza contatos de outra agência.
    """
    consultor_a = db_session.query(User).filter(User.email == "goncalo@fecho.pt").first()
    consultor_b = db_session.query(User).filter(User.email == "rui@porto-fecho.pt").first()

    headers_a = get_token_headers(consultor_a)
    headers_b = get_token_headers(consultor_b)

    # Contato cadastrado na Agência B
    contact_b = Contact(
        agencia_id=consultor_b.agencia_id,
        consultor_id=consultor_b.id,
        nome="Cliente do Porto",
        telemovel="939998877",
        tipo="comprador",
    )
    db_session.add(contact_b)
    db_session.commit()
    db_session.refresh(contact_b)

    # 1. Agência A tenta consultar o contato da Agência B
    resp_get = client.get(f"/api/v1/contacts/{contact_b.id}", headers=headers_a)
    assert resp_get.status_code == status.HTTP_404_NOT_FOUND

    # 2. Agência A tenta atualizar contato da Agência B
    resp_put = client.put(
        f"/api/v1/contacts/{contact_b.id}",
        headers=headers_a,
        json={"nome": "Invasão Tenant"}
    )
    assert resp_put.status_code == status.HTTP_404_NOT_FOUND

    # 3. Agência A tenta anonimizar contato da Agência B
    resp_anon = client.post(f"/api/v1/contacts/{contact_b.id}/anonymize", headers=headers_a)
    assert resp_anon.status_code == status.HTTP_404_NOT_FOUND

    # 4. Agência A lista contatos - contato da Agência B não deve aparecer
    resp_list = client.get("/api/v1/contacts", headers=headers_a)
    assert resp_list.status_code == status.HTTP_200_OK
    assert not any(c["id"] == contact_b.id for c in resp_list.json()["items"])


def test_delete_contact_constraints_and_detached_deletion(client: TestClient, db_session: Session):
    """
    Testa que contatos desvinculados podem ser excluídos, mas compradores vinculados a imóveis
    são bloqueados de exclusão física (devem ser anonimizados pelo RGPD).
    """
    consultor = db_session.query(User).filter(User.email == "goncalo@fecho.pt").first()
    headers = get_token_headers(consultor)

    # 1. Contato avulso da esfera de influência
    c_avulso = Contact(
        agencia_id=consultor.agencia_id,
        consultor_id=consultor.id,
        nome="Contato Desvinculado",
        telemovel="919990000",
        tipo="esfera",
    )
    db_session.add(c_avulso)
    db_session.commit()
    db_session.refresh(c_avulso)

    resp_del_avulso = client.delete(f"/api/v1/contacts/{c_avulso.id}", headers=headers)
    assert resp_del_avulso.status_code == status.HTTP_204_NO_CONTENT
    assert db_session.query(Contact).filter(Contact.id == c_avulso.id).first() is None

    # 2. Comprador vinculado a imóvel
    prop = Property(
        agencia_id=consultor.agencia_id,
        consultor_id=consultor.id,
        titulo="Moradia em Sintra",
        tipologia="Moradia",
        preco=550000.00,
        regiao_fiscal="continente",
        status="Vendido",
        nome_proprietario="Vasco da Gama",
        telefone_proprietario="911112222",
    )
    db_session.add(prop)
    db_session.commit()
    db_session.refresh(prop)

    c_comprador = Contact(
        agencia_id=consultor.agencia_id,
        consultor_id=consultor.id,
        property_id=prop.id,
        nome="Luís de Camões",
        telemovel="922223333",
        tipo="comprador",
        data_escritura=date.today(),
    )
    db_session.add(c_comprador)
    db_session.commit()
    db_session.refresh(c_comprador)

    resp_del_comprador = client.delete(f"/api/v1/contacts/{c_comprador.id}", headers=headers)
    assert resp_del_comprador.status_code == status.HTTP_400_BAD_REQUEST
    assert "não devem ser excluídos fisicamente" in resp_del_comprador.json()["detail"]


def test_director_access_and_reassignment(client: TestClient, db_session: Session):
    """
    Testa acesso da diretora a contatos de todos os consultores da agência e reatribuição.
    """
    diretora = db_session.query(User).filter(User.email == "mariana@fecho.pt").first()
    consultor = db_session.query(User).filter(User.email == "goncalo@fecho.pt").first()
    headers_dir = get_token_headers(diretora)

    # Criação de contato atribuído ao consultor
    c = Contact(
        agencia_id=diretora.agencia_id,
        consultor_id=consultor.id,
        nome="Cliente Vip Direção",
        telemovel="960001122",
        tipo="esfera",
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)

    # Diretora consulta contato do consultor
    resp_get = client.get(f"/api/v1/contacts/{c.id}", headers=headers_dir)
    assert resp_get.status_code == status.HTTP_200_OK
    assert resp_get.json()["nome"] == "Cliente Vip Direção"

    # Diretora atualiza dados
    resp_up = client.put(
        f"/api/v1/contacts/{c.id}",
        headers=headers_dir,
        json={"notas": "Atualizado pela direção comercial."}
    )
    assert resp_up.status_code == status.HTTP_200_OK
    assert resp_up.json()["notas"] == "Atualizado pela direção comercial."

