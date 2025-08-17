"""drop_memories_table

Revision ID: 287eb5ca6ef1
Revises: c705f76faea9
Create Date: 2025-06-18 19:42:14.293002

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '287eb5ca6ef1'
down_revision: Union[str, None] = 'c705f76faea9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop memories table if it exists."""
    # Drop the table if it exists (legacy cleanup)
    op.execute("DROP TABLE IF EXISTS memories CASCADE")


def downgrade() -> None:
    """Recreate memories table (not recommended)."""
    # Note: This is a destructive migration. 
    # We don't recreate the table since it's legacy and was replaced by handlers
    pass
