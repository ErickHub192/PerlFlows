"""make_chat_id_nullable_in_credentials

Revision ID: 5dde33d18bc6
Revises: add_chat_id_oauth
Create Date: 2025-07-24 00:48:43.012576

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5dde33d18bc6'
down_revision: Union[str, None] = 'add_chat_id_oauth'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make chat_id nullable to support global credentials."""
    # Remove the NOT NULL constraint from chat_id column
    op.alter_column('credentials', 'chat_id',
                   existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
                   nullable=True)
    
    # Skip constraint handling for now - we'll do it manually if needed
    print("chat_id is now nullable. Constraints can be handled manually if needed.")


def downgrade() -> None:
    """Revert chat_id to NOT NULL."""
    # Make chat_id NOT NULL again (this will fail if there are NULL values)
    op.alter_column('credentials', 'chat_id',
                   existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
                   nullable=False)
