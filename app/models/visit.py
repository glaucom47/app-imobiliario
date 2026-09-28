"""
Entidade Visit (Visitas e Notas de Voz).
Conforme FSD:
- Vinculação obrigatória ao imóvel ativo, consultor e agência.
- Gravação de áudio de até 30 segundos com transcrição e notas estruturadas.
- Nível de interesse de 1 a 5.
- Tags de objeção vinculadas para fundamentação de renegociação de preços.
"""
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.connection import Base


class Visit(Base):
    __tablename__ = "visits"
    __table_args__ = (
        CheckConstraint(
            "nivel_interesse IS NULL OR (nivel_interesse >= 1 AND nivel_interesse <= 5)",
            name="chk_visit_nivel_interesse",
        ),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agencia_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    consultor_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)

    data_visita = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    cliente_nome = Column(String(255), nullable=True)
    cliente_telefone = Column(String(50), nullable=True)

    # Dados do áudio e transcrição
    audio_duracao_segundos = Column(Integer, nullable=True)
    transcricao = Column(Text, nullable=True)
    notas_estruturadas = Column(Text, nullable=True)

    # Nível de interesse do cliente (1 a 5)
    nivel_interesse = Column(Integer, nullable=True, index=True)

    # Flag de prestação de contas ao proprietário via WhatsApp
    feedback_enviado_proprietario = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relacionamentos
    tenant = relationship("Tenant", back_populates="visits")
    property = relationship("Property", back_populates="visits")
    consultor = relationship("User", back_populates="visits")
    objections = relationship("VisitObjection", back_populates="visit", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Visit(id={self.id}, property_id={self.property_id}, nivel_interesse={self.nivel_interesse})>"
