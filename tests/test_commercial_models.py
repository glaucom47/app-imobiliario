"""
Suíte de testes automatizados para os Modelos da Direção Comercial (FSD Seção 8).
Valida:
1. Criação e integridade de Goal (metas de faturação e métricas comerciais);
2. Validação de PipelineDeal (oportunidades em carteira, probabilidade, fase, comissão);
3. Validação de WeeklyMeeting (reunião semanal com snapshot congelado e notas qualitativas);
4. Validação de MeetingCommitment (compromissos semanais, status e percentual de cumprimento);
5. Isolamento multi-tenant e integridade relacional com Tenant, User e Property.
"""
from datetime import date, datetime, timezone
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from app.models.tenant import Tenant
from app.models.user import User
from app.models.property import Property
from app.models.commercial import (
    Goal,
    PipelineDeal,
    WeeklyMeeting,
    MeetingCommitment,
)


@pytest.fixture(scope="function")
def db_session():
    """Setup de banco SQLite em memória para testes limpos e isolados."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_tenant(db_session):
    tenant = Tenant(
        nome="Agência Fecho Porto",
        slug="fecho-porto",
        nif="500111222",
        telefone="+351 220 111 222",
        email="porto@fecho.pt",
        ativo=True,
    )
    db_session.add(tenant)
    db_session.commit()
    return tenant


@pytest.fixture
def sample_users(db_session, sample_tenant):
    diretor = User(
        agencia_id=sample_tenant.id,
        nome="Diretora Ana Silva",
        email="ana.silva@fecho.pt",
        password_hash="hash_diretora",
        role="diretor",
        ativo=True,
    )
    consultor = User(
        agencia_id=sample_tenant.id,
        nome="Consultor Carlos Miguel",
        email="carlos.miguel@fecho.pt",
        password_hash="hash_consultor",
        role="consultor",
        ativo=True,
    )
    db_session.add_all([diretor, consultor])
    db_session.commit()
    return diretor, consultor


@pytest.fixture
def sample_property(db_session, sample_tenant, sample_users):
    _, consultor = sample_users
    prop = Property(
        agencia_id=sample_tenant.id,
        consultor_id=consultor.id,
        titulo="Apartamento T3 Foz do Douro",
        tipologia="T3",
        preco=Decimal("450000.00"),
        regiao_fiscal="continente",
        nome_proprietario="Sr. Oliveira",
        telefone_proprietario="+351 912 345 678",
        status="Ativo",
    )
    db_session.add(prop)
    db_session.commit()
    return prop


def test_goal_creation_and_integrity(db_session, sample_tenant, sample_users):
    """Valida cadastro de Goal com todas as metas comerciais e faturação."""
    _, consultor = sample_users
    goal = Goal(
        agencia_id=sample_tenant.id,
        consultor_id=consultor.id,
        ano=2026,
        mes=10,
        meta_faturacao=Decimal("15000.00"),
        meta_contactos=50,
        meta_reunioes=20,
        meta_angariacoes=4,
        meta_exclusivos=3,
        meta_visitas=25,
        meta_propostas=6,
        meta_cpcv=2,
        meta_escrituras=2,
    )
    db_session.add(goal)
    db_session.commit()

    assert goal.id is not None
    assert goal.meta_faturacao == Decimal("15000.00")
    assert goal.consultor.nome == "Consultor Carlos Miguel"
    assert goal.tenant.slug == "fecho-porto"
    assert goal in consultor.goals
    assert goal in sample_tenant.goals


def test_goal_unique_constraint_per_month(db_session, sample_tenant, sample_users):
    """Garante que não é possível criar duas metas para o mesmo consultor no mesmo mês e ano."""
    _, consultor = sample_users
    goal1 = Goal(
        agencia_id=sample_tenant.id,
        consultor_id=consultor.id,
        ano=2026,
        mes=10,
        meta_faturacao=Decimal("10000.00"),
    )
    db_session.add(goal1)
    db_session.commit()

    goal2 = Goal(
        agencia_id=sample_tenant.id,
        consultor_id=consultor.id,
        ano=2026,
        mes=10,
        meta_faturacao=Decimal("12000.00"),
    )
    db_session.add(goal2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_pipeline_deal_creation_and_relations(db_session, sample_tenant, sample_users, sample_property):
    """Valida cadastro de PipelineDeal com vínculo a consultor, agência e imóvel opcional."""
    _, consultor = sample_users
    deal = PipelineDeal(
        agencia_id=sample_tenant.id,
        consultor_id=consultor.id,
        property_id=sample_property.id,
        cliente_nome="Dr. Manuel Antunes",
        cliente_telefone="+351 933 444 555",
        tipo_negocio="Venda",
        valor_imovel=Decimal("450000.00"),
        comissao_estimada=Decimal("22500.00"),
        fase="Negociacao",
        probabilidade=75,
        data_prevista_fecho=date(2026, 11, 30),
        proxima_acao="Enviar minuta de CPCV",
        data_proxima_acao=date(2026, 10, 10),
        ativo=True,
    )
    db_session.add(deal)
    db_session.commit()

    assert deal.id is not None
    assert deal.fase == "Negociacao"
    assert deal.probabilidade == 75
    assert deal.property.titulo == "Apartamento T3 Foz do Douro"
    assert deal.consultor.id == consultor.id
    assert deal in sample_property.pipeline_deals
    assert deal in consultor.pipeline_deals
    assert deal in sample_tenant.pipeline_deals


def test_pipeline_deal_without_property(db_session, sample_tenant, sample_users):
    """Valida oportunidade de compra ou angariação onde property_id é opcional/nulo."""
    _, consultor = sample_users
    deal = PipelineDeal(
        agencia_id=sample_tenant.id,
        consultor_id=consultor.id,
        property_id=None,
        cliente_nome="Comprador Investidor",
        cliente_telefone="+351 911 000 111",
        tipo_negocio="Compra",
        valor_imovel=Decimal("300000.00"),
        comissao_estimada=Decimal("15000.00"),
        fase="Qualificacao",
        probabilidade=40,
        ativo=True,
    )
    db_session.add(deal)
    db_session.commit()

    assert deal.id is not None
    assert deal.property is None
    assert deal.property_id is None


def test_weekly_meeting_and_commitments(db_session, sample_tenant, sample_users):
    """Valida reunião semanal individual com snapshot congelado e compromissos vinculados."""
    diretor, consultor = sample_users
    meeting = WeeklyMeeting(
        agencia_id=sample_tenant.id,
        diretor_id=diretor.id,
        consultor_id=consultor.id,
        data_reuniao=datetime(2026, 10, 4, 10, 0, tzinfo=timezone.utc),
        semana_ano=40,
        ano=2026,
        contactos_realizados=28,
        reunioes_realizadas=9,
        angariacoes_realizadas=2,
        visitas_realizadas=12,
        propostas_realizadas=3,
        cpcv_realizados=1,
        faturacao_realizada=Decimal("8500.00"),
        dificuldade_principal="Objeções a preço nos imóveis da Boavista",
        negocio_prioritario="Fecho da venda T3 Foz do Douro",
        diagnostico_diretor="Excelente taxa de visitas, foco agora no fecho de propostas",
        estrategia_definida="Realizar 2 estudos de mercado ACM atualizados para ajuste de preço",
        apoio_direcao_necessario="Participação na reunião com o proprietário do T3",
    )
    db_session.add(meeting)
    db_session.commit()

    assert meeting.id is not None
    assert meeting.diretor.nome == "Diretora Ana Silva"
    assert meeting.consultor.nome == "Consultor Carlos Miguel"
    assert meeting in diretor.directed_meetings
    assert meeting in consultor.attended_meetings
    assert meeting in sample_tenant.weekly_meetings

    # Cadastro de compromisso semanal vinculado
    commitment1 = MeetingCommitment(
        meeting_id=meeting.id,
        consultor_id=consultor.id,
        descricao_compromisso="Ligar a 5 proprietários com relatórios ACM",
        meta_quantitativa="5 contactos",
        prazo_data=date(2026, 10, 9),
        status="Pendente",
        percentual_cumprimento=0,
    )
    commitment2 = MeetingCommitment(
        meeting_id=meeting.id,
        consultor_id=consultor.id,
        descricao_compromisso="Apresentar proposta formal no imóvel T3 Foz",
        meta_quantitativa="1 proposta",
        prazo_data=date(2026, 10, 8),
        status="Pendente",
        percentual_cumprimento=0,
    )
    db_session.add_all([commitment1, commitment2])
    db_session.commit()

    assert len(meeting.commitments) == 2
    assert commitment1 in consultor.meeting_commitments
    assert commitment1.meeting.id == meeting.id


def test_meeting_commitment_cascade_deletion(db_session, sample_tenant, sample_users):
    """Ao apagar uma reunião semanal, os compromissos filhos devem ser removidos em cascata."""
    diretor, consultor = sample_users
    meeting = WeeklyMeeting(
        agencia_id=sample_tenant.id,
        diretor_id=diretor.id,
        consultor_id=consultor.id,
        data_reuniao=datetime(2026, 10, 4, 11, 0, tzinfo=timezone.utc),
        semana_ano=40,
        ano=2026,
    )
    db_session.add(meeting)
    db_session.commit()

    commitment = MeetingCommitment(
        meeting_id=meeting.id,
        consultor_id=consultor.id,
        descricao_compromisso="Compromisso de teste cascata",
        prazo_data=date(2026, 10, 11),
        status="Pendente",
    )
    db_session.add(commitment)
    db_session.commit()

    comm_id = commitment.id
    db_session.delete(meeting)
    db_session.commit()

    assert db_session.get(MeetingCommitment, comm_id) is None


def test_multitenant_commercial_isolation(db_session):
    """Garante isolamento absoluto por agencia_id entre agências diferentes."""
    tenant_a = Tenant(nome="Agência Lisboa", slug="ag-lisboa", ativo=True)
    tenant_b = Tenant(nome="Agência Porto", slug="ag-porto", ativo=True)
    db_session.add_all([tenant_a, tenant_b])
    db_session.commit()

    user_a = User(agencia_id=tenant_a.id, nome="Consultor A", email="a@ag.pt", password_hash="h", role="consultor")
    user_b = User(agencia_id=tenant_b.id, nome="Consultor B", email="b@ag.pt", password_hash="h", role="consultor")
    db_session.add_all([user_a, user_b])
    db_session.commit()

    goal_a = Goal(agencia_id=tenant_a.id, consultor_id=user_a.id, ano=2026, mes=10, meta_faturacao=Decimal("5000.00"))
    goal_b = Goal(agencia_id=tenant_b.id, consultor_id=user_b.id, ano=2026, mes=10, meta_faturacao=Decimal("8000.00"))
    db_session.add_all([goal_a, goal_b])
    db_session.commit()

    # Consulta filtrando por agência A
    goals_a = db_session.query(Goal).filter(Goal.agencia_id == tenant_a.id).all()
    assert len(goals_a) == 1
    assert goals_a[0].consultor_id == user_a.id
    assert goals_a[0].meta_faturacao == Decimal("5000.00")

    # Agência B não vê os dados da agência A
    goals_b = db_session.query(Goal).filter(Goal.agencia_id == tenant_b.id).all()
    assert len(goals_b) == 1
    assert goals_b[0].consultor_id == user_b.id
