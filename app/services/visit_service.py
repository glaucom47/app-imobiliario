"""
Serviço de Negócios para Visitas e Objeções - Fecho (fecho.pt).

Implementa:
- Isolamento multi-tenant rigoroso por agencia_id;
- Validação de propriedade e catálogo de tags;
- Associação de objeções por visita;
- Gestão de status de feedback enviado ao proprietário;
- Geração de respostas enriquecidas com WhatsApp Deep Link.
"""
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.objection import ObjectionTag, VisitObjection
from app.models.property import Property
from app.models.user import User
from app.models.visit import Visit
from app.schemas.visit_schema import (
    AudioProcessRequest,
    AudioProcessResponse,
    ObjectionTagResponse,
    VisitCreate,
    VisitObjectionResponse,
    VisitResponse,
    VisitUpdate,
)
from app.services.speech_service import SpeechService


class VisitService:
    """Regras de negócio e persistência para visitas e notas de voz."""

    @staticmethod
    def get_agency_objection_tags(db: Session, agencia_id: int) -> List[ObjectionTag]:
        """Retorna todas as tags corporativas de objeção ativas da agência."""
        return (
            db.query(ObjectionTag)
            .filter(ObjectionTag.agencia_id == agencia_id, ObjectionTag.ativo.is_(True))
            .order_by(ObjectionTag.categoria, ObjectionTag.tag)
            .all()
        )

    @classmethod
    def process_audio_or_notes(
        cls,
        db: Session,
        agencia_id: int,
        request: AudioProcessRequest,
    ) -> AudioProcessResponse:
        """
        Orquestra a análise semântica de notas de voz ou transcrição prévia.
        Cruza com o catálogo corporativo da agência para sugerir tags no ecrã Human-in-the-Loop.
        """
        # Obtém catálogo da agência
        tags = cls.get_agency_objection_tags(db, agencia_id)
        tag_dicts = [{"id": t.id, "tag": t.tag, "categoria": t.categoria} for t in tags]

        # Texto de entrada (raw_text ou extraído)
        input_text = request.raw_text or ""
        duracao = request.audio_duracao_segundos or (30 if request.audio_base64 else 0)

        nivel, det_names, det_ids, notas = SpeechService.analyze_transcript(
            text=input_text,
            available_tags=tag_dicts,
        )

        return AudioProcessResponse(
            transcricao=input_text if input_text else "Nota de voz gravada em visita.",
            notas_estruturadas=notas,
            nivel_interesse=nivel,
            audio_duracao_segundos=duracao,
            detected_tags=det_names,
            detected_tag_ids=det_ids,
        )

    @classmethod
    def create_visit(
        cls,
        db: Session,
        agencia_id: int,
        user: User,
        data: VisitCreate,
    ) -> VisitResponse:
        """
        Registra uma nova visita após a validação no ecrã Human-in-the-Loop.
        Garante isolamento multi-tenant e integridade referencial com o imóvel.
        """
        # 1. Valida se o imóvel existe e pertence à mesma agência
        property_obj = (
            db.query(Property)
            .filter(Property.id == data.property_id, Property.agencia_id == agencia_id)
            .first()
        )
        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Imóvel não encontrado ou não pertence a esta agência.",
            )

        # 2. Cria a entidade Visit
        visit = Visit(
            agencia_id=agencia_id,
            property_id=property_obj.id,
            consultor_id=user.id,
            cliente_nome=data.cliente_nome.strip() if data.cliente_nome else None,
            cliente_telefone=data.cliente_telefone.strip() if data.cliente_telefone else None,
            audio_duracao_segundos=data.audio_duracao_segundos,
            transcricao=data.transcricao.strip() if data.transcricao else None,
            notas_estruturadas=data.notas_estruturadas.strip() if data.notas_estruturadas else None,
            nivel_interesse=data.nivel_interesse,
            feedback_enviado_proprietario=data.feedback_enviado_proprietario,
        )
        db.add(visit)
        db.flush()

        # 3. Associa as tags de objeção válidas da agência
        objection_responses: List[VisitObjectionResponse] = []
        objection_names: List[str] = []

        if data.objection_tag_ids:
            # Filtra apenas tags da mesma agência
            valid_tags = (
                db.query(ObjectionTag)
                .filter(
                    ObjectionTag.id.in_(data.objection_tag_ids),
                    ObjectionTag.agencia_id == agencia_id,
                )
                .all()
            )

            for tag in valid_tags:
                v_obj = VisitObjection(
                    agencia_id=agencia_id,
                    visit_id=visit.id,
                    property_id=property_obj.id,
                    tag_id=tag.id,
                )
                db.add(v_obj)
                db.flush()
                objection_responses.append(
                    VisitObjectionResponse(
                        id=v_obj.id,
                        tag_id=tag.id,
                        tag_nome=tag.tag,
                        categoria=tag.categoria,
                        observacao=None,
                    )
                )
                objection_names.append(tag.tag)

        db.commit()
        db.refresh(visit)

        # 4. Gera a mensagem formatada para o WhatsApp do proprietário
        wa_text, wa_link = SpeechService.format_whatsapp_feedback(
            propriedade=property_obj,
            consultor=user,
            nivel_interesse=visit.nivel_interesse,
            notas_estruturadas=visit.notas_estruturadas,
            objection_names=objection_names,
        )

        return cls._build_visit_response(visit, property_obj, user, objection_responses, wa_text, wa_link)

    @classmethod
    def get_visit_by_id(
        cls,
        db: Session,
        agencia_id: int,
        visit_id: int,
        user: User,
    ) -> VisitResponse:
        """Recupera detalhes de uma visita com isolamento multi-tenant e RBAC."""
        query = (
            db.query(Visit)
            .options(
                joinedload(Visit.property),
                joinedload(Visit.consultor),
                joinedload(Visit.objections).joinedload(VisitObjection.tag),
            )
            .filter(Visit.id == visit_id, Visit.agencia_id == agencia_id)
        )

        # Consultor só pode acessar suas próprias visitas a menos que seja diretor
        if user.role != "diretor":
            query = query.filter(Visit.consultor_id == user.id)

        visit = query.first()
        if not visit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Visita não encontrada ou acesso não autorizado.",
            )

        objection_responses = [
            VisitObjectionResponse(
                id=o.id,
                tag_id=o.tag_id,
                tag_nome=o.tag.tag if o.tag else "Objeção",
                categoria=o.tag.categoria if o.tag else "geral",
                observacao=o.observacao,
            )
            for o in visit.objections
        ]
        objection_names = [o.tag_nome for o in objection_responses]

        wa_text, wa_link = SpeechService.format_whatsapp_feedback(
            propriedade=visit.property,
            consultor=visit.consultor,
            nivel_interesse=visit.nivel_interesse,
            notas_estruturadas=visit.notas_estruturadas,
            objection_names=objection_names,
        )

        return cls._build_visit_response(
            visit, visit.property, visit.consultor, objection_responses, wa_text, wa_link
        )

    @classmethod
    def list_visits(
        cls,
        db: Session,
        agencia_id: int,
        user: User,
        property_id: Optional[int] = None,
        consultor_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[VisitResponse]:
        """Lista visitas da agência respeitando filtros e regras de RBAC."""
        query = (
            db.query(Visit)
            .options(
                joinedload(Visit.property),
                joinedload(Visit.consultor),
                joinedload(Visit.objections).joinedload(VisitObjection.tag),
            )
            .filter(Visit.agencia_id == agencia_id)
        )

        # RBAC: consultor vê apenas suas próprias visitas
        if user.role != "diretor":
            query = query.filter(Visit.consultor_id == user.id)
        elif consultor_id:
            query = query.filter(Visit.consultor_id == consultor_id)

        if property_id:
            query = query.filter(Visit.property_id == property_id)

        query = query.order_by(Visit.data_visita.desc())
        visits = query.offset(skip).limit(limit).all()

        responses = []
        for v in visits:
            obj_responses = [
                VisitObjectionResponse(
                    id=o.id,
                    tag_id=o.tag_id,
                    tag_nome=o.tag.tag if o.tag else "Objeção",
                    categoria=o.tag.categoria if o.tag else "geral",
                    observacao=o.observacao,
                )
                for o in v.objections
            ]
            obj_names = [o.tag_nome for o in obj_responses]

            wa_text, wa_link = SpeechService.format_whatsapp_feedback(
                propriedade=v.property,
                consultor=v.consultor,
                nivel_interesse=v.nivel_interesse,
                notas_estruturadas=v.notas_estruturadas,
                objection_names=obj_names,
            )

            responses.append(
                cls._build_visit_response(v, v.property, v.consultor, obj_responses, wa_text, wa_link)
            )

        return responses

    @classmethod
    def mark_feedback_sent(
        cls,
        db: Session,
        agencia_id: int,
        visit_id: int,
        user: User,
    ) -> VisitResponse:
        """Marca que o feedback ao proprietário foi enviado via WhatsApp."""
        visit = (
            db.query(Visit)
            .filter(Visit.id == visit_id, Visit.agencia_id == agencia_id)
            .first()
        )
        if not visit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Visita não encontrada.",
            )

        if user.role != "diretor" and visit.consultor_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sem permissão para alterar esta visita.",
            )

        visit.feedback_enviado_proprietario = True
        db.commit()
        db.refresh(visit)

        return cls.get_visit_by_id(db, agencia_id, visit_id, user)

    @staticmethod
    def _build_visit_response(
        visit: Visit,
        property_obj: Property,
        consultor_obj: User,
        objections: List[VisitObjectionResponse],
        wa_text: str,
        wa_link: str,
    ) -> VisitResponse:
        """Constrói o objeto Pydantic de resposta com resumo de entidades."""
        return VisitResponse(
            id=visit.id,
            agencia_id=visit.agencia_id,
            property_id=visit.property_id,
            consultor_id=visit.consultor_id,
            data_visita=visit.data_visita,
            cliente_nome=visit.cliente_nome,
            cliente_telefone=visit.cliente_telefone,
            audio_duracao_segundos=visit.audio_duracao_segundos,
            transcricao=visit.transcricao,
            notas_estruturadas=visit.notas_estruturadas,
            nivel_interesse=visit.nivel_interesse,
            feedback_enviado_proprietario=visit.feedback_enviado_proprietario,
            created_at=visit.created_at,
            updated_at=visit.updated_at,
            property={
                "id": property_obj.id,
                "titulo": property_obj.titulo,
                "tipologia": property_obj.tipologia,
                "preco": property_obj.preco,
                "nome_proprietario": property_obj.nome_proprietario,
                "telefone_proprietario": property_obj.telefone_proprietario,
            } if property_obj else None,
            consultor={
                "id": consultor_obj.id,
                "nome": consultor_obj.nome,
                "email": consultor_obj.email,
            } if consultor_obj else None,
            objections=objections,
            whatsapp_feedback_text=wa_text,
            whatsapp_deep_link=wa_link,
        )
