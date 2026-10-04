"""
Esquemas Pydantic para Backoffice, KPIs, Analytics de Objeções, Catálogo e Configurações - Fecho (fecho.pt).

Validação estrita de tipagem, controle de acesso e isolamento multi-tenant.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConsultorAssiduidade(BaseModel):
    """Métricas individuais de assiduidade e adesão do consultor."""
    consultor_id: int
    nome: str
    email: str
    total_visitas: int
    visitas_com_feedback: int
    taxa_adesao_percent: float
    nivel_interesse_medio: float
    ultima_visita: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class KPIsSummaryResponse(BaseModel):
    """Resumo consolidado de KPIs da agência para a direção."""
    periodo_dias: Optional[int] = None
    consultor_id: Optional[int] = None
    consultor_nome: Optional[str] = None
    total_visitas: int
    visitas_com_feedback: int
    taxa_adesao_percent: float
    visitas_enviadas_proprietario: int
    taxa_prestacao_contas_percent: float
    nivel_interesse_medio: float
    top_objecao: Optional[str] = None
    consultores_assiduidade: List[ConsultorAssiduidade] = []

    model_config = ConfigDict(from_attributes=True)


class ObjectionAnalyticsItem(BaseModel):
    """Item de agregação estatística de uma objeção."""
    tag_id: int
    tag: str
    categoria: str
    total_ocorrencias: int
    percentual_visitas: float

    model_config = ConfigDict(from_attributes=True)


class PropertyOptionItem(BaseModel):
    """Opção simplificada de imóvel para filtros no painel."""
    id: int
    titulo: str
    referencia: Optional[str] = None
    preco: float
    status: str
    nome_proprietario: Optional[str] = None
    telefone_proprietario: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PropertyObjectionAnalyticsResponse(BaseModel):
    """Consolidação analítica de objeções com argumento para renegociação de preços."""
    property_id: Optional[int] = None
    property_titulo: Optional[str] = None
    property_preco: Optional[float] = None
    nome_proprietario: Optional[str] = None
    telefone_proprietario: Optional[str] = None
    total_visitas_imovel: int
    total_visitas_com_objecoes: int
    distribuicao: List[ObjectionAnalyticsItem] = []
    resumo_renegociacao: str
    imoveis_disponiveis: List[PropertyOptionItem] = []

    model_config = ConfigDict(from_attributes=True)


class TagCreate(BaseModel):
    """Criação de tag corporativa no catálogo da agência."""
    tag: str = Field(..., min_length=2, max_length=100)
    categoria: str = Field(default="geral", max_length=50)
    ativo: bool = True


class TagUpdate(BaseModel):
    """Atualização de tag corporativa no catálogo da agência."""
    tag: Optional[str] = Field(None, min_length=2, max_length=100)
    categoria: Optional[str] = Field(None, max_length=50)
    ativo: Optional[bool] = None


class TagResponse(BaseModel):
    """Resposta com dados de tag corporativa de objeção."""
    id: int
    agencia_id: int
    tag: str
    categoria: str
    ativo: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgencySettingsResponse(BaseModel):
    """Parâmetros financeiros e operacionais da agência."""
    agencia_id: int
    spread_referencia: float
    taxa_stress: float
    prazo_max_financiamento_anos: int
    percentual_financiamento_max: float
    hora_notificacao_aniversario: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgencySettingsUpdate(BaseModel):
    """Atualização dos parâmetros financeiros e operacionais da agência."""
    spread_referencia: Optional[float] = Field(None, ge=0.0, le=10.0)
    taxa_stress: Optional[float] = Field(None, ge=0.0, le=10.0)
    prazo_max_financiamento_anos: Optional[int] = Field(None, ge=1, le=50)
    percentual_financiamento_max: Optional[float] = Field(None, ge=10.0, le=100.0)
    hora_notificacao_aniversario: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")


class ConsultorCreateRequest(BaseModel):
    """Payload para criação de novo consultor pela Direção Comercial."""
    nome: str = Field(..., min_length=2, max_length=255, description="Nome completo do consultor")
    email: str = Field(..., description="E-mail profissional do consultor")
    telemovel: Optional[str] = Field(None, max_length=50, description="Contacto telefónico do consultor")
    password: str = Field(..., min_length=6, max_length=128, description="Palavra-passe inicial de acesso (mínimo 6 carateres)")

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        import re
        email = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise ValueError("Formato de e-mail inválido.")
        return email


class ConsultorStatusUpdateRequest(BaseModel):
    """Payload para ativação ou desativação do acesso do consultor."""
    ativo: bool = Field(..., description="Estado de ativação da conta (True = Ativo, False = Inativo)")


class ConsultorUpdateRequest(BaseModel):
    """Payload para edição dos dados cadastrais do consultor pela Direção."""
    nome: Optional[str] = Field(None, min_length=2, max_length=255)
    telemovel: Optional[str] = Field(None, max_length=50)
    password: Optional[str] = Field(None, min_length=6, max_length=128, description="Nova palavra-passe opcional")


class ConsultorResponse(BaseModel):
    """Dados cadastrais, estado e métricas individuais do consultor na agência."""
    id: int
    agencia_id: int
    nome: str
    email: str
    role: str
    telemovel: Optional[str] = None
    ativo: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Métricas individuais em tempo real
    total_imoveis_ativos: Optional[int] = Field(None, description="Total de imóveis com status 'Ativo' atribuídos ao consultor")
    faturacao_mes: Optional[float] = Field(None, description="Faturação do consultor no mês corrente em euros")
    meta_mes: Optional[float] = Field(None, description="Meta mensal de faturação em euros")
    percentual_meta: Optional[float] = Field(None, description="Percentual de cumprimento da meta no mês")
    total_visitas_mes: Optional[int] = Field(None, description="Visitas realizadas pelo consultor no mês")
    trajetoria: Optional[str] = Field(None, description="Classificação de semáforo ('NoRitmo', 'Atencao', 'Critico')")

    model_config = ConfigDict(from_attributes=True)

