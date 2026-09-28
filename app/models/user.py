"""
Entidade User (Usuário da Agência) com controle de perfis (diretor / consultor).
Conforme FSD: isolamento por agencia_id e credenciais seguras.
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.connection import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agencia_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    nome = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="consultor")  # 'diretor' | 'consultor'
    telemovel = Column(String(50), nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relacionamentos
    tenant = relationship("Tenant", back_populates="users")
    properties = relationship("Property", back_populates="consultor")
    visits = relationship("Visit", back_populates="consultor")
    contacts = relationship("Contact", back_populates="consultor")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}', agencia_id={self.agencia_id})>"
