"""Add is_trigger column to actions

Revision ID: ca69ac846c94
Revises: b5c3c01ad08b
Create Date: 2025-04-17 23:25:24.746679

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca69ac846c94'
down_revision: Union[str, None] = 'b5c3c01ad08b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # añade la columna con default false
    op.add_column(
        'actions',
        sa.Column('is_trigger', sa.Boolean(), nullable=False, server_default=sa.text('false'))
    )
    # opcionalmente limpia el server_default
    op.alter_column('actions', 'is_trigger', server_default=None)


def downgrade() -> None:
    op.drop_column('actions', 'is_trigger')
