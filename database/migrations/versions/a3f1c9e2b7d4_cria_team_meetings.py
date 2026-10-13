"""cria_team_meetings (Reunião de Equipa coletiva com presença e atividade)

Revision ID: a3f1c9e2b7d4
Revises: d7b8caa1b18f
Create Date: 2026-10-13 17:50:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a3f1c9e2b7d4'
down_revision: Union[str, None] = 'd7b8caa1b18f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'team_meetings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('agencia_id', sa.Integer(), nullable=False),
        sa.Column('diretor_id', sa.Integer(), nullable=False),
        sa.Column('data_hora', sa.DateTime(timezone=True), nullable=False),
        sa.Column('tipo', sa.String(length=20), nullable=False),
        sa.Column('notas_gerais', sa.Text(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("tipo IN ('diaria', 'semanal', 'outra')", name='chk_team_meeting_tipo'),
        sa.ForeignKeyConstraint(['agencia_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['diretor_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_team_meetings_id'), 'team_meetings', ['id'], unique=False)
    op.create_index(op.f('ix_team_meetings_agencia_id'), 'team_meetings', ['agencia_id'], unique=False)
    op.create_index(op.f('ix_team_meetings_diretor_id'), 'team_meetings', ['diretor_id'], unique=False)
    op.create_index(op.f('ix_team_meetings_data_hora'), 'team_meetings', ['data_hora'], unique=False)

    op.create_table(
        'team_meeting_attendances',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('meeting_id', sa.Integer(), nullable=False),
        sa.Column('agencia_id', sa.Integer(), nullable=False),
        sa.Column('consultor_id', sa.Integer(), nullable=False),
        sa.Column('presenca', sa.String(length=30), nullable=False),
        sa.Column('contactos', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reunioes_angariacao', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('angariacoes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('exclusivos', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('visitas', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('propostas', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cpcv', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('escrituras', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('nota', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            "presenca IN ('Presente', 'Atraso', 'Ausente', 'AusenciaJustificada')",
            name='chk_team_attendance_presenca',
        ),
        sa.CheckConstraint(
            'contactos >= 0 AND reunioes_angariacao >= 0 AND angariacoes >= 0 AND exclusivos >= 0 '
            'AND visitas >= 0 AND propostas >= 0 AND cpcv >= 0 AND escrituras >= 0',
            name='chk_team_attendance_nao_negativo',
        ),
        sa.ForeignKeyConstraint(['meeting_id'], ['team_meetings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['agencia_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['consultor_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('meeting_id', 'consultor_id', name='uq_team_attendance_meeting_consultor'),
    )
    op.create_index(op.f('ix_team_meeting_attendances_id'), 'team_meeting_attendances', ['id'], unique=False)
    op.create_index(op.f('ix_team_meeting_attendances_meeting_id'), 'team_meeting_attendances', ['meeting_id'], unique=False)
    op.create_index(op.f('ix_team_meeting_attendances_agencia_id'), 'team_meeting_attendances', ['agencia_id'], unique=False)
    op.create_index(op.f('ix_team_meeting_attendances_consultor_id'), 'team_meeting_attendances', ['consultor_id'], unique=False)


def downgrade() -> None:
    op.drop_table('team_meeting_attendances')
    op.drop_table('team_meetings')
