"""
Esquemas Pydantic para Gestão de Leads de Captação e Angariação - Fecho (fecho.pt).
Conforme FSD (Seção 6):
- Monitorização de hasta pública (e-leiloes.pt) e classificados abertos (OLX Particulares);
- Ciclo de vida: 'Novo', 'Em Prospeccao', 'Convertido', 'Descartado', 'Oposicao_RGPD';
- Conversão em 1 clique para 'Property' com status 'Ativo';
- Governança e minimização de dados do RGPD.
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class LeadBase(BaseModel):
    """Atributos fundamentais da oportunidade de captação."""
    fonte: str = Field(default="manual", description="Fonte de captação: e-leiloes, olx, manual")
    referencia_externa: str = Field(..., max_length=100, description="Identificador único no portal de origem")
    url_origem: str = Field(..., description="Link web do anúncio original")
    titulo: str = Field(..., min_length=3, max_length=255, description="Título do anúncio ou do lote")
    descricao: Optional[str] = Field(None, description="Descrição do imóvel captado")
    tipologia: str = Field(default="T2", max_length=20, description="Tipologia (T0, T1, T2, T3, Moradia, etc.)")
    preco_solicitado: Decimal = Field(..., gt=0, description="Preço de venda pedido ou valor base em euros (€)")
    valor_minimo_abertura: Optional[Decimal] = Field(None, gt=0, description="Valor mínimo de licitação (e-leilões)")
    distrito: Optional[str] = Field(None, max_length=100, description="Distrito (ex: Lisboa, Porto, Faro)")
    concelho: Optional[str] = Field(None, max_length=100, description="Concelho (ex: Lisboa, Sintra, Cascais)")
    freguesia: Optional[str] = Field(None, max_length=100, description="Freguesia")
    morada_aproximada: Optional[str] = Field(None, max_length=255, description="Localização aproximada")
    nome_contacto: Optional[str] = Field(None, max_length=255, description="Nome do anunciante / agente de execução")
    telefone_contacto: Optional[str] = Field(None, max_length=50, description="Contacto telefónico público")
    tipo_anunciante: str = Field(default="Particular", max_length=50, description="Particular ou Agente de Execução")
    data_limite_leilao: Optional[datetime] = Field(None, description="Data limite de encerramento do leilão")

    @field_validator("fonte")
    @classmethod
    def validate_fonte(cls, v: str) -> str:
        f = v.strip().lower()
        if f not in ("e-leiloes", "olx", "manual", "idealista"):
            return "manual"
        return f


class LeadCreate(LeadBase):
    """Payload para criação manual ou via scraper de lead de captação."""
    consultor_atribuido_id: Optional[int] = Field(None, description="ID do consultor responsável pela prospecção")


class LeadUpdate(BaseModel):
    """Payload para atualização de dados da oportunidade."""
    titulo: Optional[str] = Field(None, min_length=3, max_length=255)
    descricao: Optional[str] = None
    tipologia: Optional[str] = Field(None, max_length=20)
    preco_solicitado: Optional[Decimal] = Field(None, gt=0)
    valor_minimo_abertura: Optional[Decimal] = Field(None, gt=0)
    distrito: Optional[str] = None
    concelho: Optional[str] = None
    freguesia: Optional[str] = None
    morada_aproximada: Optional[str] = None
    nome_contacto: Optional[str] = None
    telefone_contacto: Optional[str] = None
    consultor_atribuido_id: Optional[int] = None
    notas_prospeccao: Optional[str] = None


class LeadStatusUpdate(BaseModel):
    """Payload para transição de status da prospecção."""
    status: str = Field(..., description="Novo status: 'Novo', 'Em Prospeccao', 'Descartado', 'Oposicao_RGPD'")
    notas_prospeccao: Optional[str] = Field(None, description="Nota de acompanhamento ou motivo de descarte")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        s = v.strip()
        permitidos = ("Novo", "Em Prospeccao", "Convertido", "Descartado", "Oposicao_RGPD")
        if s not in permitidos:
            raise ValueError(f"Status inválido. Deve ser um dos seguintes: {', '.join(permitidos)}.")
        return s


class LeadConvertRequest(BaseModel):
    """Payload da conversão em 1 clique da oportunidade em imóvel ativo."""
    consultor_id: Optional[int] = Field(None, description="Consultor que assumirá o imóvel (padrão: usuário logado)")
    regiao_fiscal: Optional[str] = Field("continente", description="Região fiscal do imóvel: continente, madeira, acores")


class LeadOposicaoRequest(BaseModel):
    """Payload para registro de oposição formal de RGPD."""
    motivo: Optional[str] = Field("Oposição expressa manifestada pelo proprietário", max_length=255)


class LeadExtractUrlRequest(BaseModel):
    """Payload para extração rápida via link do anúncio do portal."""
    url: str = Field(..., min_length=5, description="URL pública do anúncio no OLX ou lote no e-leilões")


class LeadScanRequest(BaseModel):
    """Payload opcional para disparo de varredura."""
    concelho: Optional[str] = Field(None, description="Concelho prioritário para varredura")
    distrito: Optional[str] = Field(None, description="Distrito para varredura")
    fonte: Optional[str] = Field(None, description="Fonte: e-leiloes, olx, todos")


class LeadResponse(LeadBase):
    """Representação serializada de uma oportunidade de angariação."""
    id: int
    agencia_id: int
    consultor_atribuido_id: Optional[int] = None
    consultor_nome: Optional[str] = None
    status: str
    imovel_convertido_id: Optional[int] = None
    notas_prospeccao: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeadListResponse(BaseModel):
    """Resposta paginada de listagem de oportunidades."""
    total: int
    items: List[LeadResponse]


class LeadStatsResponse(BaseModel):
    """Métricas consolidadas de captação para o painel de Backoffice."""
    total_oportunidades: int
    total_eleiloes: int
    total_particulares_olx: int
    total_convertidas: int
    taxa_conversao_pct: float
