"""
Integração Stripe - Fecho (fecho.pt).

- Checkout alojado pelo Stripe (os dados de cartão nunca passam pelo Fecho);
- Customer Portal para gerir/cancelar a subscrição;
- Webhook com verificação obrigatória de assinatura (STRIPE_WEBHOOK_SECRET).

O agencia_id associado a cada sessão é definido pelo servidor (a partir do JWT),
nunca recebido do cliente. Nenhum dado de pagamento é registado em log.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import stripe
from sqlalchemy.orm import Session

from config.config import settings
from app.models.log import Log
from app.models.tenant import Tenant
from app.models.user import User

logger = logging.getLogger(__name__)

# Mapeamento do estado da subscrição Stripe para o estado interno da agência
_MAPA_ESTADOS = {
    "active": "ativo",
    "trialing": "ativo",
    "past_due": "pendente",
    "incomplete": "pendente",
    "unpaid": "suspenso",
    "incomplete_expired": "suspenso",
    "paused": "suspenso",
    "canceled": "cancelado",
}


class StripeNaoConfigurado(RuntimeError):
    pass


def configurado() -> bool:
    return bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_PRICE_MENSAL and settings.STRIPE_PRICE_ANUAL)


def _cliente():
    if not configurado():
        raise StripeNaoConfigurado("Pagamento online ainda não disponível.")
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def criar_checkout(db: Session, user: User, periodo: str) -> str:
    """Cria uma Checkout Session de subscrição e devolve o URL do Stripe."""
    s = _cliente()
    tenant: Tenant = user.tenant
    price = settings.STRIPE_PRICE_ANUAL if periodo == "anual" else settings.STRIPE_PRICE_MENSAL
    item = {"price": price, "quantity": 1}
    if settings.STRIPE_TAX_RATE_ID:
        item["tax_rates"] = [settings.STRIPE_TAX_RATE_ID]

    meta = {"agencia_id": str(tenant.id), "periodo": periodo}
    params = dict(
        mode="subscription",
        line_items=[item],
        client_reference_id=str(tenant.id),
        metadata=meta,
        subscription_data={"metadata": meta},
        success_url=f"{settings.APP_BASE_URL}/backoffice?pagamento=sucesso",
        cancel_url=f"{settings.APP_BASE_URL}/backoffice?pagamento=cancelado",
        locale="pt",
        billing_address_collection="required",
        tax_id_collection={"enabled": True},
        allow_promotion_codes=True,
    )
    if tenant.stripe_customer_id:
        params["customer"] = tenant.stripe_customer_id
        params["customer_update"] = {"name": "auto", "address": "auto"}
    else:
        params["customer_email"] = user.email

    session = s.checkout.Session.create(**params)
    _log(db, tenant.id, user.id, "BILLING_CHECKOUT", f"periodo={periodo}")
    db.commit()
    return session["url"]


def criar_portal(db: Session, user: User) -> str:
    s = _cliente()
    tenant: Tenant = user.tenant
    if not tenant.stripe_customer_id:
        raise ValueError("Ainda não existe subscrição associada a esta agência.")
    portal = s.billing_portal.Session.create(
        customer=tenant.stripe_customer_id,
        return_url=f"{settings.APP_BASE_URL}/backoffice",
    )
    return portal["url"]


def construir_evento(payload: bytes, assinatura: Optional[str]):
    """Valida a assinatura do webhook. Lança ValueError se inválida."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise StripeNaoConfigurado("Webhook Stripe não configurado.")
    if not assinatura:
        raise ValueError("Assinatura Stripe ausente.")
    try:
        stripe.Webhook.construct_event(payload, assinatura, settings.STRIPE_WEBHOOK_SECRET)
    except (stripe.SignatureVerificationError, ValueError) as err:
        raise ValueError("Assinatura Stripe inválida.") from err
    # Assinatura válida: trabalha com dicionários simples (independente da versão do SDK)
    return json.loads(payload)


def _ts(valor) -> Optional[datetime]:
    return datetime.fromtimestamp(int(valor), tz=timezone.utc) if valor else None


def _tenant_por_customer(db: Session, customer_id: Optional[str]) -> Optional[Tenant]:
    if not customer_id:
        return None
    return db.query(Tenant).filter(Tenant.stripe_customer_id == customer_id).first()


def _log(db: Session, agencia_id: int, user_id: Optional[int], acao: str, detalhes: str) -> None:
    db.add(Log(agencia_id=agencia_id, user_id=user_id, acao=acao, entidade="tenant",
               entidade_id=agencia_id, detalhes=detalhes))


def processar_evento(db: Session, evento) -> bool:
    """
    Aplica o evento ao estado da agência. As operações são idempotentes
    (definem estado absoluto), pelo que reenvios do Stripe não duplicam efeitos.
    Devolve True se o evento alterou alguma agência.
    """
    tipo = evento["type"]
    obj = evento["data"]["object"]
    tenant: Optional[Tenant] = None

    if tipo == "checkout.session.completed":
        ref = obj.get("client_reference_id") or (obj.get("metadata") or {}).get("agencia_id")
        if not ref or not str(ref).isdigit():
            return False
        tenant = db.query(Tenant).filter(Tenant.id == int(ref)).first()
        if tenant is None:
            return False
        tenant.stripe_customer_id = obj.get("customer") or tenant.stripe_customer_id
        tenant.stripe_subscription_id = obj.get("subscription") or tenant.stripe_subscription_id
        periodo = (obj.get("metadata") or {}).get("periodo")
        if periodo in ("mensal", "anual"):
            tenant.plano_periodo = periodo
        tenant.plano_status = "ativo"

    elif tipo == "invoice.paid":
        tenant = _tenant_por_customer(db, obj.get("customer"))
        if tenant is None:
            return False
        tenant.plano_status = "ativo"
        linhas = (obj.get("lines") or {}).get("data") or []
        if linhas:
            tenant.subscricao_valida_ate = _ts((linhas[0].get("period") or {}).get("end"))

    elif tipo == "invoice.payment_failed":
        tenant = _tenant_por_customer(db, obj.get("customer"))
        if tenant is None:
            return False
        if tenant.plano_status == "ativo":
            tenant.plano_status = "pendente"

    elif tipo in ("customer.subscription.updated", "customer.subscription.created"):
        tenant = _tenant_por_customer(db, obj.get("customer"))
        if tenant is None:
            return False
        tenant.stripe_subscription_id = obj.get("id") or tenant.stripe_subscription_id
        novo = _MAPA_ESTADOS.get(obj.get("status"))
        if novo:
            tenant.plano_status = novo
        if obj.get("current_period_end"):
            tenant.subscricao_valida_ate = _ts(obj.get("current_period_end"))

    elif tipo == "customer.subscription.deleted":
        tenant = _tenant_por_customer(db, obj.get("customer"))
        if tenant is None:
            return False
        tenant.plano_status = "cancelado"

    else:
        return False

    _log(db, tenant.id, None, "BILLING_WEBHOOK", f"evento={tipo} estado={tenant.plano_status}")
    db.commit()
    return True
