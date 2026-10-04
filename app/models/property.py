"""
Entidade Property (Imóvel da Carteira).
Conforme FSD:
- Ciclo de vida estrito: Ativo -> Reservado -> Vendido.
- Transição para Vendido exige: nome_comprador, telefone_comprador e data_escritura.
- Isolamento obrigatório por agencia_id.
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
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.connection import Base


class Property(Base):
    __tablename__ = "properties"
    __table_args__ = (
        CheckConstraint(
            "status IN ('Ativo', 'Reservado', 'Vendido')",
            name="chk_property_status",
        ),
        CheckConstraint(
            "regiao_fiscal IN ('continente', 'madeira', 'acores')",
            name="chk_property_regiao_fiscal",
        ),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agencia_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    consultor_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)

    titulo = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=True)
    tipologia = Column(String(20), nullable=False)  # T0, T1, T2, T3, T4, T5+, Moradia, etc.
    preco = Column(Numeric(12, 2), nullable=False, index=True)
    morada = Column(String(255), nullable=True)
    concelho = Column(String(100), nullable=True)
    distrito = Column(String(100), nullable=True)
    regiao_fiscal = Column(String(50), default="continente", nullable=False)
    area_bruta = Column(Numeric(8, 2), nullable=True)

    status = Column(String(20), default="Ativo", nullable=False, index=True)

    # Dados do proprietário (para envio de WhatsApp após visita)
    nome_proprietario = Column(String(255), nullable=False)
    telefone_proprietario = Column(String(50), nullable=False)

    # Campos obrigatórios exigidos exclusivamente na transição para 'Vendido'
    nome_comprador = Column(String(255), nullable=True)
    telefone_comprador = Column(String(50), nullable=True)
    data_escritura = Column(Date, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relacionamentos
    tenant = relationship("Tenant", back_populates="properties")
    consultor = relationship("User", back_populates="properties")
    visits = relationship("Visit", back_populates="property", cascade="all, delete-orphan")
    visit_objections = relationship("VisitObjection", back_populates="property", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="property")
    pipeline_deals = relationship("PipelineDeal", back_populates="property")

    def __repr__(self) -> str:
        return f"<Property(id={self.id}, titulo='{self.titulo}', status='{self.status}', preco={self.preco})>"
