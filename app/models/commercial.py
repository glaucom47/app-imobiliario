"""
Módulo de modelos da Direção Comercial & Gestão Ativa de Equipa (Fase 1 - MVP).
Conforme FSD Seção 8:
- Goal: Metas Comerciais Individuais mensais
- PipelineDeal: Oportunidades em Carteira e Negociação com probabilidade e comissão
- WeeklyMeeting: Sessões de Acompanhamento Semanal com snapshot congelado e notas qualitativas
- MeetingCommitment: Compromissos Semanais acordados entre Diretor e Consultor
"""
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.connection import Base


class StoreGoal(Base):
    """
    Metas Comerciais Globais da Loja/Agência para o mês/ano.
    Isolamento obrigatório por agencia_id.
    Permite ao Diretor definir o teto orçamentário mensal e orientar o desdobramento
    entre os consultores da equipa.
    """
    __tablename__ = "store_goals"
    __table_args__ = (
        UniqueConstraint(
            "agencia_id", "ano", "mes",
            name="uq_store_goals_agencia_ano_mes",
        ),
        CheckConstraint("mes >= 1 AND mes <= 12", name="chk_store_goal_mes"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agencia_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    ano = Column(Integer, nullable=False, index=True)
    mes = Column(Integer, nullable=False, index=True)

    meta_faturacao = Column(Numeric(12, 2), nullable=False, default=50000.0)
    meta_angariacoes = Column(Integer, nullable=False, default=10)
    meta_visitas = Column(Integer, nullable=False, default=30)
    meta_propostas = Column(Integer, nullable=False, default=10)
    meta_cpcv = Column(Integer, nullable=False, default=5)
    meta_escrituras = Column(Integer, nullable=False, default=5)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relacionamentos
    tenant = relationship("Tenant", back_populates="store_goals")

    def __repr__(self) -> str:
        return f"<StoreGoal(id={self.id}, agencia_id={self.agencia_id}, ano={self.ano}, mes={self.mes}, meta_faturacao={self.meta_faturacao})>"


class Goal(Base):
    """
    Metas Comerciais Individuais de consultores para o mês/ano.
    Isolamento obrigatório por agencia_id.
    """
    __tablename__ = "goals"
    __table_args__ = (
        UniqueConstraint(
            "agencia_id", "consultor_id", "ano", "mes",
            name="uq_goals_agencia_consultor_ano_mes",
        ),
        CheckConstraint("mes >= 1 AND mes <= 12", name="chk_goal_mes"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agencia_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    consultor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ano = Column(Integer, nullable=False, index=True)
    mes = Column(Integer, nullable=False, index=True)

    meta_faturacao = Column(Numeric(12, 2), nullable=False, default=0.0)
    meta_contactos = Column(Integer, nullable=False, default=0)
    meta_reunioes = Column(Integer, nullable=False, default=0)
    meta_angariacoes = Column(Integer, nullable=False, default=0)
    meta_exclusivos = Column(Integer, nullable=False, default=0)
    meta_visitas = Column(Integer, nullable=False, default=0)
    meta_propostas = Column(Integer, nullable=False, default=0)
    meta_cpcv = Column(Integer, nullable=False, default=0)
    meta_escrituras = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relacionamentos
    tenant = relationship("Tenant", back_populates="goals")
    consultor = relationship("User", back_populates="goals")

    def __repr__(self) -> str:
        return f"<Goal(id={self.id}, consultor_id={self.consultor_id}, ano={self.ano}, mes={self.mes}, meta_faturacao={self.meta_faturacao})>"


class PipelineDeal(Base):
    """
    Oportunidades no funil comercial da agência e do consultor.
    Isolamento obrigatório por agencia_id.
    """
    __tablename__ = "pipeline_deals"
    __table_args__ = (
        CheckConstraint(
            "tipo_negocio IN ('Venda', 'Angariação', 'Compra')",
            name="chk_deal_tipo_negocio",
        ),
        CheckConstraint(
            "fase IN ('Lead', 'Qualificacao', 'Angariacao', 'Visita', 'Proposta', 'Negociacao', 'CPCV', 'Escritura', 'Ganho', 'Perdido')",
            name="chk_deal_fase",
        ),
        CheckConstraint(
            "probabilidade >= 0 AND probabilidade <= 100",
            name="chk_deal_probabilidade",
        ),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agencia_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    consultor_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="SET NULL"), nullable=True, index=True)

    cliente_nome = Column(String(255), nullable=False)
    cliente_telefone = Column(String(50), nullable=False)
    tipo_negocio = Column(String(50), nullable=False)  # Venda, Angariação, Compra
    valor_imovel = Column(Numeric(12, 2), nullable=False, default=0.0)
    comissao_estimada = Column(Numeric(12, 2), nullable=False, default=0.0)
    fase = Column(
        String(50),
        nullable=False,
        default="Lead",
        index=True,
    )  # Lead, Qualificacao, Angariacao, Visita, Proposta, Negociacao, CPCV, Escritura, Ganho, Perdido
    probabilidade = Column(Integer, nullable=False, default=10)  # 0 a 100%
    data_prevista_fecho = Column(Date, nullable=True)
    proxima_acao = Column(String(255), nullable=True)
    data_proxima_acao = Column(Date, nullable=True)
    ativo = Column(Boolean, default=True, nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relacionamentos
    tenant = relationship("Tenant", back_populates="pipeline_deals")
    consultor = relationship("User", back_populates="pipeline_deals")
    property = relationship("Property", back_populates="pipeline_deals")

    def __repr__(self) -> str:
        return f"<PipelineDeal(id={self.id}, cliente='{self.cliente_nome}', fase='{self.fase}', valor={self.valor_imovel})>"


class WeeklyMeeting(Base):
    """
    Sessões de acompanhamento semanal individual do Diretor com o Consultor.
    Congela métricas da semana e regista avaliação humana e apoios necessários.
    """
    __tablename__ = "weekly_meetings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agencia_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    diretor_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    consultor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    data_reuniao = Column(DateTime(timezone=True), nullable=False, index=True)
    semana_ano = Column(Integer, nullable=False, index=True)
    ano = Column(Integer, nullable=False, index=True)

    # Snapshot quantitativo congelado da semana
    contactos_realizados = Column(Integer, nullable=False, default=0)
    reunioes_realizadas = Column(Integer, nullable=False, default=0)
    angariacoes_realizadas = Column(Integer, nullable=False, default=0)
    visitas_realizadas = Column(Integer, nullable=False, default=0)
    propostas_realizadas = Column(Integer, nullable=False, default=0)
    cpcv_realizados = Column(Integer, nullable=False, default=0)
    faturacao_realizada = Column(Numeric(12, 2), nullable=False, default=0.0)

    # Campos qualitativos humanos
    dificuldade_principal = Column(Text, nullable=True)
    negocio_prioritario = Column(Text, nullable=True)
    diagnostico_diretor = Column(Text, nullable=True)
    estrategia_definida = Column(Text, nullable=True)
    apoio_direcao_necessario = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relacionamentos
    tenant = relationship("Tenant", back_populates="weekly_meetings")
    diretor = relationship("User", foreign_keys=[diretor_id], back_populates="directed_meetings")
    consultor = relationship("User", foreign_keys=[consultor_id], back_populates="attended_meetings")
    commitments = relationship("MeetingCommitment", back_populates="meeting", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<WeeklyMeeting(id={self.id}, consultor_id={self.consultor_id}, semana={self.semana_ano}/{self.ano})>"


class MeetingCommitment(Base):
    """
    Compromissos acordados na sessão semanal entre o Diretor e o Consultor.
    """
    __tablename__ = "meeting_commitments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('Pendente', 'Cumprido', 'Parcial', 'NaoCumprido')",
            name="chk_commitment_status",
        ),
        CheckConstraint(
            "percentual_cumprimento >= 0 AND percentual_cumprimento <= 100",
            name="chk_commitment_percentual",
        ),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    meeting_id = Column(Integer, ForeignKey("weekly_meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    consultor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    descricao_compromisso = Column(String(255), nullable=False)
    meta_quantitativa = Column(String(100), nullable=True)
    prazo_data = Column(Date, nullable=False)
    status = Column(String(50), default="Pendente", nullable=False)  # Pendente, Cumprido, Parcial, NaoCumprido
    percentual_cumprimento = Column(Integer, default=0, nullable=False)  # 0 a 100%

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relacionamentos
    meeting = relationship("WeeklyMeeting", back_populates="commitments")
    consultor = relationship("User", back_populates="meeting_commitments")

    def __repr__(self) -> str:
        return f"<MeetingCommitment(id={self.id}, consultor_id={self.consultor_id}, status='{self.status}')>"
