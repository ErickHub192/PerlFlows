"""add_trigger_fields_to_ai_agents

Revision ID: 1351d8abeb26
Revises: 287eb5ca6ef1
Create Date: 2025-06-18 19:43:55.312269

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1351d8abeb26'
down_revision: Union[str, None] = '287eb5ca6ef1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add trigger fields to ai_agents table."""
    # Add activation configuration fields
    op.add_column('ai_agents', sa.Column('activation_type', sa.String(), nullable=False, server_default='manual'))
    op.add_column('ai_agents', sa.Column('trigger_config', sa.dialects.postgresql.JSONB(), nullable=True))
    op.add_column('ai_agents', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('ai_agents', sa.Column('last_triggered', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Remove trigger fields from ai_agents table."""
    op.drop_column('ai_agents', 'last_triggered')
    op.drop_column('ai_agents', 'is_active')
    op.drop_column('ai_agents', 'trigger_config')
    op.drop_column('ai_agents', 'activation_type')
