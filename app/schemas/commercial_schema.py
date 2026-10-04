"""
Contratos e esquemas Pydantic v2 para o Módulo de Direção Comercial & Gestão Ativa de Equipa.
Conforme FSD Seção 8:
- Metas Comerciais Individuais (Goal)
- Oportunidades do Funil (PipelineDeal)
- Dashboard da Direção Comercial (CommercialDashboard)
- Funil de Vendas e Conversões (SalesFunnel)
- Tabela de Performance & Semáforo de Trajetória
- Ficha Individual do Consultor em 4 Blocos
- Reunião Semanal Automatizada e Compromissos
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


# ==========================================
# 1. Metas Comerciais (Goal)
# ==========================================

class GoalBase(BaseModel):
    ano: int = Field(..., ge=2020, le=2050, description="Ano de vigência da meta")
    mes: int = Field(..., ge=1, le=12, description="Mês de vigência da meta (1 a 12)")
    meta_faturacao: Decimal = Field(default=Decimal("0.00"), ge=0, description="Meta de faturação em euros")
    meta_contactos: int = Field(default=0, ge=0, description="Meta de contactos comerciais")
    meta_reunioes: int = Field(default=0, ge=0, description="Meta de reuniões com clientes")
    meta_angariacoes: int = Field(default=0, ge=0, description="Meta de novas angariações")
    meta_exclusivos: int = Field(default=0, ge=0, description="Meta de contratos em regime de exclusividade")
    meta_visitas: int = Field(default=0, ge=0, description="Meta de visitas a imóveis")
    meta_propostas: int = Field(default=0, ge=0, description="Meta de propostas recebidas ou apresentadas")
    meta_cpcv: int = Field(default=0, ge=0, description="Meta de contratos promessa de compra e venda (CPCV)")
    meta_escrituras: int = Field(default=0, ge=0, description="Meta de escrituras celebradas")


class GoalCreate(GoalBase):
    consultor_id: int = Field(..., description="Identificador do consultor imobiliário")


class GoalUpdate(BaseModel):
    meta_faturacao: Optional[Decimal] = Field(None, ge=0)
    meta_contactos: Optional[int] = Field(None, ge=0)
    meta_reunioes: Optional[int] = Field(None, ge=0)
    meta_angariacoes: Optional[int] = Field(None, ge=0)
    meta_exclusivos: Optional[int] = Field(None, ge=0)
    meta_visitas: Optional[int] = Field(None, ge=0)
    meta_propostas: Optional[int] = Field(None, ge=0)
    meta_cpcv: Optional[int] = Field(None, ge=0)
    meta_escrituras: Optional[int] = Field(None, ge=0)


class GoalResponse(GoalBase):
    id: int
    agencia_id: int
    consultor_id: int
    consultor_nome: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 2. Oportunidades do Funil (PipelineDeal)
# ==========================================

TipoNegocio = Literal["Venda", "Angariação", "Compra"]
FaseDeal = Literal[
    "Lead",
    "Qualificacao",
    "Angariacao",
    "Visita",
    "Proposta",
    "Negociacao",
    "CPCV",
    "Escritura",
    "Ganho",
    "Perdido",
]


class PipelineDealBase(BaseModel):
    cliente_nome: str = Field(..., min_length=2, max_length=255, description="Nome do cliente ou contacto")
    cliente_telefone: str = Field(..., min_length=6, max_length=50, description="Número de telemóvel do cliente")
    tipo_negocio: TipoNegocio = Field(default="Venda", description="Tipo de negócio imobiliário")
    valor_imovel: Decimal = Field(default=Decimal("0.00"), ge=0, description="Valor estimado ou de listagem do imóvel")
    comissao_estimada: Decimal = Field(default=Decimal("0.00"), ge=0, description="Valor estimado da comissão da agência")
    fase: FaseDeal = Field(default="Lead", description="Etapa atual no funil de negociação")
    probabilidade: int = Field(default=10, ge=0, le=100, description="Probabilidade estimada de fecho (0 a 100%)")
    data_prevista_fecho: Optional[date] = Field(None, description="Data estimada para a escritura ou fecho")
    proxima_acao: Optional[str] = Field(None, max_length=255, description="Próxima ação comercial programada")
    data_proxima_acao: Optional[date] = Field(None, description="Data limite para a próxima ação comercial")
    property_id: Optional[int] = Field(None, description="Vínculo opcional a imóvel da carteira")
    ativo: bool = Field(default=True, description="Indica se a oportunidade está ativa na carteira")


class PipelineDealCreate(PipelineDealBase):
    consultor_id: Optional[int] = Field(None, description="Identificador do consultor (opcional se enviado pelo próprio)")


class PipelineDealUpdate(BaseModel):
    cliente_nome: Optional[str] = Field(None, min_length=2, max_length=255)
    cliente_telefone: Optional[str] = Field(None, min_length=6, max_length=50)
    tipo_negocio: Optional[TipoNegocio] = None
    valor_imovel: Optional[Decimal] = Field(None, ge=0)
    comissao_estimada: Optional[Decimal] = Field(None, ge=0)
    fase: Optional[FaseDeal] = None
    probabilidade: Optional[int] = Field(None, ge=0, le=100)
    data_prevista_fecho: Optional[date] = None
    proxima_acao: Optional[str] = Field(None, max_length=255)
    data_proxima_acao: Optional[date] = None
    property_id: Optional[int] = None
    consultor_id: Optional[int] = None
    ativo: Optional[bool] = None


class PipelineDealResponse(PipelineDealBase):
    id: int
    agencia_id: int
    consultor_id: int
    consultor_nome: Optional[str] = None
    property_titulo: Optional[str] = None
    comissao_ponderada: Decimal = Field(default=Decimal("0.00"), description="Comissão estimada multiplicada pela probabilidade")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 3. Dashboard da Direção Comercial
# ==========================================

FiltroTemporal = Literal["7_dias", "30_dias", "90_dias", "este_mes", "mes_anterior", "historico"]


class CommercialKPIData(BaseModel):
    faturacao_realizada: Decimal = Field(description="Faturação total realizada no período")
    variacao_faturacao: str = Field(description="Variação percentual vs período homólogo anterior (+X% ou -X%)")
    meta_faturacao_total: Decimal = Field(description="Soma das metas de faturação da equipa no período")
    taxa_cumprimento_faturacao: float = Field(description="Percentual de cumprimento da meta de faturação")
    
    total_angariacoes: int = Field(description="Novas angariações no período")
    variacao_angariacoes: str = Field(description="Variação percentual de angariações vs período anterior")
    
    total_visitas: int = Field(description="Total de visitas realizadas no período")
    variacao_visitas: str = Field(description="Variação percentual de visitas vs período anterior")
    
    total_propostas: int = Field(description="Total de propostas apresentadas/recebidas no período")
    variacao_propostas: str = Field(description="Variação percentual de propostas vs período anterior")
    
    total_cpcv: int = Field(description="Contratos Promessa (CPCV) celebrados no período")
    variacao_cpcv: str = Field(description="Variação percentual de CPCV vs período anterior")
    
    total_escrituras: int = Field(description="Escrituras definitivas celebradas no período")
    variacao_escrituras: str = Field(description="Variação percentual de escrituras vs período anterior")
    
    pipeline_bruto: Decimal = Field(description="Soma de todas as comissões potenciais em aberto")
    pipeline_ponderado: Decimal = Field(description="Soma ponderada das comissões (comissão × probabilidade)")
    total_negocios_ativos: int = Field(description="Quantidade total de oportunidades ativas em carteira")


class CommercialDashboardResponse(BaseModel):
    filtro: str
    periodo_inicio: date
    periodo_fim: date
    kpis: CommercialKPIData
    deals_destaque: List[PipelineDealResponse] = Field(default_factory=list, description="Principais oportunidades do pipeline")


# ==========================================
# 4. Funil Comercial e Taxas de Conversão
# ==========================================

class FunnelStepItem(BaseModel):
    etapa: str = Field(description="Nome da etapa do funil (Contactos, Reuniões, etc.)")
    quantidade: int = Field(description="Volume de ocorrências nesta etapa")
    taxa_conversao_anterior: float = Field(description="Taxa de conversão em percentagem face à etapa anterior")
    taxa_conversao_topo: float = Field(description="Taxa de conversão em percentagem face ao topo do funil")


class SalesFunnelResponse(BaseModel):
    filtro: str
    consultor_id: Optional[int] = None
    consultor_nome: Optional[str] = None
    etapas: List[FunnelStepItem]
    taxa_conversao_global: float = Field(description="Taxa de conversão global (Contactos até Escrituras)")


# ==========================================
# 5. Tabela de Performance & Semáforo
# ==========================================

TrajetoriaSemaforo = Literal["verde", "amarelo", "vermelho"]


class ConsultorPerformanceItem(BaseModel):
    consultor_id: int
    nome: str
    email: str
    telemovel: Optional[str] = None
    meta_mensal: Decimal
    faturacao_realizada: Decimal
    percentual_cumprimento: float
    pipeline_ativo: Decimal
    pipeline_ponderado: Decimal
    visitas_realizadas: int
    propostas_realizadas: int
    angariacoes_realizadas: int
    trajetoria: TrajetoriaSemaforo = Field(description="🟢 verde: no ritmo ou acima; 🟡 amarelo: atenção; 🔴 vermelho: desvio crítico")
    justificacao_trajetoria: str = Field(description="Explicação sucinta do diagnóstico de trajetória")


class ConsultoresPerformanceResponse(BaseModel):
    ano: int
    mes: int
    total_consultores: int
    consultores: List[ConsultorPerformanceItem]


# ==========================================
# 6. Ficha Individual do Consultor (4 Blocos)
# ==========================================

class BlocoObjetivos(BaseModel):
    meta_faturacao: Decimal
    faturacao_realizada: Decimal
    projecao_final_mes: Decimal
    percentual_cumprimento: float
    dias_uteis_restantes: int
    ritmo_diario_necessario: Decimal


class BlocoAtividade(BaseModel):
    contactos: int
    reunioes: int
    angariacoes: int
    visitas: int
    propostas: int
    cpcv: int
    escrituras: int


class HistoricoSemanalItem(BaseModel):
    semana_ano: int
    ano: int
    visitas: int
    propostas: int
    faturacao: Decimal


class ConsultorIndividualPerformanceResponse(BaseModel):
    consultor_id: int
    nome: str
    email: str
    telemovel: Optional[str] = None
    ano: int
    mes: int
    bloco_1_objetivos: BlocoObjetivos
    bloco_2_atividade: BlocoAtividade
    bloco_3_funil: List[FunnelStepItem]
    bloco_4_historico: List[HistoricoSemanalItem]


# ==========================================
# 7. Reunião Semanal Automatizada & Compromissos
# ==========================================

StatusCompromisso = Literal["Pendente", "Cumprido", "Parcial", "NaoCumprido"]


class MeetingCommitmentBase(BaseModel):
    descricao_compromisso: str = Field(..., min_length=3, max_length=255)
    meta_quantitativa: Optional[str] = Field(None, max_length=100)
    prazo_data: date
    status: StatusCompromisso = Field(default="Pendente")
    percentual_cumprimento: int = Field(default=0, ge=0, le=100)


class MeetingCommitmentCreate(MeetingCommitmentBase):
    pass


class MeetingCommitmentUpdate(BaseModel):
    status: Optional[StatusCompromisso] = None
    percentual_cumprimento: Optional[int] = Field(None, ge=0, le=100)
    descricao_compromisso: Optional[str] = None
    meta_quantitativa: Optional[str] = None
    prazo_data: Optional[date] = None


class MeetingCommitmentResponse(MeetingCommitmentBase):
    id: int
    meeting_id: int
    consultor_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotaVisitaRecente(BaseModel):
    visit_id: int
    property_titulo: str
    data_visita: datetime
    nivel_interesse: int
    resumo_transcricao: Optional[str] = None
    tags_detetadas: List[str] = Field(default_factory=list)


class MeetingStartResponse(BaseModel):
    consultor_id: int
    consultor_nome: str
    diretor_id: int
    diretor_nome: str
    semana_ano: int
    ano: int
    data_reuniao_sugerida: datetime
    
    # Snapshot automático em tempo real puxado do sistema
    contactos_semana: int
    reunioes_semana: int
    angariacoes_semana: int
    visitas_semana: int
    propostas_semana: int
    cpcv_semana: int
    faturacao_semana: Decimal
    
    # Contexto humano de apoio à reunião
    compromissos_pendentes: List[MeetingCommitmentResponse] = Field(default_factory=list)
    notas_visitas_recentes: List[NotaVisitaRecente] = Field(default_factory=list)
    deals_prioritarios: List[PipelineDealResponse] = Field(default_factory=list)


class StatusCommitmentUpdateItem(BaseModel):
    id: int
    status: StatusCompromisso
    percentual_cumprimento: int = Field(default=0, ge=0, le=100)


class MeetingSaveRequest(BaseModel):
    consultor_id: int
    semana_ano: int = Field(..., ge=1, le=53)
    ano: int = Field(..., ge=2020, le=2050)
    data_reuniao: Optional[datetime] = None
    
    # Campos qualitativos humanos
    dificuldade_principal: Optional[str] = None
    negocio_prioritario: Optional[str] = None
    diagnostico_diretor: Optional[str] = None
    estrategia_definida: Optional[str] = None
    apoio_direcao_necessario: Optional[str] = None
    
    # Compromissos novos para a semana seguinte
    novos_compromissos: List[MeetingCommitmentCreate] = Field(default_factory=list)
    
    # Atualização dos compromissos da semana anterior
    atualizacao_compromissos: List[StatusCommitmentUpdateItem] = Field(default_factory=list)


class WeeklyMeetingResponse(BaseModel):
    id: int
    agencia_id: int
    diretor_id: int
    diretor_nome: Optional[str] = None
    consultor_id: int
    consultor_nome: Optional[str] = None
    data_reuniao: datetime
    semana_ano: int
    ano: int
    
    # Snapshot congelado
    contactos_realizados: int
    reunioes_realizadas: int
    angariacoes_realizadas: int
    visitas_realizadas: int
    propostas_realizadas: int
    cpcv_realizados: int
    faturacao_realizada: Decimal
    
    # Avaliação qualitativa
    dificuldade_principal: Optional[str] = None
    negocio_prioritario: Optional[str] = None
    diagnostico_diretor: Optional[str] = None
    estrategia_definida: Optional[str] = None
    apoio_direcao_necessario: Optional[str] = None
    
    commitments: List[MeetingCommitmentResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
