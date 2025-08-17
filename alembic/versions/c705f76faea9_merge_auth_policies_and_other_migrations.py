"""merge auth_policies and other migrations

Revision ID: c705f76faea9
Revises: 20250615_action_auth_scopes, 409efbf5cd71
Create Date: 2025-06-15 12:43:25.068506

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c705f76faea9'
down_revision: Union[str, None] = ('20250615_action_auth_scopes', '409efbf5cd71')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
