"""
Serviço da Reunião de Equipa (coletiva) com Presença e Atividade lançada pelo Diretor.

Regras de negócio:
- Cada POST cria SEMPRE uma nova reunião (nunca substitui uma já guardada) e pré-carrega
  1 linha por consultor ativo da agência (presença padrão 'Ausente', atividade a zeros).
- Edição livre até 24h após a criação. Depois a reunião fica "bloqueada" e só aceita
  edição excecional com `confirmar_edicao_excecional=True`, registada na auditoria
  com `updated_by`/`updated_at`.
- Assiduidade = (Presente + Atraso) / (Total − Ausências Justificadas) × 100.
- Consolidação nos KPIs (sem duplicação): os valores declarados ficam guardados à parte e
  são combinados com os registos do sistema por máximo determinístico (`consolidar`).
"""
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.log import Log
from app.models.team_meeting import CAMPOS_ATIVIDADE, TeamMeeting, TeamMeetingAttendance
from app.models.user import User
from app.schemas.team_meeting_schema import (
    AttendanceResponse,
    AttendanceStatsItem,
    AttendanceStatsResponse,
    TeamMeetingCreate,
    TeamMeetingResponse,
    TeamMeetingUpdate,
)

JANELA_EDICAO = timedelta(hours=24)
DIAS_PERMITIDOS = (7, 30, 90)


def _as_utc(dt: datetime) -> datetime:
    """SQLite devolve datetimes sem fuso; tratamo-los como UTC."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def consolidar(*valores: int) -> int:
    """Máximo determinístico (GREATEST) entre fontes; evita dupla contagem."""
    return max((int(v or 0) for v in valores), default=0)


class TeamMeetingService:

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _get_meeting(db: Session, agencia_id: int, meeting_id: int) -> TeamMeeting:
        meeting = db.query(TeamMeeting).filter(
            TeamMeeting.id == meeting_id,
            TeamMeeting.agencia_id == agencia_id,
        ).first()
        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reunião de equipa não encontrada.")
        return meeting

    @staticmethod
    def is_bloqueada(meeting: TeamMeeting, agora: Optional[datetime] = None) -> bool:
        agora = agora or datetime.now(timezone.utc)
        referencia = _as_utc(meeting.created_at or meeting.data_hora)
        return agora - referencia > JANELA_EDICAO

    @classmethod
    def _to_response(cls, meeting: TeamMeeting) -> TeamMeetingResponse:
        linhas = [
            AttendanceResponse(
                id=a.id,
                consultor_id=a.consultor_id,
                consultor_nome=a.consultor.nome if a.consultor else None,
                presenca=a.presenca,
                nota=a.nota,
                **{campo: getattr(a, campo) or 0 for campo in CAMPOS_ATIVIDADE},
            )
            for a in meeting.attendances
        ]
        return TeamMeetingResponse(
            id=meeting.id,
            diretor_id=meeting.diretor_id,
            diretor_nome=meeting.diretor.nome if meeting.diretor else None,
            data_hora=meeting.data_hora,
            tipo=meeting.tipo,
            notas_gerais=meeting.notas_gerais,
            bloqueada=cls.is_bloqueada(meeting),
            updated_by=meeting.updated_by,
            total_presentes=sum(1 for a in meeting.attendances if a.presenca in ("Presente", "Atraso")),
            total_consultores=len(meeting.attendances),
            linhas=linhas,
            created_at=meeting.created_at,
            updated_at=meeting.updated_at,
        )

    # ------------------------------------------------------------------ CRUD
    @classmethod
    def create(cls, db: Session, agencia_id: int, diretor_id: int, payload: TeamMeetingCreate) -> TeamMeetingResponse:
        meeting = TeamMeeting(
            agencia_id=agencia_id,
            diretor_id=diretor_id,
            data_hora=payload.data_hora or datetime.now(timezone.utc),
            tipo=payload.tipo,
            notas_gerais=payload.notas_gerais,
        )
        db.add(meeting)
        db.flush()

        consultores = (
            db.query(User)
            .filter(User.agencia_id == agencia_id, User.role == "consultor", User.ativo.is_(True))
            .order_by(User.nome.asc())
            .all()
        )
        for c in consultores:
            db.add(TeamMeetingAttendance(
                meeting_id=meeting.id,
                agencia_id=agencia_id,
                consultor_id=c.id,
                presenca="Ausente",
            ))

        db.add(Log(
            agencia_id=agencia_id,
            user_id=diretor_id,
            entidade="team_meeting",
            entidade_id=meeting.id,
            acao="reuniao_equipa_criada",
            detalhes=f"Reunião de equipa ({payload.tipo}) iniciada com {len(consultores)} consultores.",
        ))
        db.commit()
        db.refresh(meeting)
        return cls._to_response(meeting)

    @classmethod
    def update(
        cls, db: Session, agencia_id: int, user_id: int, meeting_id: int, payload: TeamMeetingUpdate
    ) -> TeamMeetingResponse:
        meeting = cls._get_meeting(db, agencia_id, meeting_id)
        excecional = cls.is_bloqueada(meeting)
        if excecional and not payload.confirmar_edicao_excecional:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Reunião consolidada (mais de 24h). Confirme a edição excecional para continuar.",
            )

        linhas_por_consultor: Dict[int, TeamMeetingAttendance] = {a.consultor_id: a for a in meeting.attendances}
        for row in payload.linhas:
            att = linhas_por_consultor.get(row.consultor_id)
            if att is None:
                # Consultor tem de pertencer à agência (ex.: entrou na equipa depois do início da reunião).
                consultor = db.query(User).filter(
                    User.id == row.consultor_id,
                    User.agencia_id == agencia_id,
                    User.role == "consultor",
                ).first()
                if not consultor:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Consultor {row.consultor_id} não pertence a esta agência.",
                    )
                att = TeamMeetingAttendance(meeting_id=meeting.id, agencia_id=agencia_id, consultor_id=consultor.id)
                db.add(att)
                meeting.attendances.append(att)
                linhas_por_consultor[consultor.id] = att

            att.presenca = row.presenca
            att.nota = row.nota
            for campo in CAMPOS_ATIVIDADE:
                setattr(att, campo, getattr(row, campo))

        if payload.tipo is not None:
            meeting.tipo = payload.tipo
        if payload.notas_gerais is not None:
            meeting.notas_gerais = payload.notas_gerais
        meeting.updated_by = user_id
        meeting.updated_at = datetime.now(timezone.utc)

        db.add(Log(
            agencia_id=agencia_id,
            user_id=user_id,
            entidade="team_meeting",
            entidade_id=meeting.id,
            acao="reuniao_equipa_edicao_excecional" if excecional else "reuniao_equipa_atualizada",
            detalhes=f"{len(payload.linhas)} linhas de presença/atividade gravadas"
                     + (" (edição excecional após 24h)." if excecional else "."),
        ))
        db.commit()
        db.refresh(meeting)
        return cls._to_response(meeting)

    @classmethod
    def get(cls, db: Session, agencia_id: int, meeting_id: int) -> TeamMeetingResponse:
        return cls._to_response(cls._get_meeting(db, agencia_id, meeting_id))

    @classmethod
    def list(cls, db: Session, agencia_id: int, limit: int = 30) -> List[TeamMeetingResponse]:
        meetings = (
            db.query(TeamMeeting)
            .filter(TeamMeeting.agencia_id == agencia_id)
            .order_by(TeamMeeting.data_hora.desc(), TeamMeeting.id.desc())
            .limit(limit)
            .all()
        )
        return [cls._to_response(m) for m in meetings]

    # ------------------------------------------------------------------ Assiduidade
    @staticmethod
    def attendance_map(db: Session, agencia_id: int, dias: int) -> Dict[int, Dict[str, int]]:
        desde = datetime.now(timezone.utc) - timedelta(days=dias)
        rows = (
            db.query(TeamMeetingAttendance.consultor_id, TeamMeetingAttendance.presenca, func.count())
            .join(TeamMeeting, TeamMeeting.id == TeamMeetingAttendance.meeting_id)
            .filter(
                TeamMeeting.agencia_id == agencia_id,
                TeamMeetingAttendance.agencia_id == agencia_id,
                TeamMeeting.data_hora >= desde,
            )
            .group_by(TeamMeetingAttendance.consultor_id, TeamMeetingAttendance.presenca)
            .all()
        )
        result: Dict[int, Dict[str, int]] = {}
        for consultor_id, presenca, total in rows:
            result.setdefault(consultor_id, {})[presenca] = int(total)
        return result

    @staticmethod
    def calcular_pct(contagens: Dict[str, int]) -> Optional[float]:
        presentes = contagens.get("Presente", 0) + contagens.get("Atraso", 0)
        total = sum(contagens.values())
        aplicaveis = total - contagens.get("AusenciaJustificada", 0)
        if aplicaveis <= 0:
            return None
        return round(presentes / aplicaveis * 100, 1)

    @classmethod
    def attendance_stats(cls, db: Session, agencia_id: int, dias: int = 30) -> AttendanceStatsResponse:
        if dias not in DIAS_PERMITIDOS:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="dias deve ser 7, 30 ou 90.")
        desde = datetime.now(timezone.utc) - timedelta(days=dias)
        total_reunioes = db.query(TeamMeeting).filter(
            TeamMeeting.agencia_id == agencia_id, TeamMeeting.data_hora >= desde
        ).count()
        mapa = cls.attendance_map(db, agencia_id, dias)
        consultores = (
            db.query(User)
            .filter(User.agencia_id == agencia_id, User.role == "consultor", User.ativo.is_(True))
            .order_by(User.nome.asc())
            .all()
        )
        items = []
        for c in consultores:
            cont = mapa.get(c.id, {})
            items.append(AttendanceStatsItem(
                consultor_id=c.id,
                nome=c.nome,
                presentes=cont.get("Presente", 0),
                atrasos=cont.get("Atraso", 0),
                ausentes=cont.get("Ausente", 0),
                justificadas=cont.get("AusenciaJustificada", 0),
                total_reunioes=sum(cont.values()),
                assiduidade_pct=cls.calcular_pct(cont),
            ))
        return AttendanceStatsResponse(dias=dias, total_reunioes=total_reunioes, consultores=items)

    # ------------------------------------------------------------------ Integração KPIs
    @staticmethod
    def declared_activity(
        db: Session,
        agencia_id: int,
        inicio: date,
        fim: date,
        consultor_id: Optional[int] = None,
    ) -> Dict[str, int]:
        """Soma da atividade DECLARADA nas reuniões de equipa do período (datas inclusivas)."""
        q = (
            db.query(*[func.coalesce(func.sum(getattr(TeamMeetingAttendance, c)), 0) for c in CAMPOS_ATIVIDADE])
            .join(TeamMeeting, TeamMeeting.id == TeamMeetingAttendance.meeting_id)
            .filter(
                TeamMeeting.agencia_id == agencia_id,
                TeamMeetingAttendance.agencia_id == agencia_id,
                func.date(TeamMeeting.data_hora) >= inicio,
                func.date(TeamMeeting.data_hora) <= fim,
            )
        )
        if consultor_id:
            q = q.filter(TeamMeetingAttendance.consultor_id == consultor_id)
        valores = q.one()
        return {campo: int(v or 0) for campo, v in zip(CAMPOS_ATIVIDADE, valores)}

    @staticmethod
    def declared_activity_by_consultor(
        db: Session,
        agencia_id: int,
        inicio: date,
        fim: date,
    ) -> Dict[int, Dict[str, int]]:
        """Igual a declared_activity, mas agrupado por consultor numa única consulta (evita N+1).
        Consultores sem registos não aparecem: use `.get(id, ZERO)`."""
        rows = (
            db.query(
                TeamMeetingAttendance.consultor_id,
                *[func.coalesce(func.sum(getattr(TeamMeetingAttendance, c)), 0) for c in CAMPOS_ATIVIDADE],
            )
            .join(TeamMeeting, TeamMeeting.id == TeamMeetingAttendance.meeting_id)
            .filter(
                TeamMeeting.agencia_id == agencia_id,
                TeamMeetingAttendance.agencia_id == agencia_id,
                func.date(TeamMeeting.data_hora) >= inicio,
                func.date(TeamMeeting.data_hora) <= fim,
            )
            .group_by(TeamMeetingAttendance.consultor_id)
            .all()
        )
        return {
            r[0]: {campo: int(v or 0) for campo, v in zip(CAMPOS_ATIVIDADE, r[1:])}
            for r in rows
        }

    @staticmethod
    def empty_activity() -> Dict[str, int]:
        return {campo: 0 for campo in CAMPOS_ATIVIDADE}
