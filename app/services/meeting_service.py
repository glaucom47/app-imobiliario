"""
Serviço de acompanhamento e reuniões semanais automatizadas (FSD Seção 8).
Implementa as regras de negócio de:
- Inicialização de sessão semanal com snapshot em tempo real e inteligência de visitas
- Gravação de reuniões, congelamento atômico de métricas e compromissos
- Histórico evolutivo cronológico das reuniões por consultor
- Atualização e monitorização de compromissos semanais
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.commercial import MeetingCommitment, PipelineDeal, WeeklyMeeting
from app.models.log import Log
from app.models.objection import ObjectionTag, VisitObjection
from app.models.property import Property
from app.models.user import User
from app.models.visit import Visit
from app.schemas.commercial_schema import (
    MeetingCommitmentResponse,
    MeetingSaveRequest,
    MeetingStartResponse,
    NotaVisitaRecente,
    PipelineDealResponse,
    WeeklyMeetingResponse,
)


class MeetingService:

    @classmethod
    def start_meeting(
        cls,
        db: Session,
        agencia_id: int,
        diretor_id: int,
        consultor_id: int,
    ) -> MeetingStartResponse:
        """
        Inicializa a reunião semanal puxando automaticamente dados de atividade,
        últimas transcrições/notas de visita e pendências anteriores.
        """
        diretor = db.query(User).filter(User.id == diretor_id, User.agencia_id == agencia_id).first()
        consultor = db.query(User).filter(User.id == consultor_id, User.agencia_id == agencia_id).first()

        if not diretor or not consultor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilizador não encontrado na agência.")

        agora = datetime.now(timezone.utc)
        ano_iso, semana_iso, _ = agora.isocalendar()

        # Janela dos últimos 7 dias para consolidação da semana
        sete_dias_atras = agora - timedelta(days=7)

        # 1. Visitas da semana
        visitas_semana = db.query(Visit).filter(
            Visit.agencia_id == agencia_id,
            Visit.consultor_id == consultor_id,
            Visit.data_visita >= sete_dias_atras,
        ).all()
        total_visitas = len(visitas_semana)

        # 2. Angariações da semana
        total_angariacoes = db.query(Property).filter(
            Property.agencia_id == agencia_id,
            Property.consultor_id == consultor_id,
            Property.created_at >= sete_dias_atras,
        ).count()

        # 3. Deals da semana (propostas, cpcv)
        deals_semana = db.query(PipelineDeal).filter(
            PipelineDeal.agencia_id == agencia_id,
            PipelineDeal.consultor_id == consultor_id,
            PipelineDeal.created_at >= sete_dias_atras,
        ).all()

        total_propostas = sum(1 for d in deals_semana if d.fase in ["Proposta", "Negociacao", "CPCV", "Escritura", "Ganho"])
        total_cpcv = sum(1 for d in deals_semana if d.fase in ["CPCV", "Escritura", "Ganho"])

        # 4. Faturação da semana
        props_vendidos = db.query(Property).filter(
            Property.agencia_id == agencia_id,
            Property.consultor_id == consultor_id,
            Property.status == "Vendido",
            Property.data_escritura >= sete_dias_atras.date(),
        ).all()
        faturacao_semana = sum((Decimal(str(p.preco)) * Decimal("0.05") for p in props_vendidos), Decimal("0.00"))

        # Estimativas de contactos e reuniões
        total_contactos = max(len(deals_semana) * 3, total_visitas * 2, 8 if total_visitas > 0 else 0)
        total_reunioes = max(len(deals_semana), total_visitas, 2 if total_visitas > 0 else 0)

        # 5. Compromissos pendentes da reunião anterior
        compromissos_pendentes_db = db.query(MeetingCommitment).filter(
            MeetingCommitment.consultor_id == consultor_id,
            MeetingCommitment.status.in_(["Pendente", "Parcial", "NaoCumprido"]),
        ).order_by(MeetingCommitment.prazo_data.asc()).all()

        compromissos_pendentes = [
            MeetingCommitmentResponse(
                id=c.id,
                meeting_id=c.meeting_id,
                consultor_id=c.consultor_id,
                descricao_compromisso=c.descricao_compromisso,
                meta_quantitativa=c.meta_quantitativa,
                prazo_data=c.prazo_data,
                status=c.status,
                percentual_cumprimento=c.percentual_cumprimento,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in compromissos_pendentes_db
        ]

        # 6. Últimas notas de visita (até 5 visitas recentes com resumo de voz)
        ultimas_visitas = db.query(Visit).filter(
            Visit.agencia_id == agencia_id,
            Visit.consultor_id == consultor_id,
        ).order_by(Visit.data_visita.desc()).limit(5).all()

        notas_visitas: List[NotaVisitaRecente] = []
        for v in ultimas_visitas:
            # Buscar tags associadas à visita
            tags_db = (
                db.query(ObjectionTag.tag)
                .join(VisitObjection, VisitObjection.tag_id == ObjectionTag.id)
                .filter(VisitObjection.visit_id == v.id)
                .all()
            )
            tags_nomes = [t[0] for t in tags_db]

            notas_visitas.append(
                NotaVisitaRecente(
                    visit_id=v.id,
                    property_titulo=v.property.titulo if v.property else "Imóvel",
                    data_visita=v.data_visita,
                    nivel_interesse=v.nivel_interesse,
                    resumo_transcricao=v.notas_estruturadas or v.transcricao or "Sem notas adicionais registadas.",
                    tags_detetadas=tags_nomes,
                )
            )

        # 7. Deals prioritários em carteira
        deals_prioritarios_db = db.query(PipelineDeal).filter(
            PipelineDeal.agencia_id == agencia_id,
            PipelineDeal.consultor_id == consultor_id,
            PipelineDeal.ativo.is_(True),
            PipelineDeal.fase.in_(["Proposta", "Negociacao", "CPCV", "Angariacao"]),
        ).order_by(PipelineDeal.probabilidade.desc()).limit(5).all()

        deals_prioritarios = [
            PipelineDealResponse(
                id=d.id,
                agencia_id=d.agencia_id,
                consultor_id=d.consultor_id,
                consultor_nome=consultor.nome,
                property_id=d.property_id,
                property_titulo=d.property.titulo if d.property else None,
                cliente_nome=d.cliente_nome,
                cliente_telefone=d.cliente_telefone,
                tipo_negocio=d.tipo_negocio,
                valor_imovel=d.valor_imovel,
                comissao_estimada=d.comissao_estimada,
                comissao_ponderada=Decimal(str(d.comissao_estimada)) * (Decimal(str(d.probabilidade)) / Decimal("100")),
                fase=d.fase,
                probabilidade=d.probabilidade,
                data_prevista_fecho=d.data_prevista_fecho,
                proxima_acao=d.proxima_acao,
                data_proxima_acao=d.data_proxima_acao,
                ativo=d.ativo,
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
            for d in deals_prioritarios_db
        ]

        return MeetingStartResponse(
            consultor_id=consultor.id,
            consultor_nome=consultor.nome,
            diretor_id=diretor.id,
            diretor_nome=diretor.nome,
            semana_ano=semana_iso,
            ano=ano_iso,
            data_reuniao_sugerida=agora,
            contactos_semana=total_contactos,
            reunioes_semana=total_reunioes,
            angariacoes_semana=total_angariacoes,
            visitas_semana=total_visitas,
            propostas_semana=total_propostas,
            cpcv_semana=total_cpcv,
            faturacao_semana=faturacao_semana,
            compromissos_pendentes=compromissos_pendentes,
            notas_visitas_recentes=notas_visitas,
            deals_prioritarios=deals_prioritarios,
        )

    @classmethod
    def save_meeting(
        cls,
        db: Session,
        agencia_id: int,
        diretor_id: int,
        payload: MeetingSaveRequest,
    ) -> WeeklyMeetingResponse:
        """
        Grava a reunião semanal, congela o snapshot quantitativo da semana,
        atualiza pendências anteriores e cadastra novos compromissos.
        """
        consultor = db.query(User).filter(
            User.id == payload.consultor_id,
            User.agencia_id == agencia_id,
        ).first()

        if not consultor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultor não encontrado.")

        diretor = db.query(User).filter(
            User.id == diretor_id,
            User.agencia_id == agencia_id,
        ).first()

        # Calcular snapshot da semana no momento do fecho da reunião
        sete_dias = (payload.data_reuniao or datetime.now(timezone.utc)) - timedelta(days=7)

        visitas_count = db.query(Visit).filter(
            Visit.agencia_id == agencia_id,
            Visit.consultor_id == payload.consultor_id,
            Visit.data_visita >= sete_dias,
        ).count()

        angariacoes_count = db.query(Property).filter(
            Property.agencia_id == agencia_id,
            Property.consultor_id == payload.consultor_id,
            Property.created_at >= sete_dias,
        ).count()

        deals_count = db.query(PipelineDeal).filter(
            PipelineDeal.agencia_id == agencia_id,
            PipelineDeal.consultor_id == payload.consultor_id,
            PipelineDeal.created_at >= sete_dias,
        ).all()

        propostas_count = sum(1 for d in deals_count if d.fase in ["Proposta", "Negociacao", "CPCV", "Escritura", "Ganho"])
        cpcv_count = sum(1 for d in deals_count if d.fase in ["CPCV", "Escritura", "Ganho"])

        props_vendidos = db.query(Property).filter(
            Property.agencia_id == agencia_id,
            Property.consultor_id == payload.consultor_id,
            Property.status == "Vendido",
            Property.data_escritura >= sete_dias.date(),
        ).all()
        faturacao_valor = sum((Decimal(str(p.preco)) * Decimal("0.05") for p in props_vendidos), Decimal("0.00"))

        contactos_count = max(len(deals_count) * 3, visitas_count * 2, 8 if visitas_count > 0 else 0)
        reunioes_count = max(len(deals_count), visitas_count, 2 if visitas_count > 0 else 0)

        # Criar nova reunião semanal
        meeting = WeeklyMeeting(
            agencia_id=agencia_id,
            diretor_id=diretor_id,
            consultor_id=payload.consultor_id,
            data_reuniao=payload.data_reuniao or datetime.now(timezone.utc),
            semana_ano=payload.semana_ano,
            ano=payload.ano,
            contactos_realizados=contactos_count,
            reunioes_realizadas=reunioes_count,
            angariacoes_realizadas=angariacoes_count,
            visitas_realizadas=visitas_count,
            propostas_realizadas=propostas_count,
            cpcv_realizados=cpcv_count,
            faturacao_realizada=faturacao_valor,
            dificuldade_principal=payload.dificuldade_principal,
            negocio_prioritario=payload.negocio_prioritario,
            diagnostico_diretor=payload.diagnostico_diretor,
            estrategia_definida=payload.estrategia_definida,
            apoio_direcao_necessario=payload.apoio_direcao_necessario,
        )
        db.add(meeting)
        db.flush()  # Garante meeting.id gerado

        # 1. Atualizar compromissos anteriores se indicados
        for update_item in payload.atualizacao_compromissos:
            comm = db.query(MeetingCommitment).filter(
                MeetingCommitment.id == update_item.id,
                MeetingCommitment.consultor_id == payload.consultor_id,
            ).first()
            if comm:
                comm.status = update_item.status
                comm.percentual_cumprimento = update_item.percentual_cumprimento

        # 2. Cadastrar novos compromissos vinculados a esta reunião
        novos_comms: List[MeetingCommitment] = []
        for novo in payload.novos_compromissos:
            comm = MeetingCommitment(
                meeting_id=meeting.id,
                consultor_id=payload.consultor_id,
                descricao_compromisso=novo.descricao_compromisso,
                meta_quantitativa=novo.meta_quantitativa,
                prazo_data=novo.prazo_data,
                status=novo.status,
                percentual_cumprimento=novo.percentual_cumprimento,
            )
            db.add(comm)
            novos_comms.append(comm)

        # Registo de auditoria
        audit = Log(
            agencia_id=agencia_id,
            user_id=diretor_id,
            entidade="weekly_meeting",
            entidade_id=meeting.id,
            acao="reuniao_semanal_gravada",
            detalhes=f"Reunião da semana {payload.semana_ano}/{payload.ano} gravada para o consultor {consultor.nome} com {len(novos_comms)} compromissos.",
        )
        db.add(audit)

        db.commit()
        db.refresh(meeting)

        return WeeklyMeetingResponse(
            id=meeting.id,
            agencia_id=meeting.agencia_id,
            diretor_id=meeting.diretor_id,
            diretor_nome=diretor.nome if diretor else None,
            consultor_id=meeting.consultor_id,
            consultor_nome=consultor.nome,
            data_reuniao=meeting.data_reuniao,
            semana_ano=meeting.semana_ano,
            ano=meeting.ano,
            contactos_realizados=meeting.contactos_realizados,
            reunioes_realizadas=meeting.reunioes_realizadas,
            angariacoes_realizadas=meeting.angariacoes_realizadas,
            visitas_realizadas=meeting.visitas_realizadas,
            propostas_realizadas=meeting.propostas_realizadas,
            cpcv_realizados=meeting.cpcv_realizados,
            faturacao_realizada=meeting.faturacao_realizada,
            dificuldade_principal=meeting.dificuldade_principal,
            negocio_prioritario=meeting.negocio_prioritario,
            diagnostico_diretor=meeting.diagnostico_diretor,
            estrategia_definida=meeting.estrategia_definida,
            apoio_direcao_necessario=meeting.apoio_direcao_necessario,
            commitments=[
                MeetingCommitmentResponse(
                    id=c.id,
                    meeting_id=c.meeting_id,
                    consultor_id=c.consultor_id,
                    descricao_compromisso=c.descricao_compromisso,
                    meta_quantitativa=c.meta_quantitativa,
                    prazo_data=c.prazo_data,
                    status=c.status,
                    percentual_cumprimento=c.percentual_cumprimento,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                )
                for c in meeting.commitments
            ],
            created_at=meeting.created_at,
            updated_at=meeting.updated_at,
        )

    @staticmethod
    def list_consultor_meetings(
        db: Session,
        agencia_id: int,
        consultor_id: int,
    ) -> List[WeeklyMeetingResponse]:
        """Retorna o histórico cronológico de reuniões semanais de um consultor."""
        consultor = db.query(User).filter(
            User.id == consultor_id,
            User.agencia_id == agencia_id,
        ).first()

        if not consultor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultor não encontrado.")

        meetings = (
            db.query(WeeklyMeeting)
            .filter(
                WeeklyMeeting.agencia_id == agencia_id,
                WeeklyMeeting.consultor_id == consultor_id,
            )
            .order_by(WeeklyMeeting.data_reuniao.desc())
            .all()
        )

        return [
            WeeklyMeetingResponse(
                id=m.id,
                agencia_id=m.agencia_id,
                diretor_id=m.diretor_id,
                diretor_nome=m.diretor.nome if m.diretor else None,
                consultor_id=m.consultor_id,
                consultor_nome=consultor.nome,
                data_reuniao=m.data_reuniao,
                semana_ano=m.semana_ano,
                ano=m.ano,
                contactos_realizados=m.contactos_realizados,
                reunioes_realizadas=m.reunioes_realizadas,
                angariacoes_realizadas=m.angariacoes_realizadas,
                visitas_realizadas=m.visitas_realizadas,
                propostas_realizadas=m.propostas_realizadas,
                cpcv_realizados=m.cpcv_realizados,
                faturacao_realizada=m.faturacao_realizada,
                dificuldade_principal=m.dificuldade_principal,
                negocio_prioritario=m.negocio_prioritario,
                diagnostico_diretor=m.diagnostico_diretor,
                estrategia_definida=m.estrategia_definida,
                apoio_direcao_necessario=m.apoio_direcao_necessario,
                commitments=[
                    MeetingCommitmentResponse(
                        id=c.id,
                        meeting_id=c.meeting_id,
                        consultor_id=c.consultor_id,
                        descricao_compromisso=c.descricao_compromisso,
                        meta_quantitativa=c.meta_quantitativa,
                        prazo_data=c.prazo_data,
                        status=c.status,
                        percentual_cumprimento=c.percentual_cumprimento,
                        created_at=c.created_at,
                        updated_at=c.updated_at,
                    )
                    for c in m.commitments
                ],
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
            for m in meetings
        ]
