"""extend ai_agents table with status planner_state error

Revision ID: 20250608_extend_agents
Revises: 20250607_usage_mode
Create Date: 2025-06-08 00:00:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '20250608_extend_agents'
down_revision: Union[str, None] = '20250607_usage_mode'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    status_enum = sa.Enum('queued', 'running', 'paused', 'succeeded', 'failed', name='agentstatus')
    status_enum.create(op.get_bind(), checkfirst=True)
    op.add_column('ai_agents', sa.Column('status', status_enum, nullable=False, server_default='queued'))
    op.add_column('ai_agents', sa.Column('planner_state', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('ai_agents', sa.Column('error', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('ai_agents', 'error')
    op.drop_column('ai_agents', 'planner_state')
    op.drop_column('ai_agents', 'status')
    status_enum = sa.Enum(name='agentstatus')
    status_enum.drop(op.get_bind(), checkfirst=True)
