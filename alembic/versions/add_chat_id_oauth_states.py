"""add chat_id to oauth_states

Revision ID: add_chat_id_oauth
Revises: add_oauth_config
Create Date: 2025-07-06 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_chat_id_oauth'
down_revision: Union[str, None] = 'add_oauth_config'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add chat_id column to oauth_states table
    op.add_column('oauth_states', sa.Column('chat_id', postgresql.UUID(), nullable=True))
    
    # Note: We set nullable=True initially to allow existing records
    # In a production system, you'd want to backfill existing records first
    # then make it NOT NULL
    

def downgrade() -> None:
    # Drop the chat_id column
    op.drop_column('oauth_states', 'chat_id')