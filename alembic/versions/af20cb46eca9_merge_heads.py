"""Merge heads

Revision ID: af20cb46eca9
Revises: 20250604_webhook, c25f9a4b1a2b
Create Date: 2025-06-05 13:47:35.676667

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'af20cb46eca9'
down_revision: Union[str, None] = ('20250604_webhook', 'c25f9a4b1a2b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
