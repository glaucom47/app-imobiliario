"""
Controlador de Faturação (Billing) - Fecho (fecho.pt).

- GET  /billing/status   : estado do trial/subscrição (qualquer utilizador autenticado);
- POST /billing/checkout : inicia pagamento no Stripe (apenas diretor);
- POST /billing/portal   : gerir/cancelar subscrição no Stripe (apenas diretor);
- POST /billing/webhook  : eventos do Stripe (público, assinatura verificada).

O agencia_id vem exclusivamente do token JWT validado.
"""
from datetime import datetime
from typing import Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from app.dependencies import get_current_user, require_diretor
from app.models.user import User
from app.services import billing_service, stripe_service

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
    pagamento_online_disponivel: bool = False
    tem_subscricao: bool = False


class CheckoutRequest(BaseModel):
    periodo: Literal["mensal", "anual"] = "mensal"


class UrlResponse(BaseModel):
    url: str


@router.get("/status", response_model=BillingStatusResponse, summary="Estado do período de teste e da subscrição")
def billing_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dados = billing_service.estado(db, current_user.tenant)
    dados["pagamento_online_disponivel"] = stripe_service.configurado()
    dados["tem_subscricao"] = bool(current_user.tenant.stripe_customer_id)
    return dados


@router.post("/checkout", response_model=UrlResponse, summary="Iniciar subscrição (Stripe Checkout)")
def billing_checkout(
    payload: CheckoutRequest,
    current_user: User = Depends(require_diretor),
    db: Session = Depends(get_db),
):
    try:
        return {"url": stripe_service.criar_checkout(db, current_user, payload.periodo)}
    except stripe_service.StripeNaoConfigurado as err:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(err))


@router.post("/portal", response_model=UrlResponse, summary="Gerir subscrição (Stripe Customer Portal)")
def billing_portal(current_user: User = Depends(require_diretor), db: Session = Depends(get_db)):
    try:
        return {"url": stripe_service.criar_portal(db, current_user)}
    except stripe_service.StripeNaoConfigurado as err:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.post("/webhook", include_in_schema=False)
async def billing_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    try:
        evento = stripe_service.construir_evento(payload, request.headers.get("stripe-signature"))
    except stripe_service.StripeNaoConfigurado as err:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    stripe_service.processar_evento(db, evento)
    return {"recebido": True}
