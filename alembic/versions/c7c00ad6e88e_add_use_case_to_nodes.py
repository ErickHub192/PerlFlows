"""add_use_case_to_nodes

Revision ID: c7c00ad6e88e
Revises: 96008afa1db0
Create Date: 2025-04-18 15:31:50.055795

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7c00ad6e88e'
down_revision: Union[str, None] = '96008afa1db0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'nodes',
        sa.Column('use_case', sa.Text(), nullable=True)
    )

def downgrade() -> None:
    op.drop_column('nodes', 'use_case')
