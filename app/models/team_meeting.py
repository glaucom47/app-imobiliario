"""
Reunião de Equipa (coletiva) e Registo de Presença/Atividade por consultor.

- TeamMeeting: sessão coletiva (diária, semanal ou outra) conduzida pelo Diretor.
- TeamMeetingAttendance: 1 linha por consultor com presença e atividade DECLARADA
  ao Diretor durante a reunião. Os valores declarados ficam guardados de forma
  discriminada (nunca são somados aos registos do sistema) para garantir auditabilidade;
  a consolidação nos KPIs usa a regra determinística de máximo (ver team_meeting_service).
"""
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.connection import Base

TIPOS_REUNIAO = ("diaria", "semanal", "outra")
ESTADOS_PRESENCA = ("Presente", "Atraso", "Ausente", "AusenciaJustificada")
CAMPOS_ATIVIDADE = (
    "contactos",
    "reunioes_angariacao",
    "angariacoes",
    "exclusivos",
    "visitas",
    "propostas",
    "cpcv",
    "escrituras",
)


class TeamMeeting(Base):
    __tablename__ = "team_meetings"
    __table_args__ = (
        CheckConstraint("tipo IN ('diaria', 'semanal', 'outra')", name="chk_team_meeting_tipo"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agencia_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    diretor_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    data_hora = Column(DateTime(timezone=True), nullable=False, index=True)
    tipo = Column(String(20), nullable=False, default="diaria")
    notas_gerais = Column(Text, nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    diretor = relationship("User", foreign_keys=[diretor_id])
    attendances = relationship(
        "TeamMeetingAttendance",
        back_populates="meeting",
        cascade="all, delete-orphan",
        order_by="TeamMeetingAttendance.id",
    )

    def __repr__(self) -> str:
        return f"<TeamMeeting(id={self.id}, agencia_id={self.agencia_id}, tipo='{self.tipo}')>"


class TeamMeetingAttendance(Base):
    __tablename__ = "team_meeting_attendances"
    __table_args__ = (
        UniqueConstraint("meeting_id", "consultor_id", name="uq_team_attendance_meeting_consultor"),
        CheckConstraint(
            "presenca IN ('Presente', 'Atraso', 'Ausente', 'AusenciaJustificada')",
            name="chk_team_attendance_presenca",
        ),
        CheckConstraint(
            "contactos >= 0 AND reunioes_angariacao >= 0 AND angariacoes >= 0 AND exclusivos >= 0 "
            "AND visitas >= 0 AND propostas >= 0 AND cpcv >= 0 AND escrituras >= 0",
            name="chk_team_attendance_nao_negativo",
        ),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    meeting_id = Column(Integer, ForeignKey("team_meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    agencia_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    consultor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    presenca = Column(String(30), nullable=False, default="Ausente")

    contactos = Column(Integer, nullable=False, default=0)
    reunioes_angariacao = Column(Integer, nullable=False, default=0)
    angariacoes = Column(Integer, nullable=False, default=0)
    exclusivos = Column(Integer, nullable=False, default=0)
    visitas = Column(Integer, nullable=False, default=0)
    propostas = Column(Integer, nullable=False, default=0)
    cpcv = Column(Integer, nullable=False, default=0)
    escrituras = Column(Integer, nullable=False, default=0)
    nota = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    meeting = relationship("TeamMeeting", back_populates="attendances")
    consultor = relationship("User", foreign_keys=[consultor_id])

    def __repr__(self) -> str:
        return f"<TeamMeetingAttendance(meeting_id={self.meeting_id}, consultor_id={self.consultor_id}, presenca='{self.presenca}')>"
