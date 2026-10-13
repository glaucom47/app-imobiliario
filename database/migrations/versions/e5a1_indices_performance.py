"""Índices compostos de performance (filtros por agencia_id).

Revision ID: e5a1_indices_performance
Revises: a3f1c9e2b7d4
"""
from typing import Sequence, Union

from alembic import op

revision: str = "e5a1_indices_performance"
down_revision: Union[str, None] = "a3f1c9e2b7d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# goals(agencia_id, consultor_id, ano, mes) já é coberto pela UniqueConstraint uq_goals_agencia_consultor_ano_mes;
# contacts(agencia_id) já possui índice simples (index=True).
INDICES = [
    ("ix_visits_agencia_data", "visits", ["agencia_id", "data_visita"]),
    ("ix_visits_agencia_consultor", "visits", ["agencia_id", "consultor_id"]),
    ("ix_properties_agencia_status", "properties", ["agencia_id", "status"]),
    ("ix_properties_agencia_consultor", "properties", ["agencia_id", "consultor_id"]),
    ("ix_pipeline_deals_agencia_fase", "pipeline_deals", ["agencia_id", "fase"]),
    ("ix_pipeline_deals_agencia_consultor", "pipeline_deals", ["agencia_id", "consultor_id"]),
    ("ix_leads_angariacao_agencia_created", "leads_angariacao", ["agencia_id", "created_at"]),
]


def upgrade() -> None:
    for nome, tabela, colunas in INDICES:
        op.create_index(nome, tabela, colunas, unique=False, if_not_exists=True)


def downgrade() -> None:
    for nome, tabela, _ in reversed(INDICES):
        op.drop_index(nome, table_name=tabela, if_exists=True)
