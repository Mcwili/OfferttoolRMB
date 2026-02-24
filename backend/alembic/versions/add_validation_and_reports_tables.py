"""add validation and reports tables

Revision ID: add_validation_reports
Revises: d7a2ddc45378
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'add_validation_reports'
down_revision = 'd7a2ddc45378'
branch_labels = None
depends_on = None


def upgrade():
    # Validation Issues Tabelle
    op.create_table(
        'validation_issues',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('project_data_version', sa.Integer(), nullable=True),
        sa.Column('file_id', sa.Integer(), nullable=True),
        sa.Column('kategorie', sa.String(100), nullable=False),
        sa.Column('beschreibung', sa.Text(), nullable=False),
        sa.Column('fundstellen', sa.JSON(), nullable=True),  # SQLite unterstützt JSON
        sa.Column('schweregrad', sa.String(50), nullable=False),
        sa.Column('empfehlung', sa.Text(), nullable=True),
        sa.Column('betroffene_entitaet', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['file_id'], ['project_files.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_validation_issues_project_id', 'validation_issues', ['project_id'])
    op.create_index('ix_validation_issues_schweregrad', 'validation_issues', ['schweregrad'])
    
    # Generated Reports Tabelle
    op.create_table(
        'generated_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('project_data_version', sa.Integer(), nullable=True),
        sa.Column('report_type', sa.String(50), nullable=False),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('file_path', sa.String(1000), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column('generated_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['generated_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_generated_reports_project_id', 'generated_reports', ['project_id'])
    op.create_index('ix_generated_reports_report_type', 'generated_reports', ['report_type'])
    
    # Indizes für JSON-Felder in project_data
    # SQLite unterstützt keine GIN-Indizes, daher einfache Indizes
    # JSON-Abfragen funktionieren trotzdem, sind aber etwas langsamer
    op.create_index('idx_project_data_raeume', 'project_data', ['project_id'], unique=False)
    op.create_index('idx_project_data_anlagen', 'project_data', ['project_id'], unique=False)
    op.create_index('idx_project_data_geraete', 'project_data', ['project_id'], unique=False)


def downgrade():
    # Indizes entfernen
    op.drop_index('idx_project_data_geraete', table_name='project_data')
    op.drop_index('idx_project_data_anlagen', table_name='project_data')
    op.drop_index('idx_project_data_raeume', table_name='project_data')
    
    # Tabellen entfernen
    op.drop_index('ix_generated_reports_report_type', table_name='generated_reports')
    op.drop_index('ix_generated_reports_project_id', table_name='generated_reports')
    op.drop_table('generated_reports')
    
    op.drop_index('ix_validation_issues_schweregrad', table_name='validation_issues')
    op.drop_index('ix_validation_issues_project_id', table_name='validation_issues')
    op.drop_table('validation_issues')
