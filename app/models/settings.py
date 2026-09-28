"""
Entidade Settings (Parametrizações Remotas da Agência).
Conforme FSD:
- Gestão remota de parâmetros financeiros padrão (spreads de referência, taxas de stress).
- Horário de notificação de aniversários (09:00).
- Isolamento estrito por agencia_id.
"""
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.connection import Base


class Settings(Base):
    __tablename__ = "agency_settings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agencia_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # Parâmetros de crédito habitação padrão para simulações
    spread_referencia = Column(Numeric(5, 2), default=0.85, nullable=False)  # ex: 0.85%
    taxa_stress = Column(Numeric(5, 2), default=1.50, nullable=False)  # ex: 1.50%
    prazo_max_financiamento_anos = Column(Integer, default=30, nullable=False)
    percentual_financiamento_max = Column(Numeric(5, 2), default=85.00, nullable=False)  # ex: 85% LTV

    # Configuração de notificação diária
    hora_notificacao_aniversario = Column(String(5), default="09:00", nullable=False)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relacionamentos
    tenant = relationship("Tenant", back_populates="settings")

    def __repr__(self) -> str:
        return f"<Settings(agencia_id={self.agencia_id}, spread={self.spread_referencia}%, hora={self.hora_notificacao_aniversario})>"
