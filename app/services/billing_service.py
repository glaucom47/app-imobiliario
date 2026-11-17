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

# Contas e agências fundadoras com acesso vitalício automático permanente
WHITELIST_EMAILS_VITALICIOS = {
    "nanandamenegheti@gmail.com",
    "nanandamenegheti@gm6ail.com",
    "glaucom500@gmail.com",
}

WHITELIST_NOMES_AGENCIA = {
    "portugalia imóveis",
    "portugalia imoveis",
    "portugalia",
}


def is_vitalicio(email: Optional[str] = None, nome_agencia: Optional[str] = None) -> bool:
    """Verifica se o e-mail ou agência pertence à lista de fundadores com acesso vitalício."""
    if email:
        clean_email = email.strip().lower()
        if clean_email in WHITELIST_EMAILS_VITALICIOS or "nanandamenegheti" in clean_email:
            return True
    if nome_agencia:
        clean_nome = nome_agencia.strip().lower()
        if any(w in clean_nome for w in ("portugalia",)):
            return True
    return False


def aplicar_acesso_vitalicio(tenant: Tenant, user: Optional[User] = None, utilizadores: int = 10) -> bool:
    """Aplica o plano vitalício permanente à agência e garante perfil de diretor ao utilizador."""
    alterou = False
    if tenant.plano_status != "ativo":
        tenant.plano_status = "ativo"
        alterou = True
    if tenant.trial_termina_em is not None:
        tenant.trial_termina_em = None
        alterou = True
    if tenant.subscricao_valida_ate is not None:
        tenant.subscricao_valida_ate = None
        alterou = True
    if tenant.plano_periodo != "vitalicio":
        tenant.plano_periodo = "vitalicio"
        alterou = True
    if (tenant.utilizadores_contratados or 0) < utilizadores:
        tenant.utilizadores_contratados = utilizadores
        alterou = True
    if not tenant.ativo:
        tenant.ativo = True
        alterou = True
    if user:
        if not user.ativo:
            user.ativo = True
            alterou = True
        if user.role != "diretor":
            user.role = "diretor"
            alterou = True
    return alterou


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
    if is_vitalicio(tenant.email, tenant.nome):
        aplicar_acesso_vitalicio(tenant)
        return

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
