"""Merge heads

Revision ID: e1d567912011
Revises: 20250605_telegram, af20cb46eca9
Create Date: 2025-06-05 16:13:32.839625

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1d567912011'
down_revision: Union[str, None] = ('20250605_telegram', 'af20cb46eca9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
