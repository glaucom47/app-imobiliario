"""
Suíte de Testes Automatizados para a Fase 9: Backoffice Web da Agência, Métricas e Exportação CSV.

Cenários Validados:
1. Bloqueio RBAC rigoroso:
   - Usuário não autenticado recebe 401 Unauthorized;
   - Usuário com perfil 'consultor' recebe 403 Forbidden;
   - Usuário com perfil 'diretor' obtém acesso total (200 OK / 201 Created).
2. Isolamento Multi-tenant:
   - Dados, métricas, tags e exportações são rigorosamente filtrados por agencia_id;
   - Diretor da Agência A não acede a dados ou imóveis da Agência B.
3. KPIs da Agência e Assiduidade dos Consultores:
   - Total de visitas no período (7, 30 dias ou total);
   - Taxa de adesão ao feedback por voz (% de visitas com notas ou áudio);
   - Taxa de prestação de contas ao proprietário (% com feedback_enviado_proprietario);
   - Nível médio de interesse dos clientes;
   - Ranking de assiduidade individual por consultor.
4. Inteligência de Objeções e Renegociação de Preços:
   - Consolidação de objeções por imóvel e agência;
   - Contagem e percentual sobre o total de visitas;
   - Geração de parecer/argumento técnico para fundamentação de descida de preço junto ao proprietário.
5. Catálogo Corporativo de Tags de Objeção:
   - Listagem, criação e edição de tags;
   - Bloqueio de duplicidade na mesma agência;
   - Ativação/Desativação de tags.
6. Parametrizações Financeiras e Operacionais (Settings):
   - Inicialização com defaults corporativos;
   - Atualização remota de spread de referência, taxa de stress, prazo máximo, LTV e hora de aniversários.
7. Exportação de Relatórios em Formato Aberto CSV:
   - Formato UTF-8 com BOM (\\ufeff) para abertura direta no Excel e Numbers;
   - Delimitador europeu ';';
   - Sanitização contra CSV Injection (prefixação de valores iniciando em '=', '+', '-', '@');
   - Exportação de Visitas, Imóveis, Objeções Consolidadas e Esfera de Influência (RGPD preservado).
"""
from datetime import date, datetime, timedelta, timezone
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from database.connection import Base, get_db
from app.models.contact import Contact
from app.models.objection import ObjectionTag, VisitObjection
from app.models.property import Property
from app.models.settings import Settings
from app.models.tenant import Tenant
from app.models.user import User
from app.models.visit import Visit
from app.services.auth_service import create_access_token, hash_password


@pytest.fixture(scope="function")
def db_session():
    """Sessão de banco isolada em memória com duas agências e usuários de teste."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    # Criação de Agências A e B
    tenant_a = Tenant(nome="Fecho Prime Lisboa", slug="fecho-prime-lisboa", nif="501234567", ativo=True)
    tenant_b = Tenant(nome="Fecho Foz Porto", slug="fecho-foz-porto", nif="502345678", ativo=True)
    session.add_all([tenant_a, tenant_b])
    session.commit()

    # Usuários Agência A
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

    # Usuários Agência B
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

    # Tags de Objeção Agência A
    tag_preco_a = ObjectionTag(agencia_id=tenant_a.id, tag="Preço Elevado", categoria="preco", ativo=True)
    tag_ruido_a = ObjectionTag(agencia_id=tenant_a.id, tag="Ruído Excessivo", categoria="localizacao", ativo=True)
    tag_obras_a = ObjectionTag(agencia_id=tenant_a.id, tag="Cozinha a Precisar Obras", categoria="estado", ativo=True)

    # Tag Agência B
    tag_b = ObjectionTag(agencia_id=tenant_b.id, tag="Garagem Estreita", categoria="dimensao", ativo=True)

    session.add_all([tag_preco_a, tag_ruido_a, tag_obras_a, tag_b])
    session.commit()

    # Imóveis Agência A
    prop_a1 = Property(
        agencia_id=tenant_a.id,
        consultor_id=consultor_a1.id,
        titulo="Apartamento T3 nas Avenidas Novas",
        tipologia="T3",
        preco=650000.0,
        status="Ativo",
        regiao_fiscal="continente",
        nome_proprietario="Dr. António Antunes",
        telefone_proprietario="+351912345678",
    )
    prop_a2 = Property(
        agencia_id=tenant_a.id,
        consultor_id=consultor_a2.id,
        titulo="Moradia T4 no Restelo",
        tipologia="T4",
        preco=1200000.0,
        status="Vendido",
        regiao_fiscal="continente",
        nome_proprietario="Eng. Sofia Ferreira",
        telefone_proprietario="+351919999999",
        nome_comprador="Carlos Nobre",
        telefone_comprador="+351933333333",
        data_escritura=date(2025, 4, 15),
    )

    # Imóvel Agência B
    prop_b = Property(
        agencia_id=tenant_b.id,
        consultor_id=consultor_b.id,
        titulo="Penthouse T2 na Foz do Douro",
        tipologia="T2",
        preco=550000.0,
        status="Ativo",
        regiao_fiscal="continente",
        nome_proprietario="Dr. Manuel Porto",
        telefone_proprietario="+351918888888",
    )

    session.add_all([prop_a1, prop_a2, prop_b])
    session.commit()

    # Visitas Agência A
    # Visita 1 (Gonçalo, LX-100, com áudio e objeção de preço)
    v1 = Visit(
        agencia_id=tenant_a.id,
        property_id=prop_a1.id,
        consultor_id=consultor_a1.id,
        cliente_nome="Beatriz Santos",
        cliente_telefone="+351921111111",
        audio_duracao_segundos=18,
        transcricao="Gostou da luz mas achou o preço por metro quadrado muito puxado.",
        notas_estruturadas="Cliente qualificada. Considera proposta com desconto.",
        nivel_interesse=3,
        feedback_enviado_proprietario=True,
    )
    # Visita 2 (Gonçalo, LX-100, com notas e objeções de preço e obras)
    v2 = Visit(
        agencia_id=tenant_a.id,
        property_id=prop_a1.id,
        consultor_id=consultor_a1.id,
        cliente_nome="Pedro Álvares",
        cliente_telefone="+351922222222",
        transcricao="Apartamento precisa de obras na cozinha e o valor pedido não reflete isso.",
        nivel_interesse=2,
        feedback_enviado_proprietario=False,
    )
    # Visita 3 (Inês, LX-200, com áudio e interesse alto)
    v3 = Visit(
        agencia_id=tenant_a.id,
        property_id=prop_a2.id,
        consultor_id=consultor_a2.id,
        cliente_nome="Carlos Nobre",
        cliente_telefone="+351933333333",
        audio_duracao_segundos=25,
        transcricao="Excelente moradia, cliente pronto para avançar para a reserva.",
        nivel_interesse=5,
        feedback_enviado_proprietario=True,
    )
    session.add_all([v1, v2, v3])
    session.commit()

    # Vínculo de objeções
    vo1 = VisitObjection(
        agencia_id=tenant_a.id,
        visit_id=v1.id,
        property_id=prop_a1.id,
        tag_id=tag_preco_a.id,
    )
    vo2 = VisitObjection(
        agencia_id=tenant_a.id,
        visit_id=v2.id,
        property_id=prop_a1.id,
        tag_id=tag_preco_a.id,
    )
    vo3 = VisitObjection(
        agencia_id=tenant_a.id,
        visit_id=v2.id,
        property_id=prop_a1.id,
        tag_id=tag_obras_a.id,
    )
    session.add_all([vo1, vo2, vo3])
    session.commit()

    # Contacto na Esfera de Influência Agência A (um ativo e um anonimizado)
    c1 = Contact(
        agencia_id=tenant_a.id,
        consultor_id=consultor_a2.id,
        property_id=prop_a2.id,
        nome="Carlos Nobre",
        telemovel="+351933333333",
        tipo="comprador",
        data_escritura=date(2025, 4, 15),
        anonimizado=False,
    )
    c2_anon = Contact(
        agencia_id=tenant_a.id,
        consultor_id=consultor_a1.id,
        nome="Cliente Anonimizado",
        telemovel="000000000",
        tipo="comprador",
        data_escritura=date(2024, 10, 1),
        anonimizado=True,
    )
    session.add_all([c1, c2_anon])
    session.commit()

    yield session


@pytest.fixture(scope="function")
def client(db_session):
    """Cliente HTTP com override de banco em memória."""
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
    token = create_access_token(
        data={"sub": str(user.id), "agencia_id": user.agencia_id, "role": user.role, "email": user.email}
    )
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# 1. BLOQUEIO RBAC E AUTENTICAÇÃO
# ============================================================================

def test_rbac_unauthenticated_blocked(client: TestClient):
    """Garante que requisições sem token aos endpoints do backoffice retornam 401."""
    assert client.get("/api/v1/backoffice/kpis").status_code == status.HTTP_401_UNAUTHORIZED
    assert client.get("/api/v1/backoffice/objections-analytics").status_code == status.HTTP_401_UNAUTHORIZED
    assert client.get("/api/v1/backoffice/tags").status_code == status.HTTP_401_UNAUTHORIZED
    assert client.get("/api/v1/backoffice/settings").status_code == status.HTTP_401_UNAUTHORIZED
    assert client.get("/api/v1/backoffice/export/csv?tipo=visitas").status_code == status.HTTP_401_UNAUTHORIZED


def test_rbac_consultor_blocked(client: TestClient, db_session):
    """Garante que usuários com perfil 'consultor' recebem 403 Forbidden."""
    consultor = db_session.query(User).filter(User.role == "consultor").first()
    headers = get_token_headers(consultor)

    res_kpis = client.get("/api/v1/backoffice/kpis", headers=headers)
    assert res_kpis.status_code == status.HTTP_403_FORBIDDEN
    assert "Direção Comercial" in res_kpis.json()["detail"]

    res_analytics = client.get("/api/v1/backoffice/objections-analytics", headers=headers)
    assert res_analytics.status_code == status.HTTP_403_FORBIDDEN

    res_settings = client.get("/api/v1/backoffice/settings", headers=headers)
    assert res_settings.status_code == status.HTTP_403_FORBIDDEN

    res_export = client.get("/api/v1/backoffice/export/csv?tipo=visitas", headers=headers)
    assert res_export.status_code == status.HTTP_403_FORBIDDEN


def test_rbac_director_authorized(client: TestClient, db_session):
    """Garante que usuários com perfil 'diretor' têm acesso pleno (200 OK)."""
    diretor = db_session.query(User).filter(User.role == "diretor").first()
    headers = get_token_headers(diretor)

    res = client.get("/api/v1/backoffice/kpis", headers=headers)
    assert res.status_code == status.HTTP_200_OK


# ============================================================================
# 2. KPIS DE ASSIDUIDADE E TAXA DE ADESÃO
# ============================================================================

def test_kpis_calculation_and_consultor_ranking(client: TestClient, db_session):
    """Valida o cálculo exato dos KPIs corporativos e métricas por consultor."""
    diretora_a = db_session.query(User).filter(User.email == "marta@fecho.pt").first()
    headers = get_token_headers(diretora_a)

    res = client.get("/api/v1/backoffice/kpis", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    # Agência A possui 3 visitas no total
    assert data["total_visitas"] == 3
    # Todas as 3 possuem áudio ou notas
    assert data["visitas_com_feedback"] == 3
    assert data["taxa_adesao_percent"] == 100.0
    # 2 visitas com feedback enviado ao proprietário (v1 e v3)
    assert data["visitas_enviadas_proprietario"] == 2
    assert data["taxa_prestacao_contas_percent"] == 66.7
    # Média de interesse: (3 + 2 + 5) / 3 = 3.33
    assert data["nivel_interesse_medio"] == 3.33
    # Top objeção é "Preço Elevado" (2 ocorrências)
    assert data["top_objecao"] == "Preço Elevado"

    # Verificar ranking de consultores
    ranking = data["consultores_assiduidade"]
    assert len(ranking) == 2

    # Gonçalo Ramos realizou 2 visitas
    goncalo_stat = next(c for c in ranking if c["nome"] == "Gonçalo Ramos")
    assert goncalo_stat["total_visitas"] == 2
    assert goncalo_stat["visitas_com_feedback"] == 2
    assert goncalo_stat["taxa_adesao_percent"] == 100.0
    assert goncalo_stat["nivel_interesse_medio"] == 2.5

    # Inês Alentejano realizou 1 visita
    ines_stat = next(c for c in ranking if c["nome"] == "Inês Alentejano")
    assert ines_stat["total_visitas"] == 1
    assert ines_stat["nivel_interesse_medio"] == 5.0


def test_kpis_filter_by_days(client: TestClient, db_session):
    """Testa filtro de período em dias para os KPIs."""
    diretora_a = db_session.query(User).filter(User.email == "marta@fecho.pt").first()
    headers = get_token_headers(diretora_a)

    res = client.get("/api/v1/backoffice/kpis?dias=30", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["periodo_dias"] == 30


# ============================================================================
# 3. INTELIGÊNCIA DE OBJEÇÕES E RENEGOCIAÇÃO DE PREÇOS
# ============================================================================

def test_objections_analytics_agency_overview(client: TestClient, db_session):
    """Valida visão geral das objeções de toda a agência."""
    diretora_a = db_session.query(User).filter(User.email == "marta@fecho.pt").first()
    headers = get_token_headers(diretora_a)

    res = client.get("/api/v1/backoffice/objections-analytics", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    assert data["total_visitas_imovel"] == 3
    assert data["total_visitas_com_objecoes"] == 2
    assert len(data["distribuicao"]) >= 2

    top_item = data["distribuicao"][0]
    assert top_item["tag"] == "Preço Elevado"
    assert top_item["total_ocorrencias"] == 2
    assert top_item["percentual_visitas"] == 66.7


def test_objections_analytics_specific_property_and_negotiation_argument(client: TestClient, db_session):
    """Valida analítica de um imóvel específico e geração do parecer de renegociação de preços."""
    diretora_a = db_session.query(User).filter(User.email == "marta@fecho.pt").first()
    prop_lx100 = db_session.query(Property).filter(Property.titulo == "Apartamento T3 nas Avenidas Novas").first()
    headers = get_token_headers(diretora_a)

    res = client.get(f"/api/v1/backoffice/objections-analytics?property_id={prop_lx100.id}", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    assert data["property_id"] == prop_lx100.id
    assert data["property_titulo"] == "Apartamento T3 nas Avenidas Novas"
    assert data["nome_proprietario"] == "Dr. António Antunes"
    assert data["total_visitas_imovel"] == 2
    assert data["total_visitas_com_objecoes"] == 2

    # Verifica texto de fundamentação técnica
    resumo = data["resumo_renegociacao"]
    assert "Dr. António Antunes" in resumo
    assert "Preço Elevado" in resumo
    assert "necessidade de um ajuste de posicionamento de preço" in resumo


def test_objections_analytics_multi_tenant_isolation(client: TestClient, db_session):
    """Diretor da Agência A não pode consultar analítica de imóvel da Agência B."""
    diretora_a = db_session.query(User).filter(User.email == "marta@fecho.pt").first()
    prop_b = db_session.query(Property).filter(Property.titulo == "Penthouse T2 na Foz do Douro").first()
    headers = get_token_headers(diretora_a)

    res = client.get(f"/api/v1/backoffice/objections-analytics?property_id={prop_b.id}", headers=headers)
    assert res.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# 4. GESTÃO DO CATÁLOGO DE TAGS DE OBJEÇÃO
# ============================================================================

def test_tags_crud_and_uniqueness(client: TestClient, db_session):
    """Valida listagem, criação, unicidade e desativação de tags corporativas."""
    diretora_a = db_session.query(User).filter(User.email == "marta@fecho.pt").first()
    headers = get_token_headers(diretora_a)

    # 1. Listar tags da Agência A
    res_list = client.get("/api/v1/backoffice/tags", headers=headers)
    assert res_list.status_code == status.HTTP_200_OK
    tags = res_list.json()
    assert len(tags) == 3
    assert not any(t["tag"] == "Garagem Estreita" for t in tags)  # Garagem Estreita é da Agência B

    # 2. Criar nova tag com sucesso
    res_create = client.post(
        "/api/v1/backoffice/tags",
        json={"tag": "Condomínio Elevado", "categoria": "preco", "ativo": True},
        headers=headers,
    )
    assert res_create.status_code == status.HTTP_201_CREATED
    new_tag = res_create.json()
    assert new_tag["tag"] == "Condomínio Elevado"
    assert new_tag["categoria"] == "preco"

    # 3. Tentar duplicar nome da tag na mesma agência (conflito 409)
    res_dup = client.post(
        "/api/v1/backoffice/tags",
        json={"tag": "Condomínio Elevado", "categoria": "preco"},
        headers=headers,
    )
    assert res_dup.status_code == status.HTTP_409_CONFLICT

    # 4. Atualizar tag para inativa
    res_update = client.put(
        f"/api/v1/backoffice/tags/{new_tag['id']}",
        json={"ativo": False},
        headers=headers,
    )
    assert res_update.status_code == status.HTTP_200_OK
    assert res_update.json()["ativo"] is False


# ============================================================================
# 5. PARAMETRIZAÇÕES FINANCEIRAS REMOTAS (SETTINGS)
# ============================================================================

def test_agency_settings_read_and_update(client: TestClient, db_session):
    """Valida leitura e atualização das configurações financeiras da agência."""
    diretora_a = db_session.query(User).filter(User.email == "marta@fecho.pt").first()
    headers = get_token_headers(diretora_a)

    # 1. Leitura inicial (gera defaults se não existir)
    res_get = client.get("/api/v1/backoffice/settings", headers=headers)
    assert res_get.status_code == status.HTTP_200_OK
    settings = res_get.json()
    assert settings["spread_referencia"] == 0.85
    assert settings["taxa_stress"] == 1.50
    assert settings["prazo_max_financiamento_anos"] == 30
    assert settings["percentual_financiamento_max"] == 85.0
    assert settings["hora_notificacao_aniversario"] == "09:00"

    # 2. Atualização
    res_put = client.put(
        "/api/v1/backoffice/settings",
        json={
            "spread_referencia": 0.75,
            "taxa_stress": 1.25,
            "prazo_max_financiamento_anos": 35,
            "percentual_financiamento_max": 90.0,
            "hora_notificacao_aniversario": "08:45",
        },
        headers=headers,
    )
    assert res_put.status_code == status.HTTP_200_OK
    updated = res_put.json()
    assert updated["spread_referencia"] == 0.75
    assert updated["taxa_stress"] == 1.25
    assert updated["prazo_max_financiamento_anos"] == 35
    assert updated["percentual_financiamento_max"] == 90.0
    assert updated["hora_notificacao_aniversario"] == "08:45"


# ============================================================================
# 6. EXPORTAÇÃO DE RELATÓRIOS EM FORMATO ABERTO CSV
# ============================================================================

def test_export_csv_visitas(client: TestClient, db_session):
    """Valida exportação CSV de visitas com UTF-8 BOM e cabeçalhos em português."""
    diretora_a = db_session.query(User).filter(User.email == "marta@fecho.pt").first()
    headers = get_token_headers(diretora_a)

    res = client.get("/api/v1/backoffice/export/csv?tipo=visitas", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    assert "text/csv" in res.headers["content-type"]
    assert "attachment; filename=fecho_visitas_" in res.headers["content-disposition"]

    content = res.content.decode("utf-8")
    # Verifica presença de UTF-8 BOM
    assert content.startswith("\ufeff")
    # Verifica delimitador ';'
    assert "ID Visita;Data e Hora;Consultor" in content
    assert "Gonçalo Ramos" in content
    assert "Beatriz Santos" in content
    assert "Preço Elevado" in content


def test_export_csv_imoveis(client: TestClient, db_session):
    """Valida exportação CSV da carteira de imóveis."""
    diretora_a = db_session.query(User).filter(User.email == "marta@fecho.pt").first()
    headers = get_token_headers(diretora_a)

    res = client.get("/api/v1/backoffice/export/csv?tipo=imoveis", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    content = res.content.decode("utf-8")

    assert content.startswith("\ufeff")
    assert "ID Imóvel;Título" in content
    assert "Apartamento T3 nas Avenidas Novas" in content
    assert "Moradia T4 no Restelo" in content
    # Imóvel da Agência B não deve vazar
    assert "Penthouse T2 na Foz do Douro" not in content


def test_export_csv_objecoes(client: TestClient, db_session):
    """Valida exportação CSV de distribuição de objeções."""
    diretora_a = db_session.query(User).filter(User.email == "marta@fecho.pt").first()
    headers = get_token_headers(diretora_a)

    res = client.get("/api/v1/backoffice/export/csv?tipo=objecoes", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    content = res.content.decode("utf-8")

    assert content.startswith("\ufeff")
    assert "Tag de Objeção;Categoria;Ocorrências Registradas" in content
    assert "Preço Elevado" in content
    assert "Cozinha a Precisar Obras" in content


def test_export_csv_contactos_rgpd(client: TestClient, db_session):
    """Valida exportação CSV de contatos e preservação do status 'Cliente Anonimizado' conforme RGPD."""
    diretora_a = db_session.query(User).filter(User.email == "marta@fecho.pt").first()
    headers = get_token_headers(diretora_a)

    res = client.get("/api/v1/backoffice/export/csv?tipo=contactos", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    content = res.content.decode("utf-8")

    assert content.startswith("\ufeff")
    assert "Carlos Nobre" in content
    assert "Cliente Anonimizado" in content
    assert "Anonimizado (RGPD)" in content


def test_csv_injection_sanitization(client: TestClient, db_session):
    """
    Testa sanitização contra CSV Formula Injection.
    Campos que comecem com '=', '+', '-', '@' devem ser prefixados com aspas simples (').
    """
    diretora_a = db_session.query(User).filter(User.email == "marta@fecho.pt").first()
    # Adiciona visita com nome malicioso
    prop = db_session.query(Property).filter(Property.titulo == "Apartamento T3 nas Avenidas Novas").first()
    v_malicious = Visit(
        agencia_id=diretora_a.agencia_id,
        property_id=prop.id,
        consultor_id=prop.consultor_id,
        cliente_nome="=SUM(1+1)",
        cliente_telefone="+351999999999",
        transcricao="@cmd /c calc",
    )
    db_session.add(v_malicious)
    db_session.commit()

    headers = get_token_headers(diretora_a)
    res = client.get("/api/v1/backoffice/export/csv?tipo=visitas", headers=headers)
    content = res.content.decode("utf-8")

    # Deve conter '=SUM e '@cmd prefixados com aspas simples para impedir execução no Excel
    assert "'=SUM(1+1)" in content
    assert "'@cmd /c calc" in content
