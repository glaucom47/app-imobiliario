"""
Esquemas Pydantic para Visitas, Feedback por Voz e Objeções - Fecho (fecho.pt).

Validação estrita de tipagem, níveis de interesse (1 a 5) e isolamento multi-tenant.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ObjectionTagResponse(BaseModel):
    """Esquema de exibição de uma tag corporativa padronizada de objeção."""
    id: int
    tag: str
    categoria: str
    ativo: bool

    model_config = ConfigDict(from_attributes=True)


class VisitObjectionResponse(BaseModel):
    """Esquema de exibição de uma objeção registrada em visita."""
    id: int
    tag_id: int
    tag_nome: str
    categoria: str
    observacao: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AudioProcessRequest(BaseModel):
    """
    Requisição de processamento de nota oral/áudio de visita.
    Pode conter áudio em base64 ou notas orais preliminares.
    """
    audio_base64: Optional[str] = None
    audio_duracao_segundos: Optional[int] = Field(default=None, le=30, ge=1)
    raw_text: Optional[str] = None
    property_id: Optional[int] = None


class AudioProcessResponse(BaseModel):
    """
    Resultado estruturado do serviço de speech / IA para o ecrã Human-in-the-Loop.
    """
    transcricao: str
    notas_estruturadas: str
    nivel_interesse: int = Field(ge=1, le=5)
    audio_duracao_segundos: int = Field(le=30, ge=0)
    detected_tags: List[str] = []
    detected_tag_ids: List[int] = []


class VisitCreate(BaseModel):
    """
    Esquema de criação de registro de visita após validação no ecrã Human-in-the-Loop.
    """
    property_id: int
    cliente_nome: Optional[str] = Field(None, max_length=255)
    cliente_telefone: Optional[str] = Field(None, max_length=50)
    audio_duracao_segundos: Optional[int] = Field(None, ge=0, le=30)
    transcricao: Optional[str] = None
    notas_estruturadas: Optional[str] = None
    nivel_interesse: Optional[int] = Field(None, ge=1, le=5)
    objection_tag_ids: List[int] = []
    feedback_enviado_proprietario: bool = False


class VisitUpdate(BaseModel):
    """Esquema de atualização manual dos dados de uma visita."""
    cliente_nome: Optional[str] = Field(None, max_length=255)
    cliente_telefone: Optional[str] = Field(None, max_length=50)
    transcricao: Optional[str] = None
    notas_estruturadas: Optional[str] = None
    nivel_interesse: Optional[int] = Field(None, ge=1, le=5)
    objection_tag_ids: Optional[List[int]] = None
    feedback_enviado_proprietario: Optional[bool] = None


class PropertySummaryInVisit(BaseModel):
    """Resumo do imóvel vinculado para visualização de contexto em visita."""
    id: int
    titulo: str
    tipologia: str
    preco: float
    nome_proprietario: Optional[str] = None
    telefone_proprietario: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserSummaryInVisit(BaseModel):
    """Resumo do consultor que conduziu a visita."""
    id: int
    nome: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class VisitResponse(BaseModel):
    """Esquema completo de resposta de uma visita."""
    id: int
    agencia_id: int
    property_id: int
    consultor_id: int
    data_visita: datetime
    cliente_nome: Optional[str] = None
    cliente_telefone: Optional[str] = None
    audio_duracao_segundos: Optional[int] = None
    transcricao: Optional[str] = None
    notas_estruturadas: Optional[str] = None
    nivel_interesse: Optional[int] = None
    feedback_enviado_proprietario: bool
    created_at: datetime
    updated_at: datetime

    property: Optional[PropertySummaryInVisit] = None
    consultor: Optional[UserSummaryInVisit] = None
    objections: List[VisitObjectionResponse] = []

    # Mensagem formatada e link direto para WhatsApp do proprietário
    whatsapp_feedback_text: Optional[str] = None
    whatsapp_deep_link: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class VisitListResponse(BaseModel):
    """Esquema paginado de lista de visitas."""
    total: int
    visits: List[VisitResponse]
