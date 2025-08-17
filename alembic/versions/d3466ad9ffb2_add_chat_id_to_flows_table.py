"""add_chat_id_to_flows_table

Revision ID: d3466ad9ffb2
Revises: page_templates
Create Date: 2025-07-25 07:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd3466ad9ffb2'
down_revision: Union[str, None] = 'page_templates'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add chat_id column to flows table to associate workflows with chats"""
    # Add chat_id column as nullable UUID with foreign key to chat_sessions
    op.add_column('flows', sa.Column(
        'chat_id', 
        postgresql.UUID(as_uuid=True), 
        nullable=True
    ))
    
    # Add foreign key constraint to chat_sessions
    op.create_foreign_key(
        'fk_flows_chat_id_chat_sessions',
        'flows', 'chat_sessions',
        ['chat_id'], ['session_id'],
        ondelete='SET NULL'  # If chat is deleted, keep workflow but clear chat_id
    )
    
    # Add index for performance
    op.create_index('ix_flows_chat_id', 'flows', ['chat_id'])


def downgrade() -> None:
    """Remove chat_id column from flows table"""
    # Drop index
    op.drop_index('ix_flows_chat_id', 'flows')
    
    # Drop foreign key constraint
    op.drop_constraint('fk_flows_chat_id_chat_sessions', 'flows', type_='foreignkey')
    
    # Drop the chat_id column
    op.drop_column('flows', 'chat_id')