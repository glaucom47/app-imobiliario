"""
Controlador de Faturação (Billing) - Fecho (fecho.pt).

Fase A: consulta do estado do trial/subscrição da agência do utilizador autenticado.
O agencia_id vem exclusivamente do token JWT validado.
"""
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services import billing_service

router = APIRouter(prefix="/billing", tags=["Faturação"])


class BillingStatusResponse(BaseModel):
    plano_status: str
    escrita_permitida: bool
    trial_termina_em: Optional[datetime] = None
    dias_restantes_trial: Optional[int] = None
    subscricao_valida_ate: Optional[datetime] = None
    plano_periodo: Optional[str] = None
    utilizadores_contratados: int
    utilizadores_ativos: int
    precos: Dict[str, Dict[str, float]]


@router.get("/status", response_model=BillingStatusResponse, summary="Estado do período de teste e da subscrição")
def billing_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return billing_service.estado(db, current_user.tenant)
