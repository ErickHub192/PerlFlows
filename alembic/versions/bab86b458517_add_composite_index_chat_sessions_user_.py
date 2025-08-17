"""add_composite_index_chat_sessions_user_created

Revision ID: bab86b458517
Revises: e6b93444781b
Create Date: 2025-08-03 12:48:06.584390

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bab86b458517'
down_revision: Union[str, None] = 'e6b93444781b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 🔧 SIDEBAR PERFORMANCE: Add composite index for chat_sessions list queries
    # This optimizes ORDER BY created_at DESC for specific user_id
    op.create_index(
        'idx_chat_sessions_user_created',
        'chat_sessions',
        ['user_id', 'created_at'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove the composite index
    op.drop_index('idx_chat_sessions_user_created', table_name='chat_sessions')
