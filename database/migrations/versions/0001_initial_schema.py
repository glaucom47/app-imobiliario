"""0001_initial_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-28 23:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tabela: tenants (Agências Imobiliárias)
    op.create_table(
        'tenants',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('nif', sa.String(length=50), nullable=True),
        sa.Column('telefone', sa.String(length=50), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('morada', sa.Text(), nullable=True),
        sa.Column('ativo', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tenants_id'), 'tenants', ['id'], unique=False)
    op.create_index(op.f('ix_tenants_slug'), 'tenants', ['slug'], unique=True)
    op.create_index(op.f('ix_tenants_nif'), 'tenants', ['nif'], unique=False)

    # 2. Tabela: users (Usuários com perfis Diretor / Consultor)
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('agencia_id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), server_default='consultor', nullable=False),
        sa.Column('telemovel', sa.String(length=50), nullable=True),
        sa.Column('ativo', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agencia_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_agencia_id'), 'users', ['agencia_id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 3. Tabela: properties (Imóveis e Carteira Ativa)
    op.create_table(
        'properties',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('agencia_id', sa.Integer(), nullable=False),
        sa.Column('consultor_id', sa.Integer(), nullable=False),
        sa.Column('titulo', sa.String(length=255), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('tipologia', sa.String(length=20), nullable=False),
        sa.Column('preco', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('morada', sa.String(length=255), nullable=True),
        sa.Column('concelho', sa.String(length=100), nullable=True),
        sa.Column('distrito', sa.String(length=100), nullable=True),
        sa.Column('regiao_fiscal', sa.String(length=50), server_default='continente', nullable=False),
        sa.Column('area_bruta', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='Ativo', nullable=False),
        sa.Column('nome_proprietario', sa.String(length=255), nullable=False),
        sa.Column('telefone_proprietario', sa.String(length=50), nullable=False),
        sa.Column('nome_comprador', sa.String(length=255), nullable=True),
        sa.Column('telefone_comprador', sa.String(length=50), nullable=True),
        sa.Column('data_escritura', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('Ativo', 'Reservado', 'Vendido')", name='chk_property_status'),
        sa.CheckConstraint("regiao_fiscal IN ('continente', 'madeira', 'acores')", name='chk_property_regiao_fiscal'),
        sa.ForeignKeyConstraint(['agencia_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['consultor_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_properties_id'), 'properties', ['id'], unique=False)
    op.create_index(op.f('ix_properties_agencia_id'), 'properties', ['agencia_id'], unique=False)
    op.create_index(op.f('ix_properties_consultor_id'), 'properties', ['consultor_id'], unique=False)
    op.create_index(op.f('ix_properties_preco'), 'properties', ['preco'], unique=False)
    op.create_index(op.f('ix_properties_status'), 'properties', ['status'], unique=False)

    # 4. Tabela: visits (Visitas & Feedback por Voz)
    op.create_table(
        'visits',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('agencia_id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('consultor_id', sa.Integer(), nullable=False),
        sa.Column('data_visita', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('cliente_nome', sa.String(length=255), nullable=True),
        sa.Column('cliente_telefone', sa.String(length=50), nullable=True),
        sa.Column('audio_duracao_segundos', sa.Integer(), nullable=True),
        sa.Column('transcricao', sa.Text(), nullable=True),
        sa.Column('notas_estruturadas', sa.Text(), nullable=True),
        sa.Column('nivel_interesse', sa.Integer(), nullable=True),
        sa.Column('feedback_enviado_proprietario', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('nivel_interesse IS NULL OR (nivel_interesse >= 1 AND nivel_interesse <= 5)', name='chk_visit_nivel_interesse'),
        sa.ForeignKeyConstraint(['agencia_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['consultor_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_visits_id'), 'visits', ['id'], unique=False)
    op.create_index(op.f('ix_visits_agencia_id'), 'visits', ['agencia_id'], unique=False)
    op.create_index(op.f('ix_visits_property_id'), 'visits', ['property_id'], unique=False)
    op.create_index(op.f('ix_visits_consultor_id'), 'visits', ['consultor_id'], unique=False)
    op.create_index(op.f('ix_visits_data_visita'), 'visits', ['data_visita'], unique=False)

    # 5. Tabela: objection_tags (Catálogo Corporativo de Objeções)
    op.create_table(
        'objection_tags',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('agencia_id', sa.Integer(), nullable=False),
        sa.Column('tag', sa.String(length=100), nullable=False),
        sa.Column('categoria', sa.String(length=50), server_default='geral', nullable=False),
        sa.Column('ativo', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agencia_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agencia_id', 'tag', name='uq_agencia_objection_tag')
    )
    op.create_index(op.f('ix_objection_tags_id'), 'objection_tags', ['id'], unique=False)
    op.create_index(op.f('ix_objection_tags_agencia_id'), 'objection_tags', ['agencia_id'], unique=False)

    # 6. Tabela: visit_objections (Vínculos de Objeções por Visita)
    op.create_table(
        'visit_objections',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('agencia_id', sa.Integer(), nullable=False),
        sa.Column('visit_id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.Column('observacao', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agencia_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['objection_tags.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['visit_id'], ['visits.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_visit_objections_id'), 'visit_objections', ['id'], unique=False)
    op.create_index(op.f('ix_visit_objections_agencia_id'), 'visit_objections', ['agencia_id'], unique=False)
    op.create_index(op.f('ix_visit_objections_visit_id'), 'visit_objections', ['visit_id'], unique=False)
    op.create_index(op.f('ix_visit_objections_property_id'), 'visit_objections', ['property_id'], unique=False)

    # 7. Tabela: contacts (Esfera de Influência, Compradores & Aniversários de Escritura)
    op.create_table(
        'contacts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('agencia_id', sa.Integer(), nullable=False),
        sa.Column('consultor_id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=True),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('telemovel', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('tipo', sa.String(length=50), server_default='comprador', nullable=False),
        sa.Column('data_escritura', sa.Date(), nullable=True),
        sa.Column('anonimizado', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('notas', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agencia_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['consultor_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contacts_id'), 'contacts', ['id'], unique=False)
    op.create_index(op.f('ix_contacts_agencia_id'), 'contacts', ['agencia_id'], unique=False)
    op.create_index(op.f('ix_contacts_consultor_id'), 'contacts', ['consultor_id'], unique=False)
    op.create_index(op.f('ix_contacts_property_id'), 'contacts', ['property_id'], unique=False)
    op.create_index(op.f('ix_contacts_data_escritura'), 'contacts', ['data_escritura'], unique=False)
    op.create_index(op.f('ix_contacts_anonimizado'), 'contacts', ['anonimizado'], unique=False)

    # 8. Tabela: agency_settings (Parametrização Remota da Agência)
    op.create_table(
        'agency_settings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('agencia_id', sa.Integer(), nullable=False),
        sa.Column('spread_referencia', sa.Numeric(precision=5, scale=2), server_default='0.85', nullable=False),
        sa.Column('taxa_stress', sa.Numeric(precision=5, scale=2), server_default='1.50', nullable=False),
        sa.Column('prazo_max_financiamento_anos', sa.Integer(), server_default='30', nullable=False),
        sa.Column('percentual_financiamento_max', sa.Numeric(precision=5, scale=2), server_default='85.00', nullable=False),
        sa.Column('hora_notificacao_aniversario', sa.String(length=5), server_default='09:00', nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agencia_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agencia_id')
    )
    op.create_index(op.f('ix_agency_settings_id'), 'agency_settings', ['id'], unique=False)
    op.create_index(op.f('ix_agency_settings_agencia_id'), 'agency_settings', ['agencia_id'], unique=True)

    # 9. Tabela: audit_logs (Trilhas de Auditoria e Segurança)
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('agencia_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('acao', sa.String(length=100), nullable=False),
        sa.Column('entidade', sa.String(length=100), nullable=False),
        sa.Column('entidade_id', sa.Integer(), nullable=True),
        sa.Column('detalhes', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agencia_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_agencia_id'), 'audit_logs', ['agencia_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_acao'), 'audit_logs', ['acao'], unique=False)
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('agency_settings')
    op.drop_table('contacts')
    op.drop_table('visit_objections')
    op.drop_table('objection_tags')
    op.drop_table('visits')
    op.drop_table('properties')
    op.drop_table('users')
    op.drop_table('tenants')
