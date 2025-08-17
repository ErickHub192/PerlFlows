"""merge_page_templates

Revision ID: f018fb42fb1b
Revises: page_templates, actions_auth_policy_ref
Create Date: 2025-06-27 14:44:03.988627

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f018fb42fb1b'
down_revision: Union[str, None] = ('page_templates', 'actions_auth_policy_ref')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
