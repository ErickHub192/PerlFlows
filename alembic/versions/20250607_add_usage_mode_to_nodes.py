"""add usage_mode column to nodes

Revision ID: 20250607_usage_mode
Revises: 20250606_marketplace_templates
Create Date: 2025-06-07 00:00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '20250607_usage_mode'
down_revision: Union[str, None] = '20250606_marketplace_templates'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    usage_enum = sa.Enum('step', 'tool', 'step_and_tool', 'function', name='nodeusagemode')
    usage_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'nodes',
        sa.Column('usage_mode', usage_enum, nullable=False, server_default='step')
    )


def downgrade() -> None:
    op.drop_column('nodes', 'usage_mode')
    usage_enum = sa.Enum(name='nodeusagemode')
    usage_enum.drop(op.get_bind(), checkfirst=True)
