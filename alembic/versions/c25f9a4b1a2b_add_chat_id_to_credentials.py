"""add chat_id column to credentials

Revision ID: c25f9a4b1a2b
Revises: 20250603_flavor_cred
Create Date: 2025-06-10 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c25f9a4b1a2b'
down_revision: Union[str, None] = '20250603_flavor_cred'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('credentials', schema=None) as batch_op:
        batch_op.add_column(sa.Column('chat_id', sa.UUID(), nullable=True))
        batch_op.create_index(batch_op.f('ix_credentials_chat_id'), ['chat_id'], unique=False)
        batch_op.drop_constraint('uq_user_provider_flavor', type_='unique')
        batch_op.create_unique_constraint('uq_user_provider_flavor_chat', ['user_id', 'provider', 'flavor', 'chat_id'])
        batch_op.create_foreign_key('credentials_chat_id_fkey', 'chat_sessions', ['chat_id'], ['session_id'], ondelete='CASCADE')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('credentials', schema=None) as batch_op:
        batch_op.drop_constraint('credentials_chat_id_fkey', type_='foreignkey')
        batch_op.drop_constraint('uq_user_provider_flavor_chat', type_='unique')
        batch_op.create_unique_constraint('uq_user_provider_flavor', ['user_id', 'provider', 'flavor'])
        batch_op.drop_index(batch_op.f('ix_credentials_chat_id'))
        batch_op.drop_column('chat_id')
