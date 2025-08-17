"""embedding-to-512

Revision ID: 96008afa1db0
Revises: 3534787c86ce
Create Date: 2025-04-18 14:42:23.849558

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '96008afa1db0'
down_revision: Union[str, None] = '3534787c86ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('nodes', 'embedding')

    # 2) Añadir columna nueva de 512 dimensiones
    op.add_column(
        'nodes',
        sa.Column('embedding', Vector(512), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('nodes', 'embedding')
    op.add_column(
        'nodes',
        sa.Column('embedding', Vector(1536), nullable=True)
    )