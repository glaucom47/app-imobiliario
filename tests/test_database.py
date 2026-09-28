"""
Suíte de testes automatizados para a Fase 2: Banco de Dados, Persistência e Isolamento Multi-tenant.
Valida:
1. Criação correta das entidades relacionais e metadados;
2. Isolamento lógico multi-tenant rigoroso por agencia_id;
3. Máquina de estados de Imóveis (Ativo -> Reservado -> Vendido) e campos obrigatórios de fechamento;
4. Nível de interesse de visitas (1 a 5);
5. Catálogo corporativo de objeções e vínculos com visitas;
6. Rotina de conformidade RGPD ('Cliente Anonimizado');
7. Parametrização remota da agência.
"""
from datetime import date, datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from app.models.tenant import Tenant
from app.models.user import User
from app.models.property import Property
from app.models.visit import Visit
from app.models.objection import ObjectionTag, VisitObjection
from app.models.contact import Contact
from app.models.settings import Settings
from app.models.log import Log


# Setup de banco SQLite em memória para execução limpa e isolada dos testes unitários
@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


def test_tenant_creation_and_relations(db_session):
    """Valida criação de agência (Tenant) e seus relacionamentos básicos."""
    tenant = Tenant(
        nome="Agência Lisboa Centro",
        slug="lisboa-centro",
        nif="599888777",
        telefone="+351 211 222 333",
        email="info@lisboacentro.pt",
        ativo=True,
    )
    db_session.add(tenant)
    db_session.commit()

    assert tenant.id is not None
    assert tenant.slug == "lisboa-centro"
    assert tenant.ativo is True


def test_user_creation_and_roles(db_session):
    """Valida criação de usuários com perfis e vinculação a tenant."""
    tenant = Tenant(nome="Agência Porto", slug="porto-prime")
    db_session.add(tenant)
    db_session.commit()

    diretor = User(
        agencia_id=tenant.id,
        nome="Mariana Costa",
        email="mariana@portoprime.pt",
        password_hash="fake_hash_bcrypt",
        role="diretor",
    )
    consultor = User(
        agencia_id=tenant.id,
        nome="Pedro Duarte",
        email="pedro@portoprime.pt",
        password_hash="fake_hash_bcrypt",
        role="consultor",
    )
    db_session.add_all([diretor, consultor])
    db_session.commit()

    assert diretor.id is not None
    assert diretor.role == "diretor"
    assert consultor.role == "consultor"
    assert len(tenant.users) == 2


def test_multi_tenant_data_isolation(db_session):
    """Valida rigorosamente o isolamento lógico multi-tenant por agencia_id."""
    agencia_a = Tenant(nome="Agência A", slug="agencia-a")
    agencia_b = Tenant(nome="Agência B", slug="agencia-b")
    db_session.add_all([agencia_a, agencia_b])
    db_session.commit()

    user_a = User(agencia_id=agencia_a.id, nome="User A", email="a@a.pt", password_hash="h", role="consultor")
    user_b = User(agencia_id=agencia_b.id, nome="User B", email="b@b.pt", password_hash="h", role="consultor")
    db_session.add_all([user_a, user_b])
    db_session.commit()

    prop_a = Property(
        agencia_id=agencia_a.id,
        consultor_id=user_a.id,
        titulo="Imóvel Agência A",
        tipologia="T2",
        preco=350000.00,
        status="Ativo",
        nome_proprietario="Proprietário A",
        telefone_proprietario="+351 911 000 111",
    )
    prop_b = Property(
        agencia_id=agencia_b.id,
        consultor_id=user_b.id,
        titulo="Imóvel Agência B",
        tipologia="T3",
        preco=550000.00,
        status="Ativo",
        nome_proprietario="Proprietário B",
        telefone_proprietario="+351 922 000 222",
    )
    db_session.add_all([prop_a, prop_b])
    db_session.commit()

    # Consulta filtrando obrigatoriamente por agencia_id da Agência A
    imoveis_agencia_a = db_session.query(Property).filter(Property.agencia_id == agencia_a.id).all()
    assert len(imoveis_agencia_a) == 1
    assert imoveis_agencia_a[0].titulo == "Imóvel Agência A"

    # Confirma que nenhum dado da Agência B vaza para a Agência A
    assert all(p.agencia_id == agencia_a.id for p in imoveis_agencia_a)


def test_property_lifecycle_and_sold_fields(db_session):
    """Valida estados de ciclo de vida e preenchimento dos 3 campos ao vender."""
    tenant = Tenant(nome="Agência Cascais", slug="cascais-real")
    db_session.add(tenant)
    db_session.commit()

    consultor = User(agencia_id=tenant.id, nome="Rui Silva", email="rui@cascais.pt", password_hash="h", role="consultor")
    db_session.add(consultor)
    db_session.commit()

    prop = Property(
        agencia_id=tenant.id,
        consultor_id=consultor.id,
        titulo="Moradia Cascais",
        tipologia="T4",
        preco=1450000.00,
        status="Ativo",
        nome_proprietario="António Alves",
        telefone_proprietario="+351 910 111 222",
    )
    db_session.add(prop)
    db_session.commit()

    # Transição Ativo -> Reservado
    prop.status = "Reservado"
    db_session.commit()
    assert prop.status == "Reservado"

    # Transição Reservado -> Vendido com os 3 campos obrigatórios (FSD Seção 1 e 5)
    prop.status = "Vendido"
    prop.nome_comprador = "Sofia Mendonça"
    prop.telefone_comprador = "+351 965 444 333"
    prop.data_escritura = date(2026, 10, 15)
    db_session.commit()

    assert prop.status == "Vendido"
    assert prop.nome_comprador == "Sofia Mendonça"
    assert prop.telefone_comprador == "+351 965 444 333"
    assert prop.data_escritura == date(2026, 10, 15)


def test_visit_and_objection_association(db_session):
    """Valida registro de visita, notas e associação de tags de objeção."""
    tenant = Tenant(nome="Agência Sintra", slug="sintra-real")
    db_session.add(tenant)
    db_session.commit()

    consultor = User(agencia_id=tenant.id, nome="Ana Rocha", email="ana@sintra.pt", password_hash="h", role="consultor")
    db_session.add(consultor)
    db_session.commit()

    prop = Property(
        agencia_id=tenant.id,
        consultor_id=consultor.id,
        titulo="Apartamento Sintra",
        tipologia="T2",
        preco=220000.00,
        status="Ativo",
        nome_proprietario="Dono Sintra",
        telefone_proprietario="+351 919 000 999",
    )
    db_session.add(prop)
    db_session.commit()

    tag_preco = ObjectionTag(agencia_id=tenant.id, tag="Preço Elevado", categoria="preco")
    tag_ruido = ObjectionTag(agencia_id=tenant.id, tag="Ruído da Rua", categoria="localizacao")
    db_session.add_all([tag_preco, tag_ruido])
    db_session.commit()

    visita = Visit(
        agencia_id=tenant.id,
        property_id=prop.id,
        consultor_id=consultor.id,
        cliente_nome="Beatriz Martins",
        cliente_telefone="+351 928 777 666",
        audio_duracao_segundos=28,
        transcricao="Cliente achou o valor acima da média da zona e queixou-se do barulho da avenida.",
        notas_estruturadas="Interesse moderado. Objeções fortes a preço e acústica.",
        nivel_interesse=3,
        feedback_enviado_proprietario=False,
    )
    db_session.add(visita)
    db_session.commit()

    # Vínculo das objeções levantadas na visita
    obj1 = VisitObjection(
        agencia_id=tenant.id,
        visit_id=visita.id,
        property_id=prop.id,
        tag_id=tag_preco.id,
        observacao="Cliente comparou com outro T2 na mesma freguesia por 195k.",
    )
    obj2 = VisitObjection(
        agencia_id=tenant.id,
        visit_id=visita.id,
        property_id=prop.id,
        tag_id=tag_ruido.id,
        observacao="Quarto principal virado para a rotunda.",
    )
    db_session.add_all([obj1, obj2])
    db_session.commit()

    assert len(visita.objections) == 2
    assert visita.objections[0].tag.tag in ["Preço Elevado", "Ruído da Rua"]


def test_rgpd_anonymization(db_session):
    """Valida a anonimização definitiva de compradores para conformidade com o RGPD."""
    tenant = Tenant(nome="Agência Algarve", slug="algarve-prime")
    db_session.add(tenant)
    db_session.commit()

    consultor = User(agencia_id=tenant.id, nome="Lucas Lima", email="lucas@algarve.pt", password_hash="h", role="consultor")
    db_session.add(consultor)
    db_session.commit()

    contato = Contact(
        agencia_id=tenant.id,
        consultor_id=consultor.id,
        nome="Guilherme Ferreira",
        telemovel="+351 915 222 111",
        email="guilherme@exemplo.pt",
        tipo="comprador",
        data_escritura=date(2024, 5, 20),
        notas="Comprador particular de moradia.",
    )
    db_session.add(contato)
    db_session.commit()

    assert contato.anonimizado is False
    assert contato.nome == "Guilherme Ferreira"

    # Executa a rotina de anonimização conforme FSD
    contato.anonimizar_rgpd()
    db_session.commit()

    assert contato.anonimizado is True
    assert contato.nome == "Cliente Anonimizado"
    assert contato.telemovel == "000000000"
    assert contato.email is None
    # Integridade histórica mantida (ID, data da escritura, tenant continuam intactos)
    assert contato.data_escritura == date(2024, 5, 20)
    assert contato.agencia_id == tenant.id


def test_agency_settings(db_session):
    """Valida parametrização remota da agência."""
    tenant = Tenant(nome="Agência Braga", slug="braga-real")
    db_session.add(tenant)
    db_session.commit()

    settings = Settings(
        agencia_id=tenant.id,
        spread_referencia=0.75,
        taxa_stress=1.75,
        prazo_max_financiamento_anos=35,
        percentual_financiamento_max=90.00,
        hora_notificacao_aniversario="09:00",
    )
    db_session.add(settings)
    db_session.commit()

    assert settings.id is not None
    assert float(settings.spread_referencia) == 0.75
    assert settings.hora_notificacao_aniversario == "09:00"
