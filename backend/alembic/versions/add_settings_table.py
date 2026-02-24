"""add settings table

Revision ID: add_settings_table
Revises: 733119ce3f64
Create Date: 2025-01-13 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'add_settings_table'
down_revision = 'add_validation_reports'
branch_labels = None
depends_on = None


def upgrade():
    # Erstelle app_settings Tabelle
    op.create_table(
        'app_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Erstelle Index für key
    op.create_index(op.f('ix_app_settings_key'), 'app_settings', ['key'], unique=True)
    op.create_index(op.f('ix_app_settings_id'), 'app_settings', ['id'], unique=False)


def downgrade():
    # Entferne Indexe
    op.drop_index(op.f('ix_app_settings_id'), table_name='app_settings')
    op.drop_index(op.f('ix_app_settings_key'), table_name='app_settings')
    
    # Entferne Tabelle
    op.drop_table('app_settings')
