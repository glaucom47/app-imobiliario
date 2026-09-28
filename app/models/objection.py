"""
Entidades de Objeções (Catálogo Padronizado da Agência e Vínculos de Visita).
Conforme FSD:
- Catálogo corporativo de tags padronizadas gerenciado pela direção.
- Vínculo a visitas para alimentar o gráfico consolidado de objeções por imóvel no backoffice.
"""
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.connection import Base


class ObjectionTag(Base):
    """
    Catálogo corporativo de tags de objeção padronizadas por agência.
    Ex: 'Preço Elevado', 'Ruído da Rua', 'Área Inferior ao Esperado', etc.
    """
    __tablename__ = "objection_tags"
    __table_args__ = (
        UniqueConstraint("agencia_id", "tag", name="uq_agencia_objection_tag"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agencia_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    tag = Column(String(100), nullable=False)
    categoria = Column(String(50), default="geral", nullable=False)  # 'preco', 'localizacao', 'estado', 'dimensao', etc.
    ativo = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relacionamentos
    tenant = relationship("Tenant", back_populates="objection_tags")
    visit_objections = relationship("VisitObjection", back_populates="tag", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<ObjectionTag(id={self.id}, tag='{self.tag}', agencia_id={self.agencia_id})>"


class VisitObjection(Base):
    """
    Registro das objeções levantadas durante uma visita específica a um imóvel.
    """
    __tablename__ = "visit_objections"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agencia_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    visit_id = Column(Integer, ForeignKey("visits.id", ondelete="CASCADE"), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    tag_id = Column(Integer, ForeignKey("objection_tags.id", ondelete="RESTRICT"), nullable=False, index=True)

    observacao = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relacionamentos
    tenant = relationship("Tenant", back_populates="visit_objections")
    visit = relationship("Visit", back_populates="objections")
    property = relationship("Property", back_populates="visit_objections")
    tag = relationship("ObjectionTag", back_populates="visit_objections")

    def __repr__(self) -> str:
        return f"<VisitObjection(id={self.id}, visit_id={self.visit_id}, tag_id={self.tag_id})>"
