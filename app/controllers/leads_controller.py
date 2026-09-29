"""
Controlador HTTP REST para Captação e Angariação de Imóveis - Fecho (fecho.pt).
Conforme FSD (Seção 6):
- Listagem e filtros de oportunidades de fontes abertas (e-leiloes.pt e OLX);
- Estatísticas agregadas de captação para o Backoffice;
- Conversão em 1 clique de oportunidade em imóvel ativo da carteira;
- Extração direta via URL pública do anúncio;
- Registro e bloqueio de oposição formal de RGPD.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database.connection import get_db
from app.dependencies import get_current_user, require_consultor, require_diretor
from app.models.lead import LeadAngariacao
from app.models.property import Property
from app.models.user import User
from app.schemas.lead_schema import (
    LeadConvertRequest,
    LeadCreate,
    LeadExtractUrlRequest,
    LeadListResponse,
    LeadOposicaoRequest,
    LeadResponse,
    LeadScanRequest,
    LeadStatsResponse,
    LeadStatusUpdate,
)
from app.schemas.property_schema import PropertyResponse
from app.services.lead_service import LeadService

router = APIRouter(prefix="/leads", tags=["Captação & Angariação"])


def _format_lead_response(lead: LeadAngariacao) -> LeadResponse:
    """Converte a entidade SQLAlchemy LeadAngariacao em schema Pydantic LeadResponse."""
    return LeadResponse(
        id=lead.id,
        agencia_id=lead.agencia_id,
        consultor_atribuido_id=lead.consultor_atribuido_id,
        consultor_nome=lead.consultor_atribuido.nome if lead.consultor_atribuido else None,
        fonte=lead.fonte,
        referencia_externa=lead.referencia_externa,
        url_origem=lead.url_origem,
        titulo=lead.titulo,
        descricao=lead.descricao,
        tipologia=lead.tipologia,
        preco_solicitado=lead.preco_solicitado,
        valor_minimo_abertura=lead.valor_minimo_abertura,
        distrito=lead.distrito,
        concelho=lead.concelho,
        freguesia=lead.freguesia,
        morada_aproximada=lead.morada_aproximada,
        nome_contacto=lead.nome_contacto,
        telefone_contacto=lead.telefone_contacto,
        tipo_anunciante=lead.tipo_anunciante,
        status=lead.status,
        imovel_convertido_id=lead.imovel_convertido_id,
        data_limite_leilao=lead.data_limite_leilao,
        notas_prospeccao=lead.notas_prospeccao,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
    )


def _format_property_response(prop: Property) -> PropertyResponse:
    """Converte o imóvel criado na conversão em schema Pydantic PropertyResponse."""
    return PropertyResponse(
        id=prop.id,
        agencia_id=prop.agencia_id,
        consultor_id=prop.consultor_id,
        consultor_nome=prop.consultor.nome if prop.consultor else None,
        titulo=prop.titulo,
        descricao=prop.descricao,
        tipologia=prop.tipologia,
        preco=prop.preco,
        morada=prop.morada,
        concelho=prop.concelho,
        distrito=prop.distrito,
        regiao_fiscal=prop.regiao_fiscal,
        area_bruta=prop.area_bruta,
        status=prop.status,
        nome_proprietario=prop.nome_proprietario,
        telefone_proprietario=prop.telefone_proprietario,
        nome_comprador=prop.nome_comprador,
        telefone_comprador=prop.telefone_comprador,
        data_escritura=prop.data_escritura,
        created_at=prop.created_at,
        updated_at=prop.updated_at,
    )


@router.get("", response_model=LeadListResponse, summary="Listar oportunidades de captação")
def list_leads(
    fonte: Optional[str] = Query(None, description="Filtrar por fonte: e-leiloes, olx, manual"),
    status_lead: Optional[str] = Query(None, alias="status", description="Filtrar por status"),
    concelho: Optional[str] = Query(None, description="Filtrar por concelho"),
    tipologia: Optional[str] = Query(None, description="Filtrar por tipologia (T1, T2, T3, Moradia)"),
    consultor_id: Optional[int] = Query(None, description="Filtrar por consultor atribuído"),
    busca: Optional[str] = Query(None, description="Busca textual em título, concelho e referência"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_consultor),
    db: Session = Depends(get_db),
):
    """Retorna listagem paginada das oportunidades com isolamento de agência."""
    total, items = LeadService.listar_leads(
        agencia_id=current_user.agencia_id,
        fonte=fonte,
        status=status_lead,
        concelho=concelho,
        tipologia=tipologia,
        consultor_id=consultor_id,
        busca=busca,
        skip=skip,
        limit=limit,
        db=db,
    )
    return LeadListResponse(total=total, items=[_format_lead_response(l) for l in items])


@router.get("/stats", response_model=LeadStatsResponse, summary="Métricas de captação para Backoffice")
def get_lead_stats(
    current_user: User = Depends(require_consultor),
    db: Session = Depends(get_db),
):
    """Calcula indicadores consolidados do módulo de angariação para a agência."""
    return LeadService.obter_estatisticas(agencia_id=current_user.agencia_id, db=db)


@router.get("/{lead_id}", response_model=LeadResponse, summary="Detalhes da oportunidade")
def get_lead_detail(
    lead_id: int,
    current_user: User = Depends(require_consultor),
    db: Session = Depends(get_db),
):
    """Retorna dados completos de uma oportunidade com validação multi-tenant."""
    lead = LeadService.obter_lead(lead_id=lead_id, agencia_id=current_user.agencia_id, db=db)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oportunidade não encontrada.")
    return _format_lead_response(lead)


@router.post("/manual", response_model=LeadResponse, status_code=status.HTTP_201_CREATED, summary="Criar oportunidade manual")
def create_manual_lead(
    payload: LeadCreate,
    current_user: User = Depends(require_consultor),
    db: Session = Depends(get_db),
):
    """Registra manualmente um imóvel particular ou oportunidade identificado pela equipe."""
    try:
        lead = LeadService.criar_lead_manual(
            agencia_id=current_user.agencia_id,
            payload=payload,
            db=db,
        )
        return _format_lead_response(lead)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/extrair-url", response_model=LeadResponse, status_code=status.HTTP_201_CREATED, summary="Captura rápida via link")
def extract_from_url(
    payload: LeadExtractUrlRequest,
    current_user: User = Depends(require_consultor),
    db: Session = Depends(get_db),
):
    """Extrai e registra automaticamente a oportunidade a partir da URL colada."""
    try:
        lead = LeadService.extrair_por_url(
            agencia_id=current_user.agencia_id,
            url=payload.url,
            consultor_id=current_user.id if current_user.role == "consultor" else None,
            db=db,
        )
        return _format_lead_response(lead)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/varredura", summary="Disparar varredura de fontes abertas")
def trigger_scan(
    payload: Optional[LeadScanRequest] = None,
    current_user: User = Depends(require_consultor),
    db: Session = Depends(get_db),
):
    """
    Executa varredura nas fontes abertas (e-leilões e OLX particulares) para a zona da agência.
    """
    concelho = payload.concelho if payload else None
    distrito = payload.distrito if payload else None
    fonte = payload.fonte if payload else None

    total_novos = LeadService.executar_varredura(
        agencia_id=current_user.agencia_id,
        concelho=concelho,
        distrito=distrito,
        fonte=fonte,
        db=db,
    )
    return {
        "status": "sucesso",
        "novas_oportunidades_captadas": total_novos,
        "mensagem": f"Varredura concluída com sucesso. {total_novos} oportunidades processadas na zona da agência.",
    }


@router.post("/{lead_id}/converter", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED, summary="Conversão em 1 clique")
def convert_lead_to_property(
    lead_id: int,
    payload: Optional[LeadConvertRequest] = None,
    current_user: User = Depends(require_consultor),
    db: Session = Depends(get_db),
):
    """
    Ação em 1 Clique:
    Converte a oportunidade em imóvel oficial da carteira com status 'Ativo',
    atribuindo ao consultor logado (ou consultor especificado pelo diretor).
    """
    consultor_id = current_user.id
    if current_user.role == "diretor" and payload and payload.consultor_id:
        consultor_id = payload.consultor_id

    regiao_fiscal = payload.regiao_fiscal if payload else "continente"

    try:
        imovel_criado = LeadService.converter_em_imovel(
            lead_id=lead_id,
            consultor_id=consultor_id,
            agencia_id=current_user.agencia_id,
            regiao_fiscal=regiao_fiscal,
            db=db,
        )
        return _format_property_response(imovel_criado)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.patch("/{lead_id}/status", response_model=LeadResponse, summary="Atualizar status da prospecção")
def update_lead_status(
    lead_id: int,
    payload: LeadStatusUpdate,
    current_user: User = Depends(require_consultor),
    db: Session = Depends(get_db),
):
    """Atualiza o status de acompanhamento da prospecção comercial."""
    try:
        lead = LeadService.atualizar_status(
            lead_id=lead_id,
            agencia_id=current_user.agencia_id,
            novo_status=payload.status,
            notas=payload.notas_prospeccao,
            db=db,
        )
        return _format_lead_response(lead)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/{lead_id}/oposicao-rgpd", response_model=LeadResponse, summary="Registrar oposição formal RGPD")
def register_rgpd_objection(
    lead_id: int,
    payload: Optional[LeadOposicaoRequest] = None,
    current_user: User = Depends(require_consultor),
    db: Session = Depends(get_db),
):
    """
    Registra a oposição do titular conforme Art. 21 do RGPD:
    bloqueia o telemóvel na agência e anonimiza os dados pessoais da lead.
    """
    motivo = payload.motivo if payload else None
    try:
        lead = LeadService.aplicar_oposicao_rgpd(
            lead_id=lead_id,
            agencia_id=current_user.agencia_id,
            user_id=current_user.id,
            motivo=motivo,
            db=db,
        )
        return _format_lead_response(lead)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
