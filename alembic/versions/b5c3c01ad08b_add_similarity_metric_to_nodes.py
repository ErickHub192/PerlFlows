"""Add similarity_metric to nodes

Revision ID: b5c3c01ad08b
Revises: 98e540cd67a2
Create Date: 2025-04-17 22:08:47.437500

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5c3c01ad08b'
down_revision: Union[str, None] = '98e540cd67a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "nodes",
        sa.Column(
            "similarity_metric",
            sa.String(),
            nullable=False,
            server_default="cosine"
        )
    )


def downgrade() -> None:
    op.drop_column("nodes", "similarity_metric")
