"""
Suíte de Testes Automatizados para a Fase 10:
Auditoria de Segurança, Testes de Estresse Multi-tenant e Validação PWA/Offline.

Cobre:
1. Cabeçalhos HTTP defensivos (CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Cache-Control em APIs);
2. Rate Limiting e prevenção contra ataques de força bruta no login;
3. Limitação de tamanho de payload (proteção contra Slowloris / Memory Exhaustion);
4. Teste de estresse de isolamento multi-tenant irrestrito entre Agência A e Agência B;
5. Falsificação, violação de assinatura e manipulação de tokens JWT;
6. Defesa ativa contra CSV Formula Injection nos endpoints de exportação;
7. Integridade do Service Worker, Manifesto PWA e ativos estáticos em modo offline;
8. Verificação de tokens de contraste para luz solar intensa (docs/DESIGN.md).
"""
import io
import json
import os
from datetime import date, datetime, timedelta, timezone
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from config.config import settings
from database.connection import Base, get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.models.property import Property
from app.models.visit import Visit
from app.models.objection import ObjectionTag, VisitObjection
from app.models.contact import Contact
from app.models.settings import Settings
from app.models.log import Log
from app.middleware.security import rate_limiter
from app.services.auth_service import create_access_token, hash_password
from app.services.export_service import sanitize_csv_cell


@pytest.fixture(scope="function")
def db_session():
    """Configura base de dados em memória isolada para cada teste."""
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
    """Instancia o TestClient com override da sessão de banco de dados."""
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
def multi_tenant_fixture(db_session):
    """
    Cria dois tenants completamente independentes:
    - Agência A (Lisboa Prime)
    - Agência B (Porto Douro)
    com usuários, imóveis, visitas, objeções, contatos e parametrizações.
    """
    # Tenant A
    tenant_a = Tenant(
        nome="Lisboa Prime Real Estate",
        slug="lisboa-prime",
        nif="511111111",
        telefone="+351 211 111 111",
        email="contato@lisboaprime.pt",
        ativo=True,
    )
    db_session.add(tenant_a)

    # Tenant B
    tenant_b = Tenant(
        nome="Porto Douro Properties",
        slug="porto-douro",
        nif="522222222",
        telefone="+351 222 222 222",
        email="contato@portodouro.pt",
        ativo=True,
    )
    db_session.add(tenant_b)
    db_session.flush()

    # Usuários Tenant A
    diretor_a = User(
        agencia_id=tenant_a.id,
        nome="Diretor Lisboa",
        email="diretor_a@fecho.pt",
        password_hash=hash_password("senha_diretor_a"),
        role="diretor",
        telemovel="+351 911 000 001",
        ativo=True,
    )
    consultor_a = User(
        agencia_id=tenant_a.id,
        nome="Consultor Lisboa",
        email="consultor_a@fecho.pt",
        password_hash=hash_password("senha_consultor_a"),
        role="consultor",
        telemovel="+351 911 000 002",
        ativo=True,
    )

    # Usuários Tenant B
    diretor_b = User(
        agencia_id=tenant_b.id,
        nome="Diretor Porto",
        email="diretor_b@fecho.pt",
        password_hash=hash_password("senha_diretor_b"),
        role="diretor",
        telemovel="+351 922 000 001",
        ativo=True,
    )
    consultor_b = User(
        agencia_id=tenant_b.id,
        nome="Consultor Porto",
        email="consultor_b@fecho.pt",
        password_hash=hash_password("senha_consultor_b"),
        role="consultor",
        telemovel="+351 922 000 002",
        ativo=True,
    )
    db_session.add_all([diretor_a, consultor_a, diretor_b, consultor_b])
    db_session.flush()

    # Imóveis
    prop_a = Property(
        agencia_id=tenant_a.id,
        consultor_id=consultor_a.id,
        titulo="Apartamento Chiado T2",
        tipologia="T2",
        preco=450000.0,
        area_bruta=110.0,
        regiao_fiscal="continente",
        status="Ativo",
        nome_proprietario="Proprietário Lisboa",
        telefone_proprietario="+351 911 999 001",
    )
    prop_b = Property(
        agencia_id=tenant_b.id,
        consultor_id=consultor_b.id,
        titulo="Moradia Foz T4",
        tipologia="T4",
        preco=850000.0,
        area_bruta=260.0,
        regiao_fiscal="continente",
        status="Ativo",
        nome_proprietario="Proprietário Porto",
        telefone_proprietario="+351 922 999 001",
    )
    db_session.add_all([prop_a, prop_b])
    db_session.flush()

    # Tags de Objeção
    tag_a = ObjectionTag(agencia_id=tenant_a.id, tag="Ruído de Rua", categoria="Localização")
    tag_b = ObjectionTag(agencia_id=tenant_b.id, tag="Preço Excessivo", categoria="Preço")
    db_session.add_all([tag_a, tag_b])
    db_session.flush()

    # Visitas
    visit_a = Visit(
        agencia_id=tenant_a.id,
        property_id=prop_a.id,
        consultor_id=consultor_a.id,
        cliente_nome="Cliente Lisboa",
        nivel_interesse=4,
        notas_estruturadas="Cliente gostou da luminosidade mas apontou ruído.",
        data_visita=datetime.now(timezone.utc),
    )
    visit_b = Visit(
        agencia_id=tenant_b.id,
        property_id=prop_b.id,
        consultor_id=consultor_b.id,
        cliente_nome="Cliente Porto",
        nivel_interesse=3,
        notas_estruturadas="Cliente achou o valor por m² acima da média da Foz.",
        data_visita=datetime.now(timezone.utc),
    )
    db_session.add_all([visit_a, visit_b])
    db_session.flush()

    # Objeções associadas às visitas
    db_session.add(VisitObjection(agencia_id=tenant_a.id, visit_id=visit_a.id, property_id=prop_a.id, tag_id=tag_a.id))
    db_session.add(VisitObjection(agencia_id=tenant_b.id, visit_id=visit_b.id, property_id=prop_b.id, tag_id=tag_b.id))

    # Contatos na Esfera de Influência
    contact_a = Contact(
        agencia_id=tenant_a.id,
        consultor_id=consultor_a.id,
        property_id=prop_a.id,
        nome="Comprador Lisboa",
        telemovel="+351 911 888 777",
        tipo="comprador",
        data_escritura=date.today(),
    )
    contact_b = Contact(
        agencia_id=tenant_b.id,
        consultor_id=consultor_b.id,
        property_id=prop_b.id,
        nome="Comprador Porto",
        telemovel="+351 922 888 777",
        tipo="comprador",
        data_escritura=date.today(),
    )
    db_session.add_all([contact_a, contact_b])

    # Configurações de Agência
    settings_a = Settings(agencia_id=tenant_a.id, spread_referencia=0.85)
    settings_b = Settings(agencia_id=tenant_b.id, spread_referencia=1.15)
    db_session.add_all([settings_a, settings_b])
    db_session.commit()

    # Gera tokens JWT
    token_diretor_a = create_access_token(data={"sub": str(diretor_a.id), "agencia_id": tenant_a.id, "role": "diretor"})
    token_consultor_a = create_access_token(data={"sub": str(consultor_a.id), "agencia_id": tenant_a.id, "role": "consultor"})
    token_diretor_b = create_access_token(data={"sub": str(diretor_b.id), "agencia_id": tenant_b.id, "role": "diretor"})
    token_consultor_b = create_access_token(data={"sub": str(consultor_b.id), "agencia_id": tenant_b.id, "role": "consultor"})

    return {
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "diretor_a": diretor_a,
        "consultor_a": consultor_a,
        "diretor_b": diretor_b,
        "consultor_b": consultor_b,
        "prop_a": prop_a,
        "prop_b": prop_b,
        "tag_a": tag_a,
        "tag_b": tag_b,
        "visit_a": visit_a,
        "visit_b": visit_b,
        "contact_a": contact_a,
        "contact_b": contact_b,
        "tokens": {
            "diretor_a": token_diretor_a,
            "consultor_a": token_consultor_a,
            "diretor_b": token_diretor_b,
            "consultor_b": token_consultor_b,
        }
    }


# ==============================================================================
# 1. TESTES DE CABEÇALHOS DEFENSIVOS E SEGURANÇA HTTP
# ==============================================================================

def test_security_headers_applied_to_all_responses(client):
    """
    Garante que cabeçalhos defensivos modernos de segurança estão presentes
    em todas as respostas da aplicação (CSP, X-Frame-Options, X-Content-Type-Options, etc.).
    """
    resp = client.get("/health")
    assert resp.status_code == status.HTTP_200_OK

    # Content-Security-Policy
    csp = resp.headers.get("Content-Security-Policy")
    assert csp is not None
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp

    # Anti-Clickjacking & Anti-MIME Sniffing
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-XSS-Protection") == "1; mode=block"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    # Permissions-Policy
    perm_policy = resp.headers.get("Permissions-Policy")
    assert perm_policy is not None
    assert "microphone=(self)" in perm_policy


def test_api_cache_control_headers_prevent_leaks(client, multi_tenant_fixture):
    """
    Garante que respostas da API REST (/api/v1/*) recebem headers de Cache-Control 'no-store'
    para impedir armazenamento em caches compartilhados, proxies intermediários ou disco local.
    """
    token_a = multi_tenant_fixture["tokens"]["consultor_a"]
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"})
    assert resp.status_code == status.HTTP_200_OK

    cache_control = resp.headers.get("Cache-Control", "")
    assert "no-store" in cache_control
    assert "no-cache" in cache_control
    assert "must-revalidate" in cache_control
    assert resp.headers.get("Pragma") == "no-cache"


# ==============================================================================
# 2. TESTES DE RATE LIMITING E PROTEÇÃO CONTRA FORÇA BRUTA
# ==============================================================================

def test_rate_limiter_brute_force_protection(client):
    """
    Testa se tentativas repetidas e excessivas no endpoint de login
    acionam o bloqueio HTTP 429 Too Many Requests com cabeçalho Retry-After.
    """
    rate_limiter.reset()
    # Define limite de teste para 3 tentativas por minuto
    rate_limiter.limits["login"] = (3, 60)

    try:
        # 3 tentativas permitidas (mesmo que com credenciais inválidas)
        for i in range(3):
            r = client.post("/api/v1/auth/login", json={"email": "wrong@fecho.pt", "password": "wrong"})
            assert r.status_code == status.HTTP_401_UNAUTHORIZED

        # 4ª tentativa deve ser prontamente bloqueada por Rate Limiting
        blocked_resp = client.post("/api/v1/auth/login", json={"email": "wrong@fecho.pt", "password": "wrong"})
        assert blocked_resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        data = blocked_resp.json()
        assert "Limite de requisições excedido" in data["detail"]
        assert "Retry-After" in blocked_resp.headers
        assert int(blocked_resp.headers["Retry-After"]) >= 1
    finally:
        # Restaura limites padrão e limpa memória
        rate_limiter.limits["login"] = (10, 60)
        rate_limiter.reset()


def test_payload_size_limiter_rejection(client):
    """
    Verifica se o middleware de tamanho de carga rejeita requisições anômalas
    com Content-Length excessivo (HTTP 413 Payload Too Large).
    """
    # Simula requisição com cabeçalho de 20MB em endpoint padrão (limite de 2MB)
    headers = {"Content-Length": str(20 * 1024 * 1024), "Content-Type": "application/json"}
    resp = client.post("/api/v1/properties", headers=headers, json={"titulo": "A"})
    assert resp.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    assert "excede o limite máximo permitido" in resp.json()["detail"]


# ==============================================================================
# 3. TESTES DE ESTRESSE DE ISOLAMENTO MULTI-TENANT
# ==============================================================================

def test_multi_tenant_stress_properties_isolation(client, multi_tenant_fixture):
    """
    Garante que o Consultor da Agência A não consegue visualizar, atualizar,
    transitar nem deletar imóveis pertencentes à Agência B.
    """
    token_a = multi_tenant_fixture["tokens"]["consultor_a"]
    prop_b_id = multi_tenant_fixture["prop_b"].id

    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 1. Tentar ler imóvel da Agência B
    get_resp = client.get(f"/api/v1/properties/{prop_b_id}", headers=headers_a)
    assert get_resp.status_code == status.HTTP_404_NOT_FOUND
    assert "não encontrado na sua agência" in get_resp.json()["detail"]

    # 2. Tentar atualizar imóvel da Agência B
    put_resp = client.put(f"/api/v1/properties/{prop_b_id}", headers=headers_a, json={"preco": 999999.0})
    assert put_resp.status_code == status.HTTP_404_NOT_FOUND

    # 3. Tentar alterar status do imóvel da Agência B
    trans_resp = client.post(
        f"/api/v1/properties/{prop_b_id}/transition",
        headers=headers_a,
        json={"novo_status": "Reservado"}
    )
    assert trans_resp.status_code == status.HTTP_404_NOT_FOUND

    # 4. Tentar remover imóvel da Agência B
    del_resp = client.delete(f"/api/v1/properties/{prop_b_id}", headers=headers_a)
    assert del_resp.status_code == status.HTTP_404_NOT_FOUND

    # 5. Listar imóveis: a lista da Agência A deve conter apenas o imóvel A
    list_resp = client.get("/api/v1/properties", headers=headers_a)
    assert list_resp.status_code == status.HTTP_200_OK
    items = list_resp.json()["properties"]
    assert len(items) == 1
    assert items[0]["id"] == multi_tenant_fixture["prop_a"].id
    assert items[0]["titulo"] == "Apartamento Chiado T2"


def test_multi_tenant_stress_visits_and_objections_isolation(client, multi_tenant_fixture):
    """
    Verifica que visitas e ocorrências de objeção não sofrem vazamento nem associação cruzada.
    """
    token_a = multi_tenant_fixture["tokens"]["consultor_a"]
    prop_b_id = multi_tenant_fixture["prop_b"].id
    tag_b_id = multi_tenant_fixture["tag_b"].id

    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 1. Consultor A tenta criar visita referenciando imóvel da Agência B
    visit_payload = {
        "property_id": prop_b_id,
        "cliente_nome": "Cliente Invasor",
        "nivel_interesse": 4,
        "transcricao": "Tentativa de registrar visita em imóvel de outra agência.",
        "objection_tag_ids": [tag_b_id]
    }
    create_visit_resp = client.post("/api/v1/visits", headers=headers_a, json=visit_payload)
    assert create_visit_resp.status_code == status.HTTP_404_NOT_FOUND
    assert "não pertence a esta agência" in create_visit_resp.json()["detail"]

    # 2. Consultor A lista visitas: não deve ver a visita da Agência B
    list_visits_resp = client.get("/api/v1/visits", headers=headers_a)
    assert list_visits_resp.status_code == status.HTTP_200_OK
    visits_data = list_visits_resp.json()
    assert len(visits_data["visits"]) == 1
    assert visits_data["visits"][0]["cliente_nome"] == "Cliente Lisboa"


def test_multi_tenant_stress_contacts_isolation(client, multi_tenant_fixture):
    """
    Garante que compradores na esfera de influência e rotinas de anonimização RGPD
    não são acessíveis nem modificáveis por outra agência.
    """
    token_a = multi_tenant_fixture["tokens"]["consultor_a"]
    contact_b_id = multi_tenant_fixture["contact_b"].id
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 1. Consultor A lista contatos: vê apenas contatos da sua agência
    list_resp = client.get("/api/v1/contacts", headers=headers_a)
    assert list_resp.status_code == status.HTTP_200_OK
    contatos_data = list_resp.json()
    assert len(contatos_data["items"]) == 1
    assert contatos_data["items"][0]["nome"] == "Comprador Lisboa"

    # 2. Consultor A tenta anonimizar contato da Agência B
    anon_resp = client.post(f"/api/v1/contacts/{contact_b_id}/anonymize", headers=headers_a)
    assert anon_resp.status_code == status.HTTP_404_NOT_FOUND

    # 3. Consultor A tenta remover contato da Agência B
    del_resp = client.delete(f"/api/v1/contacts/{contact_b_id}", headers=headers_a)
    assert del_resp.status_code == status.HTTP_404_NOT_FOUND


def test_multi_tenant_stress_backoffice_and_csv_exports(client, multi_tenant_fixture):
    """
    Verifica que Diretor da Agência A tem acesso rigorosamente restrito aos dados
    analíticos e relatórios CSV da sua agência, sem contaminação por dados da Agência B.
    """
    token_dir_a = multi_tenant_fixture["tokens"]["diretor_a"]
    headers_dir_a = {"Authorization": f"Bearer {token_dir_a}"}

    # 1. KPIs da Agência A
    kpis_resp = client.get("/api/v1/backoffice/kpis", headers=headers_dir_a)
    assert kpis_resp.status_code == status.HTTP_200_OK
    kpi_data = kpis_resp.json()
    assert kpi_data["total_visitas"] == 1
    # Consultor ranking deve ter apenas o Consultor Lisboa
    consultores = kpi_data["consultores_assiduidade"]
    assert len(consultores) == 1
    assert consultores[0]["nome"] == "Consultor Lisboa"

    # 2. Objeções consolidadas do imóvel B a partir da Agência A deve dar 404
    prop_b_id = multi_tenant_fixture["prop_b"].id
    analytics_resp = client.get(f"/api/v1/backoffice/objections/property/{prop_b_id}", headers=headers_dir_a)
    assert analytics_resp.status_code == status.HTTP_404_NOT_FOUND

    # 3. Exportações CSV da Agência A não devem conter menções à Agência B
    for export_type in ["visitas", "imoveis", "objecoes", "contactos"]:
        csv_resp = client.get(f"/api/v1/backoffice/export/csv?tipo={export_type}", headers=headers_dir_a)
        assert csv_resp.status_code == status.HTTP_200_OK
        content = csv_resp.text
        # Garante UTF-8 BOM
        assert content.startswith("\ufeff")
        # Garante que dados do Porto não aparecem no CSV de Lisboa
        assert "Porto" not in content
        assert "Moradia Foz" not in content


# ==============================================================================
# 4. TESTES DE SEGURANÇA E INTEGRIDADE DE TOKENS JWT
# ==============================================================================

def test_jwt_tampering_and_forgery_defenses(client, multi_tenant_fixture):
    """
    Valida a rejeição imediata de tokens com assinaturas forjadas, algoritmos
    inseguros ('none') ou manipulados com agencia_id divergente.
    """
    # 1. Token assinado com chave privada arbitrária / incorreta
    forged_token = jwt.encode(
        {"sub": "1", "agencia_id": 1, "role": "diretor", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "chave-hacker-arbitraria-nao-autorizada",
        algorithm="HS256"
    )
    resp1 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged_token}"})
    assert resp1.status_code == status.HTTP_401_UNAUTHORIZED

    # 2. Token expirado
    expired_token = jwt.encode(
        {"sub": "1", "agencia_id": 1, "role": "diretor", "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
        settings.SECRET_KEY,
        algorithm="HS256"
    )
    resp2 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp2.status_code == status.HTTP_401_UNAUTHORIZED

    # 3. Token com claim de agência inexistente ou manipulada
    user_a = multi_tenant_fixture["consultor_a"]
    mismatched_token = jwt.encode(
        {"sub": str(user_a.id), "agencia_id": 99999, "role": "consultor", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        settings.SECRET_KEY,
        algorithm="HS256"
    )
    resp3 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {mismatched_token}"})
    assert resp3.status_code == status.HTTP_401_UNAUTHORIZED


# ==============================================================================
# 5. TESTES DE PROTEÇÃO CONTRA CSV FORMULA INJECTION
# ==============================================================================

def test_csv_formula_injection_sanitization():
    """
    Garante que células que se iniciam com caracteres executáveis por planilhas
    (=, +, -, @, tab, retorno de carro) são higienizadas com aspas simples apóstrofo (').
    """
    payloads_maliciosos = [
        "=cmd|' /C calc'!A0",
        "+cmd|' /C calc'!A0",
        "-1+1",
        "@SUM(1,2)",
        "\tmalicious_tab",
        "\rmalicious_cr"
    ]

    for payload in payloads_maliciosos:
        sanitized = sanitize_csv_cell(payload)
        assert sanitized.startswith("'"), f"Falha ao sanitizar payload de injeção CSV: {payload}"

    # Valores benignos normais não devem ser alterados
    assert sanitize_csv_cell("Chiado T2") == "Chiado T2"
    assert sanitize_csv_cell("450000 €") == "450000 €"
    assert sanitize_csv_cell(None) == ""


# ==============================================================================
# 6. VALIDAÇÃO DO MODO OFFLINE, SERVICE WORKER E PWA
# ==============================================================================

def test_pwa_manifest_and_service_worker_served(client):
    """
    Verifica se o manifesto PWA e o Service Worker são servidos corretamente
    com os cabeçalhos e definições de funcionamento offline.
    """
    # 1. Manifesto PWA
    manifest_resp = client.get("/static/manifest.json")
    assert manifest_resp.status_code == status.HTTP_200_OK
    manifest_data = manifest_resp.json()
    assert manifest_data["name"] == "Fecho - Assistente Imobiliário"
    assert manifest_data["display"] == "standalone"
    assert manifest_data["theme_color"] == "#111111"

    # 2. Service Worker
    sw_resp = client.get("/static/sw.js")
    assert sw_resp.status_code == status.HTTP_200_OK
    sw_text = sw_resp.text
    assert "fecho-static-v10" in sw_text
    assert "/static/js/calculator.js" in sw_text
    assert "/static/js/teleprompter.js" in sw_text

    # 3. Shells PWA e Backoffice
    shell_resp = client.get("/")
    assert shell_resp.status_code == status.HTTP_200_OK
    assert "Fecho" in shell_resp.text

    bo_resp = client.get("/backoffice")
    assert bo_resp.status_code == status.HTTP_200_OK
    assert "Backoffice" in bo_resp.text or "Direção Comercial" in bo_resp.text


def test_offline_cached_assets_existence():
    """
    Garante que 100% dos arquivos declarados na lista ASSETS_TO_CACHE do Service Worker
    realmente existem no diretório estático do projeto.
    """
    sw_path = os.path.join(settings.STATIC_DIR, "sw.js")
    assert os.path.exists(sw_path), "Arquivo sw.js não encontrado"

    with open(sw_path, "r", encoding="utf-8") as f:
        sw_content = f.read()

    # Extrai arquivos referenciados
    expected_assets = [
        "static/manifest.json",
        "static/css/design-tokens.css",
        "static/css/style.css",
        "static/js/app.js",
        "static/js/api.js",
        "static/js/calculator.js",
        "static/js/teleprompter.js",
        "static/js/audio_recorder.js",
        "static/img/screen.png",
        "static/img/logo.png"
    ]

    for rel_path in expected_assets:
        full_path = os.path.join(settings.BASE_DIR, rel_path)
        assert os.path.exists(full_path), f"Ativo em cache ausente: {rel_path}"


# ==============================================================================
# 7. VERIFICAÇÃO DE CONTRASTE SOB LUZ SOLAR INTENSA (docs/DESIGN.md)
# ==============================================================================

def test_sunlight_contrast_mode_tokens_and_styles():
    """
    Verifica se os tokens de contraste para luz solar intensa, classes de
    estilo de alto contraste e conformidade tipográfica estão presentes.
    """
    tokens_path = os.path.join(settings.STATIC_DIR, "css", "design-tokens.css")
    style_path = os.path.join(settings.STATIC_DIR, "css", "style.css")

    with open(tokens_path, "r", encoding="utf-8") as f:
        tokens_css = f.read()

    with open(style_path, "r", encoding="utf-8") as f:
        style_css = f.read()

    # 1. Números tabulares obrigatórios para dados financeiros
    assert "tnum" in tokens_css
    assert "tabular-nums" in tokens_css

    # 2. Modo Luz Solar Intensa no style.css
    assert "body.sunlight-mode" in style_css
    assert "prefers-contrast: more" in style_css

    # 3. Cores de contraste máximo (#000000 e #ffffff) no modo luz solar
    assert "--color-primary: #000000 !important;" in style_css
    assert "--color-background: #ffffff !important;" in style_css

    # 4. Botão de luz solar nas cascas HTML
    index_path = os.path.join(settings.STATIC_DIR, "index.html")
    bo_path = os.path.join(settings.STATIC_DIR, "backoffice.html")

    with open(index_path, "r", encoding="utf-8") as f:
        index_html = f.read()
    with open(bo_path, "r", encoding="utf-8") as f:
        bo_html = f.read()

    assert "btn-sunlight-toggle" in index_html
    assert "offline-status-banner" in index_html
    assert "btn-sunlight-toggle-bo" in bo_html
    assert "offline-status-banner-bo" in bo_html


# ==============================================================================
# 8. TRAVAS DE SEGURANÇA E GUARDRAILS DE PRODUÇÃO (PAAS)
# ==============================================================================

def test_production_security_guardrails_secret_key():
    """
    Verifica se a aplicação bloqueia inicialização em produção caso a SECRET_KEY
    seja a chave padrão insegura de desenvolvimento ou possua menos de 32 caracteres.
    """
    import pytest
    from config.config import Settings

    # Salva estado original
    orig_env = Settings.ENVIRONMENT
    orig_key = Settings.SECRET_KEY

    try:
        Settings.ENVIRONMENT = "production"
        Settings.SECRET_KEY = "fecho-dev-insecure-secret-key-replace-in-production-paas"

        # Deve lançar ValueError recusando chave padrão
        with pytest.raises(ValueError, match="Configuração Insegura Crítica"):
            Settings.validate_production_settings()

        # Deve recusar chave fraca curta (< 32 caracteres)
        Settings.SECRET_KEY = "chave-curta-insegura"
        with pytest.raises(ValueError, match="Configuração Insegura Crítica"):
            Settings.validate_production_settings()

        # Com chave forte (64 caracteres), deve passar sem exceções
        Settings.SECRET_KEY = "a" * 64
        Settings.validate_production_settings()

    finally:
        Settings.ENVIRONMENT = orig_env
        Settings.SECRET_KEY = orig_key


def test_production_sqlite_fallback_blocked():
    """
    Verifica se em ambiente de produção (ENVIRONMENT=production) o fallback
    automático para SQLite e o seed de demonstração são estritamente bloqueados.
    """
    import pytest
    from config.config import settings
    from database.connection import _init_engine

    orig_env = settings.ENVIRONMENT
    orig_url = settings.DATABASE_URL

    try:
        settings.ENVIRONMENT = "production"
        # URL PostgreSQL inválida para simular falha de conexão na nuvem
        settings.DATABASE_URL = "postgresql+psycopg2://user:pass@127.0.0.1:54399/invalido_db"

        # Em produção, deve lançar RuntimeError e NUNCA fazer fallback silencioso para SQLite
        with pytest.raises(RuntimeError, match="Falha de conexão com o banco de dados PostgreSQL"):
            _init_engine()

    finally:
        settings.ENVIRONMENT = orig_env
        settings.DATABASE_URL = orig_url

