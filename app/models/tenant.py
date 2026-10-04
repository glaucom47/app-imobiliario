"""
Entidade Tenant (Agência Imobiliária) para suporte ao isolamento lógico multi-tenant.
Conforme FSD: Todas as tabelas de negócio e consultas devem conter e filtrar obrigatoriamente por agencia_id.
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.connection import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    nif = Column(String(50), nullable=True, index=True)
    telefone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    morada = Column(Text, nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relacionamentos
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    properties = relationship("Property", back_populates="tenant", cascade="all, delete-orphan")
    visits = relationship("Visit", back_populates="tenant", cascade="all, delete-orphan")
    objection_tags = relationship("ObjectionTag", back_populates="tenant", cascade="all, delete-orphan")
    visit_objections = relationship("VisitObjection", back_populates="tenant", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="tenant", cascade="all, delete-orphan")
    settings = relationship("Settings", back_populates="tenant", uselist=False, cascade="all, delete-orphan")
    logs = relationship("Log", back_populates="tenant", cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="tenant", cascade="all, delete-orphan")
    pipeline_deals = relationship("PipelineDeal", back_populates="tenant", cascade="all, delete-orphan")
    weekly_meetings = relationship("WeeklyMeeting", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, nome='{self.nome}', slug='{self.slug}')>"
