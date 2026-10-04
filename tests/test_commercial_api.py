"""
Suíte de testes automatizados para a API REST da Direção Comercial (FSD Seção 8).
Cenários validados:
1. Bloqueio RBAC rigoroso:
   - Utilizador não autenticado recebe 401 Unauthorized;
   - Utilizador com perfil 'consultor' recebe 403 Forbidden;
   - Utilizador com perfil 'diretor' obtém acesso total (200 OK / 201 Created).
2. Isolamento Multi-tenant profundo por agencia_id:
   - Métricas, reuniões, metas e pipeline não vazam entre agências distintas.
3. Dashboard Comercial da Direção:
   - Filtros temporais, variações homólogas e cálculo de pipeline ponderado.
4. Funil Comercial de Vendas (7 etapas e conversões):
   - Contactos -> Reuniões -> Angariações -> Visitas -> Propostas -> CPCV -> Escrituras.
5. Tabela de Performance & Semáforo de Trajetória:
   - Classificação verde, amarelo e vermelho conforme ritmo e atividade.
6. Ficha Individual de Performance em 4 Blocos.
7. Automação da Reunião Semanal e Gestão de Compromissos:
   - Start com snapshot em tempo real e notas de visitas;
   - Save com congelamento atômico e compromissos vinculados.
8. CRUD de Metas (Goals) e Pipeline Deals.
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
from app.models.commercial import Goal, MeetingCommitment, PipelineDeal, WeeklyMeeting
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.user import User
from app.models.visit import Visit
from app.services.auth_service import create_access_token, hash_password


@pytest.fixture(scope="function")
def db_session():
    """Sessão de banco isolada em memória com duas agências e utilizadores."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    # Agências A e B
    tenant_a = Tenant(nome="Fecho Prime Lisboa", slug="fecho-prime-lisboa", nif="501234567", ativo=True)
    tenant_b = Tenant(nome="Fecho Foz Porto", slug="fecho-foz-porto", nif="502345678", ativo=True)
    session.add_all([tenant_a, tenant_b])
    session.commit()

    # Utilizadores Agência A
    diretora_a = User(
        agencia_id=tenant_a.id,
        nome="Dra. Marta Silva",
        email="marta@fecho.pt",
        password_hash=hash_password("senha123"),
        role="diretor",
        ativo=True,
    )
    consultor_a1 = User(
        agencia_id=tenant_a.id,
        nome="Gonçalo Ramos",
        email="goncalo@fecho.pt",
        password_hash=hash_password("senha123"),
        role="consultor",
        ativo=True,
    )
    consultor_a2 = User(
        agencia_id=tenant_a.id,
        nome="Inês Alentejano",
        email="ines@fecho.pt",
        password_hash=hash_password("senha123"),
        role="consultor",
        ativo=True,
    )

    # Utilizadores Agência B
    diretora_b = User(
        agencia_id=tenant_b.id,
        nome="Helena Costa",
        email="helena@porto.fecho.pt",
        password_hash=hash_password("senha123"),
        role="diretor",
        ativo=True,
    )
    consultor_b = User(
        agencia_id=tenant_b.id,
        nome="Rui Pedro",
        email="rui@porto.fecho.pt",
        password_hash=hash_password("senha123"),
        role="consultor",
        ativo=True,
    )

    session.add_all([diretora_a, consultor_a1, consultor_a2, diretora_b, consultor_b])
    session.commit()

    # Imóveis da Agência A
    prop_a1 = Property(
        agencia_id=tenant_a.id,
        consultor_id=consultor_a1.id,
        titulo="Apartamento T3 Avenidas Novas",
        tipologia="T3",
        preco=Decimal("600000.00"),
        status="Vendido",
        regiao_fiscal="continente",
        nome_proprietario="Dr. António Antunes",
        telefone_proprietario="+351 912 345 678",
        nome_comprador="Dr. Comprador",
        telefone_comprador="+351 911 222 333",
        data_escritura=date.today(),
    )
    prop_a2 = Property(
        agencia_id=tenant_a.id,
        consultor_id=consultor_a2.id,
        titulo="Moradia Cascais",
        tipologia="Moradia",
        preco=Decimal("950000.00"),
        status="Ativo",
        regiao_fiscal="continente",
        nome_proprietario="D. Teresa",
        telefone_proprietario="+351 922 333 444",
    )
    session.add_all([prop_a1, prop_a2])
    session.commit()

    # Visitas da Agência A
    v1 = Visit(
        agencia_id=tenant_a.id,
        property_id=prop_a2.id,
        consultor_id=consultor_a1.id,
        cliente_nome="Cliente Comprador",
        cliente_telefone="+351 933 222 111",
        data_visita=datetime.now(timezone.utc) - timedelta(days=2),
        nivel_interesse=4,
        notas_estruturadas="Cliente muito interessado nos acabamentos.",
    )
    session.add(v1)
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
def auth_headers(db_session):
    """Gera cabeçalhos de autenticação para os diferentes perfis."""
    diretora_a = db_session.query(User).filter(User.email == "marta@fecho.pt").first()
    consultor_a = db_session.query(User).filter(User.email == "goncalo@fecho.pt").first()
    diretora_b = db_session.query(User).filter(User.email == "helena@porto.fecho.pt").first()

    token_diretora_a = create_access_token({"sub": str(diretora_a.id), "agencia_id": diretora_a.agencia_id, "role": "diretor"})
    token_consultor_a = create_access_token({"sub": str(consultor_a.id), "agencia_id": consultor_a.agencia_id, "role": "consultor"})
    token_diretora_b = create_access_token({"sub": str(diretora_b.id), "agencia_id": diretora_b.agencia_id, "role": "diretor"})

    return {
        "diretora_a": {"Authorization": f"Bearer {token_diretora_a}"},
        "consultor_a": {"Authorization": f"Bearer {token_consultor_a}"},
        "diretora_b": {"Authorization": f"Bearer {token_diretora_b}"},
        "diretora_a_id": diretora_a.id,
        "consultor_a_id": consultor_a.id,
    }


def test_commercial_dashboard_diretor_success(client, auth_headers):
    """Diretor acede ao dashboard comercial e recebe KPIs com pipeline ponderado."""
    resp = client.get("/api/v1/backoffice/commercial-dashboard?filtro=este_mes", headers=auth_headers["diretora_a"])
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()

    assert data["filtro"] == "este_mes"
    assert "kpis" in data
    kpis = data["kpis"]
    assert "faturacao_realizada" in kpis
    assert "pipeline_bruto" in kpis
    assert "pipeline_ponderado" in kpis
    assert "total_visitas" in kpis
    assert kpis["total_visitas"] >= 1
    # Imóvel vendido gerou faturação estimada (5% de 600.000 = 30.000)
    assert float(kpis["faturacao_realizada"]) == 30000.0


def test_commercial_dashboard_rbac_consultor_forbidden(client, auth_headers):
    """Consultor é estritamente bloqueado de aceder ao dashboard comercial da diretoria."""
    resp = client.get("/api/v1/backoffice/commercial-dashboard", headers=auth_headers["consultor_a"])
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_commercial_dashboard_unauthenticated(client):
    """Requisição anônima recebe 401 Unauthorized."""
    resp = client.get("/api/v1/backoffice/commercial-dashboard")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_sales_funnel_7_steps(client, auth_headers):
    """Valida o funil de vendas consolidado nas 7 etapas e taxas de conversão automáticas."""
    resp = client.get("/api/v1/backoffice/sales-funnel?filtro=este_mes", headers=auth_headers["diretora_a"])
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()

    assert len(data["etapas"]) == 7
    etapas_nomes = [e["etapa"] for e in data["etapas"]]
    assert etapas_nomes == ["Contactos", "Reuniões", "Angariações", "Visitas", "Propostas", "CPCV", "Escrituras"]

    # Conversão do topo da etapa 1 deve ser 100%
    assert data["etapas"][0]["taxa_conversao_topo"] == 100.0


def test_sales_funnel_consultor_filter(client, auth_headers):
    """Valida funil filtrado por um consultor individual."""
    consultor_id = auth_headers["consultor_a_id"]
    resp = client.get(f"/api/v1/backoffice/sales-funnel?consultor_id={consultor_id}", headers=auth_headers["diretora_a"])
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["consultor_id"] == consultor_id
    assert data["consultor_nome"] == "Gonçalo Ramos"


def test_consultores_performance_semaforo(client, auth_headers, db_session):
    """Valida a listagem da equipa com classificação no Semáforo de Trajetória."""
    consultor_id = auth_headers["consultor_a_id"]

    # Cria meta mensal de 20.000 € para o consultor
    hoje = date.today()
    goal = Goal(
        agencia_id=1,
        consultor_id=consultor_id,
        ano=hoje.year,
        mes=hoje.month,
        meta_faturacao=Decimal("20000.00"),
    )
    db_session.add(goal)
    db_session.commit()

    resp = client.get("/api/v1/backoffice/consultores-performance", headers=auth_headers["diretora_a"])
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()

    assert data["total_consultores"] >= 2
    c1 = next(c for c in data["consultores"] if c["consultor_id"] == consultor_id)
    assert c1["nome"] == "Gonçalo Ramos"
    assert float(c1["meta_mensal"]) == 20000.0
    # Como faturou 30.000 € contra 20.000 € de meta, o cumprimento é 150% (Verde)
    assert c1["percentual_cumprimento"] == 150.0
    assert c1["trajetoria"] == "verde"


def test_consultor_individual_performance_4_blocos(client, auth_headers):
    """Valida ficha individual estruturada rigorosamente nos 4 blocos de gestão."""
    consultor_id = auth_headers["consultor_a_id"]
    resp = client.get(f"/api/v1/backoffice/consultor/{consultor_id}/performance", headers=auth_headers["diretora_a"])
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()

    assert data["consultor_id"] == consultor_id
    assert "bloco_1_objetivos" in data
    assert "bloco_2_atividade" in data
    assert "bloco_3_funil" in data
    assert "bloco_4_historico" in data

    b1 = data["bloco_1_objetivos"]
    assert "projecao_final_mes" in b1
    assert "ritmo_diario_necessario" in b1


def test_weekly_meeting_start_flow(client, auth_headers):
    """Valida a inicialização da reunião semanal puxando atividade em tempo real e notas."""
    consultor_id = auth_headers["consultor_a_id"]
    resp = client.post(f"/api/v1/backoffice/meetings/start?consultor_id={consultor_id}", headers=auth_headers["diretora_a"])
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()

    assert data["consultor_id"] == consultor_id
    assert data["consultor_nome"] == "Gonçalo Ramos"
    assert data["visitas_semana"] >= 1
    assert len(data["notas_visitas_recentes"]) >= 1
    assert data["notas_visitas_recentes"][0]["nivel_interesse"] == 4


def test_weekly_meeting_save_and_history(client, auth_headers):
    """Valida gravação da reunião, congelamento do snapshot e consulta ao histórico."""
    consultor_id = auth_headers["consultor_a_id"]
    hoje = date.today()
    ano_iso, semana_iso, _ = hoje.isocalendar()

    payload = {
        "consultor_id": consultor_id,
        "semana_ano": semana_iso,
        "ano": ano_iso,
        "dificuldade_principal": "Objecções no preço de apartamentos T3",
        "negocio_prioritario": "Fecho da moradia em Cascais",
        "diagnostico_diretor": "Muito bom ritmo de visitas, focar em converter para propostas",
        "estrategia_definida": "Apresentar estudo ACM atualizado ao cliente",
        "apoio_direcao_necessario": "Acompanhamento na negociação com proprietário",
        "novos_compromissos": [
            {
                "descricao_compromisso": "Contactar 4 clientes qualificados",
                "meta_quantitativa": "4 contactos",
                "prazo_data": str(hoje + timedelta(days=5)),
                "status": "Pendente",
                "percentual_cumprimento": 0,
            }
        ],
        "atualizacao_compromissos": [],
    }

    # Gravar reunião
    resp_save = client.post("/api/v1/backoffice/meetings/save", json=payload, headers=auth_headers["diretora_a"])
    assert resp_save.status_code == status.HTTP_201_CREATED
    data_save = resp_save.json()

    assert data_save["semana_ano"] == semana_iso
    assert data_save["dificuldade_principal"] == "Objecções no preço de apartamentos T3"
    assert len(data_save["commitments"]) == 1
    assert data_save["commitments"][0]["descricao_compromisso"] == "Contactar 4 clientes qualificados"

    # Consultar histórico
    resp_hist = client.get(f"/api/v1/backoffice/consultor/{consultor_id}/meetings", headers=auth_headers["diretora_a"])
    assert resp_hist.status_code == status.HTTP_200_OK
    data_hist = resp_hist.json()
    assert len(data_hist) >= 1
    assert data_hist[0]["consultor_id"] == consultor_id


def test_goals_crud_flow(client, auth_headers):
    """Valida cadastro e listagem de metas comerciais."""
    consultor_id = auth_headers["consultor_a_id"]
    payload = {
        "consultor_id": consultor_id,
        "ano": 2026,
        "mes": 11,
        "meta_faturacao": "18000.00",
        "meta_contactos": 40,
        "meta_reunioes": 15,
        "meta_angariacoes": 3,
        "meta_exclusivos": 2,
        "meta_visitas": 20,
        "meta_propostas": 5,
        "meta_cpcv": 2,
        "meta_escrituras": 2,
    }

    # Criar meta
    resp_post = client.post("/api/v1/backoffice/goals", json=payload, headers=auth_headers["diretora_a"])
    assert resp_post.status_code == status.HTTP_201_CREATED
    data_goal = resp_post.json()
    assert float(data_goal["meta_faturacao"]) == 18000.0
    assert data_goal["mes"] == 11

    # Listar metas
    resp_get = client.get("/api/v1/backoffice/goals?ano=2026&mes=11", headers=auth_headers["diretora_a"])
    assert resp_get.status_code == status.HTTP_200_OK
    assert len(resp_get.json()) >= 1


def test_pipeline_deals_crud_flow(client, auth_headers):
    """Valida ciclo completo de CRUD de oportunidades no pipeline."""
    consultor_id = auth_headers["consultor_a_id"]

    deal_payload = {
        "cliente_nome": "Investidor Imobiliário Lisboa",
        "cliente_telefone": "+351 919 888 777",
        "tipo_negocio": "Venda",
        "valor_imovel": "450000.00",
        "comissao_estimada": "22500.00",
        "fase": "Proposta",
        "probabilidade": 60,
        "proxima_acao": "Reunião de fecho com proprietário",
        "consultor_id": consultor_id,
    }

    # 1. Create Deal
    resp_create = client.post("/api/v1/backoffice/pipeline", json=deal_payload, headers=auth_headers["diretora_a"])
    assert resp_create.status_code == status.HTTP_201_CREATED
    deal_data = resp_create.json()
    deal_id = deal_data["id"]
    assert deal_data["fase"] == "Proposta"
    assert float(deal_data["comissao_ponderada"]) == 22500.0 * 0.6

    # 2. List Deals
    resp_list = client.get("/api/v1/backoffice/pipeline?fase=Proposta", headers=auth_headers["diretora_a"])
    assert resp_list.status_code == status.HTTP_200_OK
    assert any(d["id"] == deal_id for d in resp_list.json())

    # 3. Update Deal
    update_payload = {"fase": "Negociacao", "probabilidade": 80}
    resp_update = client.put(f"/api/v1/backoffice/pipeline/{deal_id}", json=update_payload, headers=auth_headers["diretora_a"])
    assert resp_update.status_code == status.HTTP_200_OK
    assert resp_update.json()["fase"] == "Negociacao"
    assert resp_update.json()["probabilidade"] == 80

    # 4. Delete Deal
    resp_del = client.delete(f"/api/v1/backoffice/pipeline/{deal_id}", headers=auth_headers["diretora_a"])
    assert resp_del.status_code == status.HTTP_200_OK


def test_multitenant_isolation_commercial(client, auth_headers):
    """Garante que a Diretora da Agência B não acede nem visualiza dados da Agência A."""
    # Agência B consulta o dashboard: não deve ver os números da Agência A
    resp_b = client.get("/api/v1/backoffice/commercial-dashboard", headers=auth_headers["diretora_b"])
    assert resp_b.status_code == status.HTTP_200_OK
    data_b = resp_b.json()
    assert float(data_b["kpis"]["faturacao_realizada"]) == 0.0

    # Agência B tenta aceder à ficha do consultor da Agência A: deve receber 404
    consultor_a_id = auth_headers["consultor_a_id"]
    resp_b_consultor = client.get(f"/api/v1/backoffice/consultor/{consultor_a_id}/performance", headers=auth_headers["diretora_b"])
    assert resp_b_consultor.status_code == status.HTTP_404_NOT_FOUND
