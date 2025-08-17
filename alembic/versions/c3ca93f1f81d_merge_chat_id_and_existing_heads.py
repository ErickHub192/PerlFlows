"""merge_chat_id_and_existing_heads

Revision ID: c3ca93f1f81d
Revises: 5dde33d18bc6, d3466ad9ffb2
Create Date: 2025-07-24 19:40:14.198197

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3ca93f1f81d'
down_revision: Union[str, None] = ('5dde33d18bc6', 'd3466ad9ffb2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
