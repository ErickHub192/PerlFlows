"""add telegram credentials table and webhook secret

Revision ID: 20250605_telegram
Revises: 20250604_webhook
Create Date: 2025-06-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '20250605_telegram'
down_revision: Union[str, None] = '20250604_webhook'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ai_agents', sa.Column('webhook_secret', sa.String(), nullable=False, server_default=sa.text("''")))
    op.create_table(
        'telegram_credentials',
        sa.Column('agent_id', sa.UUID(), nullable=False),
        sa.Column('bot_token', sa.String(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['ai_agents.agent_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('agent_id')
    )


def downgrade() -> None:
    op.drop_table('telegram_credentials')
    op.drop_column('ai_agents', 'webhook_secret')
