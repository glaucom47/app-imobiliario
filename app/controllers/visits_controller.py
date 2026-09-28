"""
Controlador REST para Visitas, Feedback por Voz e Objeções - Fecho (fecho.pt).

Endpoints:
- POST /api/v1/visits/audio : Processamento e estruturação automática de notas de voz (Speech/NLP);
- POST /api/v1/visits       : Criação de visita com tags de objeções e geração de link WhatsApp;
- GET  /api/v1/visits       : Listagem com filtros por imóvel, consultor e paginação;
- GET  /api/v1/visits/tags  : Catálogo corporativo de tags de objeção ativas da agência;
- GET  /api/v1/visits/{id}  : Detalhes de uma visita específica;
- PATCH /api/v1/visits/{id}/feedback-sent : Atualização da flag de envio de feedback ao proprietário.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_tenant, get_db, require_consultor
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.visit_schema import (
    AudioProcessRequest,
    AudioProcessResponse,
    ObjectionTagResponse,
    VisitCreate,
    VisitListResponse,
    VisitResponse,
)
from app.services.visit_service import VisitService

router = APIRouter(prefix="/visits", tags=["Visitas & Feedback por Voz"])


@router.get("/tags", response_model=List[ObjectionTagResponse])
async def list_objection_tags(
    db: Session = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(require_consultor),
):
    """
    Retorna o catálogo de tags de objeções padronizadas da agência.
    Usado no ecrã de revisão (Human-in-the-Loop) para seleção rápida de chips táteis.
    """
    tags = VisitService.get_agency_objection_tags(db=db, agencia_id=current_tenant.id)
    return tags


@router.post("/audio", response_model=AudioProcessResponse)
async def process_visit_audio(
    request: AudioProcessRequest,
    db: Session = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(require_consultor),
):
    """
    Processa nota de voz ou transcrição prévia de até 30 segundos.
    Extrai o nível de interesse estimado (1 a 5), identifica objeções contra
    o catálogo da agência e organiza notas estruturadas para revisão humana.
    """
    result = VisitService.process_audio_or_notes(
        db=db,
        agencia_id=current_tenant.id,
        request=request,
    )
    return result


@router.post("", response_model=VisitResponse, status_code=status.HTTP_201_CREATED)
async def create_visit(
    data: VisitCreate,
    db: Session = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(require_consultor),
):
    """
    Registra uma nova visita após a validação no ecrã Human-in-the-Loop.
    Vincula obrigatoriamente o imóvel ativo, o consultor autenticado e as tags de objeção.
    Retorna o texto refinado de feedback e o Deep Link para WhatsApp do proprietário.
    """
    visit = VisitService.create_visit(
        db=db,
        agencia_id=current_tenant.id,
        user=current_user,
        data=data,
    )
    return visit


@router.get("", response_model=VisitListResponse)
async def list_visits(
    property_id: Optional[int] = Query(None, description="Filtrar por ID do imóvel"),
    consultor_id: Optional[int] = Query(None, description="Filtrar por ID do consultor (Direção)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(require_consultor),
):
    """
    Lista visitas da agência.
    Consultores visualizam apenas suas próprias visitas; Diretores visualizam de toda a agência.
    """
    visits = VisitService.list_visits(
        db=db,
        agencia_id=current_tenant.id,
        user=current_user,
        property_id=property_id,
        consultor_id=consultor_id,
        skip=skip,
        limit=limit,
    )
    return VisitListResponse(total=len(visits), visits=visits)


@router.get("/{visit_id}", response_model=VisitResponse)
async def get_visit_details(
    visit_id: int,
    db: Session = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(require_consultor),
):
    """
    Obtém detalhes completos de uma visita, incluindo objeções levantadas
    e link de WhatsApp para o proprietário.
    """
    return VisitService.get_visit_by_id(
        db=db,
        agencia_id=current_tenant.id,
        visit_id=visit_id,
        user=current_user,
    )


@router.patch("/{visit_id}/feedback-sent", response_model=VisitResponse)
async def mark_visit_feedback_sent(
    visit_id: int,
    db: Session = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(require_consultor),
):
    """
    Atualiza a visita confirmando que o feedback ao proprietário foi enviado pelo consultor.
    """
    return VisitService.mark_feedback_sent(
        db=db,
        agencia_id=current_tenant.id,
        visit_id=visit_id,
        user=current_user,
    )
