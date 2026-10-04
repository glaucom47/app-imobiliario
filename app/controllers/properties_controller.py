"""
Controller REST de Imóveis (Properties) - Fecho (fecho.pt).

Endpoints:
- GET  /api/v1/properties: Lista imóveis da agência com filtros (status, tipologia, consultor, busca);
- POST /api/v1/properties: Cria novo imóvel na carteira com status inicial 'Ativo';
- GET  /api/v1/properties/{id}: Detalhes de um imóvel;
- PUT  /api/v1/properties/{id}: Atualização cadastral de um imóvel;
- POST /api/v1/properties/{id}/transition: Transição na máquina de estados com validação dos 3 campos de fecho;
- DELETE /api/v1/properties/{id}: Exclusão de imóvel sem histórico de visitas.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from database.connection import get_db
from app.dependencies import get_current_user, require_consultor
from app.models.property import Property
from app.models.user import User
from app.schemas.property_schema import (
    PropertyCreate,
    PropertyListResponse,
    PropertyResponse,
    PropertyTransitionStatus,
    PropertyUpdate,
)
from app.schemas.market_study_schema import MarketStudyRequest, MarketStudyResponse
from app.services.property_service import PropertyService
from app.services.market_study_service import MarketStudyService
from app.services.ine_data import INEService

router = APIRouter(prefix="/properties", tags=["Imóveis & Carteira"])


def _format_property_response(prop: Property) -> PropertyResponse:
    """Converte a entidade SQLAlchemy Property em schema Pydantic PropertyResponse."""
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


@router.get("", response_model=PropertyListResponse, summary="Listar imóveis da agência")
async def list_properties(
    status: Optional[str] = Query(None, description="Filtrar por status: Ativo, Reservado, Vendido"),
    tipologia: Optional[str] = Query(None, description="Filtrar por tipologia (T0, T1, T2, T3, etc.)"),
    consultor_id: Optional[int] = Query(None, description="Filtrar por ID do consultor responsável"),
    busca: Optional[str] = Query(None, description="Termo de pesquisa (título, morada, concelho, proprietário)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_consultor),
):
    """
    Lista todos os imóveis da agência do usuário com isolamento multi-tenant rigoroso por agencia_id.
    """
    props, total = PropertyService.list_properties(
        db=db,
        agencia_id=current_user.agencia_id,
        status_filter=status,
        tipologia=tipologia,
        consultor_id=consultor_id,
        busca=busca,
        skip=skip,
        limit=limit,
    )
    return PropertyListResponse(
        total=total,
        properties=[_format_property_response(p) for p in props],
    )


@router.post("", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED, summary="Cadastrar novo imóvel")
async def create_property(
    property_in: PropertyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_consultor),
):
    """
    Cadastra um novo imóvel na carteira. O status inicial é sempre 'Ativo'.
    Consultores cadastram vinculados a si; Diretores podem atribuir a qualquer consultor da agência.
    """
    created_prop = PropertyService.create_property(
        db=db,
        property_in=property_in,
        current_user=current_user,
    )
    return _format_property_response(created_prop)


@router.get("/concelhos-ine", summary="Lista nacional de concelhos e medianas INE")
async def get_concelhos_ine(
    current_user: User = Depends(require_consultor),
):
    """
    Retorna a lista dos 308 Concelhos de Portugal com seus respectivos
    Distritos, Regiões Fiscais e Preços Medianos de Venda (€/m²) do INE.
    """
    return INEService.get_all_concelhos()


@router.post("/market-study", response_model=MarketStudyResponse, summary="Gerar Estudo de Mercado Inteligente (ACM)")
async def generate_market_study(
    request: MarketStudyRequest,
    current_user: User = Depends(require_consultor),
):
    """
    Gera Estudo de Mercado Comparativo (ACM) em menos de 1 minuto, integrando:
    1. Leitura e extração de dados da Caderneta Predial Urbana;
    2. Análise visual de acabamentos por fotos dos cómodos;
    3. Relato oral do consultor (até 30s) para calibragem ponderada (-20% a +25%);
    4. Estatísticas oficiais do INE dos 308 concelhos;
    5. Benchmarking e auditoria de convergência com Casafari e Alfredo AI.
    """
    result = await MarketStudyService.generate_market_study(
        request=request,
        current_user=current_user,
    )
    return result


@router.get("/{property_id}", response_model=PropertyResponse, summary="Obter detalhes do imóvel")
async def get_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_consultor),
):
    """
    Obtém os detalhes de um imóvel com garantia de isolamento multi-tenant por agencia_id.
    """
    prop = PropertyService.get_property_by_id(
        db=db,
        property_id=property_id,
        agencia_id=current_user.agencia_id,
    )
    return _format_property_response(prop)


@router.put("/{property_id}", response_model=PropertyResponse, summary="Atualizar dados cadastrais do imóvel")
async def update_property(
    property_id: int,
    property_update: PropertyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_consultor),
):
    """
    Atualiza as informações de cadastro do imóvel.
    Para alterar o status, deve ser utilizado o endpoint /transition.
    """
    updated_prop = PropertyService.update_property(
        db=db,
        property_id=property_id,
        property_update=property_update,
        current_user=current_user,
    )
    return _format_property_response(updated_prop)


@router.post("/{property_id}/transition", response_model=PropertyResponse, summary="Transitar status do imóvel na máquina de estados")
async def transition_property_status(
    property_id: int,
    transition_data: PropertyTransitionStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_consultor),
):
    """
    Aplica a transição na máquina de estados:
    - Ativo -> Reservado
    - Reservado -> Ativo
    - Ativo ou Reservado -> Vendido
    
    A transição para 'Vendido' exige obrigatoriamente:
    - Nome do Comprador (nome_comprador)
    - Telemóvel do Comprador (telefone_comprador)
    - Data da Escritura (data_escritura)
    
    Ao concretizar a venda, o comprador é automaticamente registrado na base de contactos (Esfera de Influência).
    """
    transitioned_prop = PropertyService.transition_status(
        db=db,
        property_id=property_id,
        transition_data=transition_data,
        current_user=current_user,
    )
    return _format_property_response(transitioned_prop)


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remover imóvel sem visitas")
async def delete_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_consultor),
):
    """
    Remove um imóvel da carteira, desde que não possua visitas ou feedbacks vinculados.
    """
    PropertyService.delete_property(
        db=db,
        property_id=property_id,
        current_user=current_user,
    )
    return None

