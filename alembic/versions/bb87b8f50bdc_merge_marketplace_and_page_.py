"""merge marketplace and page customization branches

Revision ID: bb87b8f50bdc
Revises: 0a063fe41356, 20250609_enhance_marketplace_templates
Create Date: 2025-06-09 22:56:57.162166

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bb87b8f50bdc'
down_revision: Union[str, None] = ('0a063fe41356', '20250609_enhance_marketplace_templates')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
