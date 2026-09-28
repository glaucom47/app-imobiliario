"""
Endpoints REST para Geração de Conteúdo e Scripts de Vídeo Curto - Fecho (fecho.pt).
Conforme FSD e DESIGN:
- Geração de roteiros em 3 blocos (Gancho, 2 Destaques e CTA).
- Objetivos: Angariação, Baixa de Preço e Open House.
- Isolamento estrito por agencia_id.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from database.connection import get_db
from app.dependencies import require_consultor
from app.models.user import User
from app.schemas.script_schema import (
    ScriptObjectiveEnum,
    ScriptObjectiveInfo,
    ScriptGenerateRequest,
    ScriptResponse,
)
from app.services.script_service import ScriptService

router = APIRouter(prefix="/scripts", tags=["Scripts de Vídeo"])


@router.get(
    "/objectives",
    response_model=List[ScriptObjectiveInfo],
    summary="Listar objetivos comerciais disponíveis para roteiros"
)
async def list_script_objectives(
    current_user: User = Depends(require_consultor)
):
    """
    Retorna os objetivos comerciais suportados pelo Fecho:
    - Angariação / Novo Imóvel
    - Baixa de Preço / Oportunidade
    - Open House / Portas Abertas
    """
    return ScriptService.get_objectives()


@router.post(
    "/generate",
    response_model=ScriptResponse,
    status_code=status.HTTP_200_OK,
    summary="Gerar roteiro de marketing em 3 blocos para vídeo curto"
)
async def generate_script(
    payload: ScriptGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_consultor)
):
    """
    Gera um roteiro em 3 blocos:
    1. Gancho (Hook): 0 a 5 segundos;
    2. Dois Destaques: 5 a 25 segundos;
    3. Chamada para Ação (CTA): 25 a 35 segundos.
    
    Respeita isolamento de agência (agencia_id) e formata cadência para o Teleprompter.
    """
    return ScriptService.generate_script(db=db, request=payload, current_user=current_user)


@router.get(
    "/property/{property_id}",
    response_model=ScriptResponse,
    summary="Obter sugestão rápida de roteiro para um imóvel específico"
)
async def get_property_script(
    property_id: int,
    objetivo: Optional[ScriptObjectiveEnum] = Query(
        default=ScriptObjectiveEnum.ANGARIACAO,
        description="Objetivo do vídeo: 'angariacao', 'baixa_preco' ou 'open_house'"
    ),
    tom: Optional[str] = Query(default="sofisticado", description="Tom do roteiro"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_consultor)
):
    """
    Gera rapidamente um roteiro com parâmetros padrão para o imóvel em foco.
    """
    req = ScriptGenerateRequest(
        property_id=property_id,
        objetivo=objetivo or ScriptObjectiveEnum.ANGARIACAO,
        tom=tom
    )
    return ScriptService.generate_script(db=db, request=req, current_user=current_user)
