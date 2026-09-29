"""
Entidades de Captação e Angariação de Imóveis (Fontes Abertas & FSBO).
Conforme FSD (Seção 6):
- Monitorização de hasta pública (e-leiloes.pt) e classificados abertos (OLX Particulares);
- Ciclo de vida estrito da lead: Novo -> Em Prospeccao -> Convertido | Descartado | Oposicao_RGPD;
- Conversão em 1 clique gerando imóvel da carteira ('Property') com status 'Ativo';
- Governança RGPD com bloqueio por telefone (LeadBlacklist) e oposição de tratamento.
- Isolamento obrigatório por agencia_id.
"""
from sqlalchemy import (
    CheckConstraint,
    Column,
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


class LeadAngariacao(Base):
    __tablename__ = "leads_angariacao"
    __table_args__ = (
        CheckConstraint(
            "status IN ('Novo', 'Em Prospeccao', 'Convertido', 'Descartado', 'Oposicao_RGPD')",
            name="chk_lead_status",
        ),
        UniqueConstraint("agencia_id", "fonte", "referencia_externa", name="uq_lead_agencia_fonte_ref"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agencia_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    consultor_atribuido_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Identificação de Origem
    fonte = Column(String(50), nullable=False, index=True)  # 'e-leiloes', 'olx', 'manual'
    referencia_externa = Column(String(100), nullable=False, index=True)
    url_origem = Column(Text, nullable=False)

    # Atributos do Imóvel Captado
    titulo = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=True)
    tipologia = Column(String(20), nullable=False)  # T0, T1, T2, T3, T4, Moradia, etc.
    preco_solicitado = Column(Numeric(12, 2), nullable=False, index=True)
    valor_minimo_abertura = Column(Numeric(12, 2), nullable=True)  # Específico para e-leilões
    distrito = Column(String(100), nullable=True)
    concelho = Column(String(100), nullable=True, index=True)
    freguesia = Column(String(100), nullable=True)
    morada_aproximada = Column(String(255), nullable=True)

    # Dados de Contato e Prospecção (RGPD)
    nome_contacto = Column(String(255), nullable=True)
    telefone_contacto = Column(String(50), nullable=True, index=True)
    tipo_anunciante = Column(String(50), default="Particular", nullable=False)  # 'Particular' | 'Agente de Execução'

    # Ciclo de Vida da Lead
    status = Column(String(30), default="Novo", nullable=False, index=True)
    imovel_convertido_id = Column(Integer, ForeignKey("properties.id", ondelete="SET NULL"), nullable=True, index=True)
    data_limite_leilao = Column(DateTime, nullable=True)  # Para e-leilões
    notas_prospeccao = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relacionamentos
    tenant = relationship("Tenant", foreign_keys=[agencia_id])
    consultor_atribuido = relationship("User", foreign_keys=[consultor_atribuido_id])
    imovel_convertido = relationship("Property", foreign_keys=[imovel_convertido_id])


class LeadBlacklist(Base):
    __tablename__ = "leads_blacklist_rgpd"
    __table_args__ = (
        UniqueConstraint("agencia_id", "telefone", name="uq_blacklist_agencia_telefone"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agencia_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    telefone = Column(String(50), nullable=False, index=True)
    motivo = Column(String(255), default="Oposição expressa RGPD", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tenant = relationship("Tenant", foreign_keys=[agencia_id])
