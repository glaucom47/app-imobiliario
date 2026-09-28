"""
Entidade Contact (Esfera de Influência, Compradores e Pós-Venda).
Conforme FSD:
- Registro de compradores pós-venda vinculados à escritura.
- Base para notificação de aniversário de celebração da escritura às 09:00.
- Suporte integral ao RGPD com anonimização definitiva ('Cliente Anonimizado').
"""
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.connection import Base


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agencia_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    consultor_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="SET NULL"), nullable=True, index=True)

    nome = Column(String(255), nullable=False)
    telemovel = Column(String(50), nullable=False)
    email = Column(String(255), nullable=True)
    tipo = Column(String(50), default="comprador", nullable=False)  # 'comprador' | 'proprietario' | 'esfera'

    # Data da celebração da escritura para alerta de aniversário anual
    data_escritura = Column(Date, nullable=True, index=True)

    # Flag de conformidade com RGPD
    anonimizado = Column(Boolean, default=False, nullable=False, index=True)

    notas = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relacionamentos
    tenant = relationship("Tenant", back_populates="contacts")
    consultor = relationship("User", back_populates="contacts")
    property = relationship("Property", back_populates="contacts")

    def anonimizar_rgpd(self) -> None:
        """
        Aplica a regra de conformidade RGPD do FSD:
        Substitui dados pessoais por 'Cliente Anonimizado' mantendo integridade histórica.
        """
        self.nome = "Cliente Anonimizado"
        self.telemovel = "000000000"
        self.email = None
        self.notas = "Dados pessoais anonimizados nos termos do RGPD."
        self.anonimizado = True

    def __repr__(self) -> str:
        return f"<Contact(id={self.id}, nome='{self.nome}', tipo='{self.tipo}', data_escritura={self.data_escritura})>"
