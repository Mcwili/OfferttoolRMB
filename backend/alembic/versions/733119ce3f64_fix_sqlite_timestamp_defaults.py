"""fix_sqlite_timestamp_defaults

Revision ID: 733119ce3f64
Revises: add_validation_reports
Create Date: 2026-01-12 13:31:07.260901

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '733119ce3f64'
down_revision: Union[str, Sequence[str], None] = 'add_validation_reports'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
