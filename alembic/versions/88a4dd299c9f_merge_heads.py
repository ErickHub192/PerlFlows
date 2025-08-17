"""merge_heads

Revision ID: 88a4dd299c9f
Revises: f018fb42fb1b, fix_service_id_nullable
Create Date: 2025-06-30 12:42:28.176078

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '88a4dd299c9f'
down_revision: Union[str, None] = ('f018fb42fb1b', 'fix_service_id_nullable')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
