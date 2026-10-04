"""
Controlador HTTP REST para o Módulo de Direção Comercial & Gestão Ativa de Equipa (FSD Seção 8).
Endpoints restritos à Direção Comercial (RBAC: 'diretor') com isolamento estrito por agencia_id:
1. GET /api/v1/backoffice/commercial-dashboard: KPIs consolidados, variações homólogas e pipeline ponderado
2. GET /api/v1/backoffice/sales-funnel: Funil comercial de 7 etapas com taxas automáticas de conversão
3. GET /api/v1/backoffice/consultores-performance: Tabela da equipa com semáforo de trajetória
4. GET /api/v1/backoffice/consultor/{id}/performance: Ficha individual detalhada em 4 blocos
5. POST /api/v1/backoffice/meetings/start: Inicialização de reunião semanal com atividade e pendências
6. POST /api/v1/backoffice/meetings/save: Gravação de reunião semanal com snapshot congelado e compromissos
7. GET /api/v1/backoffice/consultor/{id}/meetings: Histórico cronológico das sessões semanais
8. Endpoints de gestão de metas (Goals) e oportunidades de carteira (Pipeline Deals)
"""
from typing import List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database.connection import get_db
from app.dependencies import require_diretor
from app.models.user import User
from app.schemas.commercial_schema import (
    CommercialDashboardResponse,
    ConsultoresPerformanceResponse,
    ConsultorIndividualPerformanceResponse,
    GoalCreate,
    GoalResponse,
    MeetingSaveRequest,
    MeetingStartResponse,
    PipelineDealCreate,
    PipelineDealResponse,
    PipelineDealUpdate,
    SalesFunnelResponse,
    WeeklyMeetingResponse,
)
from app.services.commercial_service import CommercialService
from app.services.meeting_service import MeetingService

router = APIRouter(prefix="/backoffice", tags=["Direção Comercial & Gestão de Equipa"])


# ==========================================
# 1. Dashboard da Direção Comercial
# ==========================================

@router.get(
    "/commercial-dashboard",
    response_model=CommercialDashboardResponse,
    summary="Dashboard da Direção Comercial",
    description="Retorna KPIs consolidados da agência ou específicos de um consultor com variações homólogas e pipeline bruto/ponderado.",
)
def get_commercial_dashboard(
    filtro: str = Query(
        "este_mes",
        pattern="^(7_dias|30_dias|90_dias|este_mes|mes_anterior|historico)$",
        description="Filtro temporal (7_dias, 30_dias, 90_dias, este_mes, mes_anterior, historico)",
    ),
    consultor_id: Optional[int] = Query(None, description="Identificador do consultor para visão individual de KPIs"),
    current_user: User = Depends(require_diretor),
    db: Session = Depends(get_db),
):
    return CommercialService.get_dashboard(
        db,
        agencia_id=current_user.agencia_id,
        filtro=filtro,
        consultor_id=consultor_id,
    )


# ==========================================
# 2. Funil Comercial da Loja e Individual
# ==========================================

@router.get(
    "/sales-funnel",
    response_model=SalesFunnelResponse,
    summary="Funil Comercial da Loja ou Individual",
    description="Retorna as 7 etapas do funil de vendas (Contactos até Escrituras) com cálculo automático das taxas de conversão sequenciais.",
)
def get_sales_funnel(
    filtro: str = Query(
        "este_mes",
        pattern="^(7_dias|30_dias|90_dias|este_mes|mes_anterior|historico)$",
        description="Filtro temporal de análise",
    ),
    consultor_id: Optional[int] = Query(None, description="Filtro opcional para visualizar o funil de um consultor específico"),
    current_user: User = Depends(require_diretor),
    db: Session = Depends(get_db),
):
    return CommercialService.get_sales_funnel(
        db,
        agencia_id=current_user.agencia_id,
        filtro=filtro,
        consultor_id=consultor_id,
    )


# ==========================================
# 3. Tabela de Performance & Semáforo
# ==========================================

@router.get(
    "/consultores-performance",
    response_model=ConsultoresPerformanceResponse,
    summary="Tabela de Performance da Equipa com Semáforo",
    description="Retorna a listagem comparativa dos consultores com metas, faturação realizada, pipeline e semáforo de trajetória (Verde, Amarelo, Vermelho).",
)
def get_consultores_performance(
    ano: Optional[int] = Query(None, ge=2020, le=2050, description="Ano de análise (padrão: ano corrente)"),
    mes: Optional[int] = Query(None, ge=1, le=12, description="Mês de análise (1 a 12, padrão: mês corrente)"),
    current_user: User = Depends(require_diretor),
    db: Session = Depends(get_db),
):
    return CommercialService.get_consultores_performance(
        db,
        agencia_id=current_user.agencia_id,
        ano=ano,
        mes=mes,
    )


# ==========================================
# 4. Ficha Individual do Consultor (4 Blocos)
# ==========================================

@router.get(
    "/consultor/{consultor_id}/performance",
    response_model=ConsultorIndividualPerformanceResponse,
    summary="Ficha Individual de Performance do Consultor",
    description="Retorna a visão analítica 360 do consultor estruturada em 4 blocos: Objetivos e projeção, Atividade, Funil individual e Histórico semanal.",
)
def get_consultor_performance(
    consultor_id: int,
    ano: Optional[int] = Query(None, ge=2020, le=2050),
    mes: Optional[int] = Query(None, ge=1, le=12),
    current_user: User = Depends(require_diretor),
    db: Session = Depends(get_db),
):
    return CommercialService.get_consultor_individual_performance(
        db,
        agencia_id=current_user.agencia_id,
        consultor_id=consultor_id,
        ano=ano,
        mes=mes,
    )


# ==========================================
# 5. Reunião Semanal Automatizada
# ==========================================

@router.post(
    "/meetings/start",
    response_model=MeetingStartResponse,
    summary="Inicializar Sessão Semanal com Consultor",
    description="Puxa automaticamente dados de visitas recentes, transcrições/notas de voz, compromissos anteriores pendentes e negócios em carteira.",
)
def start_weekly_meeting(
    consultor_id: int = Query(..., description="ID do consultor participante"),
    current_user: User = Depends(require_diretor),
    db: Session = Depends(get_db),
):
    return MeetingService.start_meeting(
        db,
        agencia_id=current_user.agencia_id,
        diretor_id=current_user.id,
        consultor_id=consultor_id,
    )


@router.post(
    "/meetings/save",
    response_model=WeeklyMeetingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Gravar Sessão Semanal e Congelar Snapshot",
    description="Grava o diagnóstico qualitativo do diretor, congela as métricas da semana e cadastra os novos compromissos acordados.",
)
def save_weekly_meeting(
    payload: MeetingSaveRequest,
    current_user: User = Depends(require_diretor),
    db: Session = Depends(get_db),
):
    return MeetingService.save_meeting(
        db,
        agencia_id=current_user.agencia_id,
        diretor_id=current_user.id,
        payload=payload,
    )


@router.get(
    "/consultor/{consultor_id}/meetings",
    response_model=List[WeeklyMeetingResponse],
    summary="Histórico de Reuniões Semanais do Consultor",
    description="Retorna o histórico cronológico de reuniões e evolução de compromissos de um consultor ao longo do tempo.",
)
def list_consultor_meetings(
    consultor_id: int,
    current_user: User = Depends(require_diretor),
    db: Session = Depends(get_db),
):
    return MeetingService.list_consultor_meetings(
        db,
        agencia_id=current_user.agencia_id,
        consultor_id=consultor_id,
    )


# ==========================================
# 6. Gestão de Metas Comerciais (Goals)
# ==========================================

@router.get(
    "/goals",
    response_model=List[GoalResponse],
    summary="Listar Metas Comerciais da Agência",
    description="Retorna a lista de metas comerciais mensais com filtros opcionais por ano, mês e consultor.",
)
def list_goals(
    ano: Optional[int] = Query(None, ge=2020, le=2050),
    mes: Optional[int] = Query(None, ge=1, le=12),
    consultor_id: Optional[int] = Query(None),
    current_user: User = Depends(require_diretor),
    db: Session = Depends(get_db),
):
    return CommercialService.list_goals(
        db,
        agencia_id=current_user.agencia_id,
        ano=ano,
        mes=mes,
        consultor_id=consultor_id,
    )


@router.post(
    "/goals",
    response_model=GoalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar ou Atualizar Meta Comercial",
    description="Cria ou atualiza a meta comercial mensal de um consultor para um determinado mês e ano.",
)
def set_goal(
    payload: GoalCreate,
    current_user: User = Depends(require_diretor),
    db: Session = Depends(get_db),
):
    return CommercialService.create_or_update_goal(
        db,
        agencia_id=current_user.agencia_id,
        payload=payload,
    )


# ==========================================
# 7. Gestão de Oportunidades do Pipeline
# ==========================================

@router.get(
    "/pipeline",
    response_model=List[PipelineDealResponse],
    summary="Listar Oportunidades do Pipeline",
    description="Retorna as oportunidades comerciais em carteira com filtros por consultor, fase e status ativo.",
)
def list_pipeline_deals(
    consultor_id: Optional[int] = Query(None),
    fase: Optional[str] = Query(None),
    ativo_apenas: bool = Query(True),
    current_user: User = Depends(require_diretor),
    db: Session = Depends(get_db),
):
    return CommercialService.list_pipeline_deals(
        db,
        agencia_id=current_user.agencia_id,
        consultor_id=consultor_id,
        fase=fase,
        ativo_apenas=ativo_apenas,
    )


@router.post(
    "/pipeline",
    response_model=PipelineDealResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar Oportunidade no Pipeline",
    description="Adiciona uma nova oportunidade comercial em carteira vinculada a um consultor e opcionalmente a um imóvel.",
)
def create_pipeline_deal(
    payload: PipelineDealCreate,
    current_user: User = Depends(require_diretor),
    db: Session = Depends(get_db),
):
    return CommercialService.create_pipeline_deal(
        db,
        agencia_id=current_user.agencia_id,
        payload=payload,
        user_id=current_user.id,
    )


@router.put(
    "/pipeline/{deal_id}",
    response_model=PipelineDealResponse,
    summary="Atualizar Oportunidade no Pipeline",
    description="Atualiza fase, probabilidade, valores ou ações de uma oportunidade comercial existente.",
)
def update_pipeline_deal(
    deal_id: int,
    payload: PipelineDealUpdate,
    current_user: User = Depends(require_diretor),
    db: Session = Depends(get_db),
):
    return CommercialService.update_pipeline_deal(
        db,
        agencia_id=current_user.agencia_id,
        deal_id=deal_id,
        payload=payload,
    )


@router.delete(
    "/pipeline/{deal_id}",
    summary="Remover Oportunidade do Pipeline",
    description="Remove uma oportunidade do pipeline da agência garantindo isolamento multi-tenant.",
)
def delete_pipeline_deal(
    deal_id: int,
    current_user: User = Depends(require_diretor),
    db: Session = Depends(get_db),
):
    return CommercialService.delete_pipeline_deal(
        db,
        agencia_id=current_user.agencia_id,
        deal_id=deal_id,
    )
