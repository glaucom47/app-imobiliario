"""cria_tabela_store_goals

Revision ID: c119662148b6
Revises: 2295ed8b2647
Create Date: 2026-10-04 18:57:29.281483

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c119662148b6'
down_revision: Union[str, None] = '2295ed8b2647'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'store_goals' not in tables:
        op.create_table(
            'store_goals',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('agencia_id', sa.Integer(), nullable=False),
            sa.Column('ano', sa.Integer(), nullable=False),
            sa.Column('mes', sa.Integer(), nullable=False),
            sa.Column('meta_faturacao', sa.Numeric(precision=12, scale=2), nullable=False, server_default='50000.00'),
            sa.Column('meta_angariacoes', sa.Integer(), nullable=False, server_default='10'),
            sa.Column('meta_visitas', sa.Integer(), nullable=False, server_default='30'),
            sa.Column('meta_propostas', sa.Integer(), nullable=False, server_default='10'),
            sa.Column('meta_cpcv', sa.Integer(), nullable=False, server_default='5'),
            sa.Column('meta_escrituras', sa.Integer(), nullable=False, server_default='5'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.CheckConstraint('mes >= 1 AND mes <= 12', name='chk_store_goal_mes'),
            sa.ForeignKeyConstraint(['agencia_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('agencia_id', 'ano', 'mes', name='uq_store_goals_agencia_ano_mes'),
        )
        op.create_index(op.f('ix_store_goals_agencia_id'), 'store_goals', ['agencia_id'], unique=False)
        op.create_index(op.f('ix_store_goals_ano'), 'store_goals', ['ano'], unique=False)
        op.create_index(op.f('ix_store_goals_id'), 'store_goals', ['id'], unique=False)
        op.create_index(op.f('ix_store_goals_mes'), 'store_goals', ['mes'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_store_goals_mes'), table_name='store_goals')
    op.drop_index(op.f('ix_store_goals_id'), table_name='store_goals')
    op.drop_index(op.f('ix_store_goals_ano'), table_name='store_goals')
    op.drop_index(op.f('ix_store_goals_agencia_id'), table_name='store_goals')
    op.drop_table('store_goals')
