"""
Serviço de Faturação (Billing) - Fecho (fecho.pt).

Fase A: período de teste (trial) de 7 dias e modo só leitura após expiração.
O estado é sempre calculado no servidor a partir da base de dados; o frontend apenas o apresenta.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.models.user import User

TRIAL_DIAS = 7
UTILIZADORES_INCLUIDOS = 3

# Estados com acesso total de escrita (o 'pendente' é a tolerância após falha de pagamento)
ESTADOS_COM_ESCRITA = {"ativo", "pendente"}

PRECOS = {
    "mensal": {"base": 29.00, "iva_pct": 23},
    "anual": {"base": 290.00, "iva_pct": 23},
    "utilizador_extra_mensal": {"base": 9.00, "iva_pct": 23},
}


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    """SQLite devolve datetimes 'naive'; normaliza para UTC."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def iniciar_trial(tenant: Tenant, agora: Optional[datetime] = None) -> None:
    agora = agora or _agora()
    tenant.plano_status = "trial"
    tenant.trial_termina_em = agora + timedelta(days=TRIAL_DIAS)
    tenant.utilizadores_contratados = UTILIZADORES_INCLUIDOS


def escrita_permitida(tenant: Optional[Tenant], agora: Optional[datetime] = None) -> bool:
    """True se a agência pode criar/alterar dados."""
    if tenant is None:
        return False
    status = tenant.plano_status or "ativo"
    if status in ESTADOS_COM_ESCRITA:
        return True
    if status == "trial":
        fim = _aware(tenant.trial_termina_em)
        return fim is not None and fim > (agora or _agora())
    return False


def estado(db: Session, tenant: Tenant, agora: Optional[datetime] = None) -> dict:
    agora = agora or _agora()
    status = tenant.plano_status or "ativo"
    fim_trial = _aware(tenant.trial_termina_em)
    dias_restantes = None
    if status == "trial" and fim_trial is not None:
        segundos = (fim_trial - agora).total_seconds()
        dias_restantes = max(0, int(-(-segundos // 86400)))  # arredonda para cima
    utilizadores_ativos = db.query(User).filter(
        User.agencia_id == tenant.id, User.ativo.is_(True)
    ).count()
    return {
        "plano_status": status,
        "escrita_permitida": escrita_permitida(tenant, agora),
        "trial_termina_em": fim_trial,
        "dias_restantes_trial": dias_restantes,
        "subscricao_valida_ate": _aware(tenant.subscricao_valida_ate),
        "plano_periodo": tenant.plano_periodo,
        "utilizadores_contratados": tenant.utilizadores_contratados or UTILIZADORES_INCLUIDOS,
        "utilizadores_ativos": utilizadores_ativos,
        "precos": PRECOS,
    }


def pode_adicionar_utilizador(db: Session, tenant: Tenant) -> bool:
    """
    Limite de utilizadores ativos: aplica-se no trial e em subscrições Stripe.
    Agências legadas (ativas antes da faturação, sem subscrição Stripe) não são limitadas.
    """
    status = tenant.plano_status or "ativo"
    if status != "trial" and not tenant.stripe_subscription_id:
        return True
    ativos = db.query(User).filter(User.agencia_id == tenant.id, User.ativo.is_(True)).count()
    return ativos < (tenant.utilizadores_contratados or UTILIZADORES_INCLUIDOS)


LIMITE_UTILIZADORES_MSG = (
    "Limite de utilizadores do plano atingido. Aumente os utilizadores contratados na subscrição."
)
