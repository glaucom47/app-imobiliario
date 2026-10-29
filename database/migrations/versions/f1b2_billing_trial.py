"""Faturação: trial de 7 dias e estado de subscrição por agência.

Revision ID: f1b2_billing_trial
Revises: e5a1_indices_performance
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f1b2_billing_trial"
down_revision: Union[str, None] = "e5a1_indices_performance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agências existentes ficam 'ativo' (server_default) para não interromper clientes atuais.
    op.add_column("tenants", sa.Column("plano_status", sa.String(20), nullable=False, server_default="ativo"))
    op.add_column("tenants", sa.Column("trial_termina_em", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tenants", sa.Column("subscricao_valida_ate", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tenants", sa.Column("plano_periodo", sa.String(10), nullable=True))
    op.add_column("tenants", sa.Column("utilizadores_contratados", sa.Integer(), nullable=False, server_default="3"))
    op.add_column("tenants", sa.Column("stripe_customer_id", sa.String(255), nullable=True))
    op.add_column("tenants", sa.Column("stripe_subscription_id", sa.String(255), nullable=True))
    op.add_column("tenants", sa.Column("termos_aceites_em", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_tenants_stripe_customer_id", "tenants", ["stripe_customer_id"])
    op.create_index("ix_tenants_stripe_subscription_id", "tenants", ["stripe_subscription_id"])


def downgrade() -> None:
    op.drop_index("ix_tenants_stripe_subscription_id", table_name="tenants")
    op.drop_index("ix_tenants_stripe_customer_id", table_name="tenants")
    for col in ("termos_aceites_em", "stripe_subscription_id", "stripe_customer_id", "utilizadores_contratados",
                "plano_periodo", "subscricao_valida_ate", "trial_termina_em", "plano_status"):
        op.drop_column("tenants", col)
