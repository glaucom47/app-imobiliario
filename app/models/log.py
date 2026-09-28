"""
Entidade Log (Trilhas de Auditoria e Conformidade de Segurança).
Conforme AGENTS.md e FSD:
- Registro de ações críticas e conformidade.
- Proibido registrar senhas, tokens JWT ou dados sensíveis.
- Isolamento multi-tenant por agencia_id.
"""
from sqlalchemy import (
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


class Log(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agencia_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    acao = Column(String(100), nullable=False, index=True)  # ex: 'LOGIN', 'LOGOUT', 'CRIAR_IMOVEL', 'TRANSICAO_STATUS'
    entidade = Column(String(100), nullable=False)  # ex: 'property', 'user', 'contact'
    entidade_id = Column(Integer, nullable=True)
    detalhes = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relacionamentos
    tenant = relationship("Tenant", back_populates="logs")

    def __repr__(self) -> str:
        return f"<Log(id={self.id}, acao='{self.acao}', entidade='{self.entidade}', agencia_id={self.agencia_id})>"
