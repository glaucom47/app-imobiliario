"""Contratos Pydantic v2 da Reunião de Equipa (coletiva) e Assiduidade."""
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

TipoReuniao = Literal["diaria", "semanal", "outra"]
EstadoPresenca = Literal["Presente", "Atraso", "Ausente", "AusenciaJustificada"]


class TeamMeetingCreate(BaseModel):
    tipo: TipoReuniao = "diaria"
    data_hora: Optional[datetime] = None
    notas_gerais: Optional[str] = Field(default=None, max_length=5000)


class AttendanceUpdateRow(BaseModel):
    consultor_id: int
    presenca: EstadoPresenca
    contactos: int = Field(default=0, ge=0, le=10000)
    reunioes_angariacao: int = Field(default=0, ge=0, le=10000)
    angariacoes: int = Field(default=0, ge=0, le=10000)
    exclusivos: int = Field(default=0, ge=0, le=10000)
    visitas: int = Field(default=0, ge=0, le=10000)
    propostas: int = Field(default=0, ge=0, le=10000)
    cpcv: int = Field(default=0, ge=0, le=10000)
    escrituras: int = Field(default=0, ge=0, le=10000)
    nota: Optional[str] = Field(default=None, max_length=2000)


class TeamMeetingUpdate(BaseModel):
    tipo: Optional[TipoReuniao] = None
    notas_gerais: Optional[str] = Field(default=None, max_length=5000)
    linhas: List[AttendanceUpdateRow] = Field(default_factory=list, max_length=500)
    confirmar_edicao_excecional: bool = Field(
        default=False,
        description="Obrigatório para editar uma reunião com mais de 24h (fica registado na auditoria).",
    )


class AttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    consultor_id: int
    consultor_nome: Optional[str] = None
    presenca: EstadoPresenca
    contactos: int
    reunioes_angariacao: int
    angariacoes: int
    exclusivos: int
    visitas: int
    propostas: int
    cpcv: int
    escrituras: int
    nota: Optional[str] = None


class TeamMeetingResponse(BaseModel):
    id: int
    diretor_id: int
    diretor_nome: Optional[str] = None
    data_hora: datetime
    tipo: TipoReuniao
    notas_gerais: Optional[str] = None
    bloqueada: bool = Field(description="True quando passaram mais de 24h (edição só excecional).")
    updated_by: Optional[int] = None
    total_presentes: int
    total_consultores: int
    linhas: List[AttendanceResponse]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AttendanceStatsItem(BaseModel):
    consultor_id: int
    nome: str
    presentes: int
    atrasos: int
    ausentes: int
    justificadas: int
    total_reunioes: int
    assiduidade_pct: Optional[float] = Field(
        default=None,
        description="(Presente + Atraso) / (Total − Justificadas) × 100. None sem reuniões aplicáveis.",
    )


class AttendanceStatsResponse(BaseModel):
    dias: int
    total_reunioes: int
    consultores: List[AttendanceStatsItem]
