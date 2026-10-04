"""
Esquemas Pydantic para o Módulo de Estudo de Mercado Comparativo (ACM) - Fecho (fecho.pt).

Validação estrita de contratos de dados para leitura de Caderneta Predial,
análise multimodal, relato de voz do consultor e benchmarking Casafari/Alfredo AI.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CadernetaDataInput(BaseModel):
    """Dados da Caderneta Predial Urbana (extraídos via OCR ou pré-preenchidos)."""
    concelho: Optional[str] = None
    distrito: Optional[str] = None
    freguesia: Optional[str] = None
    artigo_matricial: Optional[str] = None
    fracao: Optional[str] = None
    area_bruta_privativa: Optional[float] = Field(None, ge=10, le=5000)
    area_bruta_dependente: Optional[float] = Field(0.0, ge=0, le=2000)
    ano_matriz: Optional[int] = Field(None, ge=1800, le=2030)
    vpt: Optional[float] = Field(None, ge=0)
    tipologia: Optional[str] = None


class MarketStudyRequest(BaseModel):
    """Payload de submissão para geração do Estudo de Mercado Inteligente."""
    # Passo 1: Caderneta Predial (imagem ou texto OCR ou dados parciais)
    caderneta_base64: Optional[str] = None
    caderneta_raw_text: Optional[str] = None
    caderneta_manual: Optional[CadernetaDataInput] = None
    
    # Passo 2: Fotos dos Cómodos
    fotos_comodos_base64: Optional[List[str]] = Field(default_factory=list)
    tags_fotos: Optional[List[str]] = Field(default_factory=list)  # ex: ["fachada", "cozinha", "wc"]
    
    # Passo 3: Áudio e Notas do Consultor
    audio_base64: Optional[str] = None
    audio_duracao_segundos: Optional[int] = Field(None, ge=1, le=30)
    consultor_notas_voz: Optional[str] = None  # Transcrição ou texto ditado
    
    # Contexto e Benchmarking Externo
    property_id: Optional[int] = None
    nome_proprietario: Optional[str] = None
    telemovel_proprietario: Optional[str] = None
    casafari_manual_override: Optional[float] = None
    alfredo_manual_override: Optional[float] = None


class ComparableProperty(BaseModel):
    """Imóvel concorrente na zona para tabela comparativa."""
    id: int
    titulo: str
    tipologia: str
    area_util_m2: float
    preco_pedido: float
    preco_m2: float
    fonte: str
    estado: str
    distancia: str


class BenchmarkValuation(BaseModel):
    """Avaliação de um provedor de benchmarking externo."""
    provedor: str
    status: str
    preco_estimado: float
    preco_m2: float
    intervalo_baixo: Optional[float] = None
    intervalo_alto: Optional[float] = None
    indice_confianca: Optional[int] = None
    amostra_comparaveis: Optional[int] = None
    dias_medios_mercado: Optional[int] = None
    liquidez_zona: Optional[str] = None
    risco_sobrepreco: Optional[str] = None
    variacao_trimestral_pct: Optional[float] = None
    observacao: str


class TripleBenchmarkSummary(BaseModel):
    """Quadro de convergência tripla: Fecho x Casafari x Alfredo AI."""
    fecho_avaliacao: Dict[str, Any]
    casafari_avaliacao: BenchmarkValuation
    alfredo_avaliacao: BenchmarkValuation
    media_ponderada_mercado: float
    indice_convergencia_pct: float
    parecer_auditoria: str


class MarketStudyResponse(BaseModel):
    """Resposta executiva completa do Estudo de Mercado (ACM)."""
    # Enquadramento e Dados da Caderneta
    concelho: str
    distrito: str
    freguesia: str
    regiao_fiscal: str
    artigo_matricial: Optional[str] = None
    fracao: Optional[str] = None
    tipologia: str
    area_bruta_privativa: float
    area_bruta_dependente: float
    ano_matriz: Optional[int] = None
    vpt: Optional[float] = None
    
    # Análise de Campo e Qualitativa
    transcricao_consultor: str
    diagnostico_conservacao: str
    qualidade_acabamentos: str
    fatores_valorizacao: List[str]
    fatores_desvalorizacao: List[str]
    fator_ajuste_aplicado_pct: float
    
    # Estatística INE e Valores de Mercado
    preco_mediano_m2_ine: float
    preco_m2_calibrado: float
    preco_venda_rapida: float
    preco_recomendado: float
    preco_teto_teste: float
    
    # Amostra de Concorrência
    comparaveis: List[ComparableProperty]
    
    # Benchmarking e Auditoria Externa (Casafari & Alfredo AI)
    benchmarking_triplo: TripleBenchmarkSummary
    
    # Estratégia e Cartão do Consultor
    estrategia_comercializacao: str
    conclusao_executiva: str
    consultor_nome: str
    consultor_telemovel: str
    agencia_nome: str
    
    # Disparos e Partilha
    whatsapp_texto: str
    whatsapp_link: str

    model_config = ConfigDict(from_attributes=True)
