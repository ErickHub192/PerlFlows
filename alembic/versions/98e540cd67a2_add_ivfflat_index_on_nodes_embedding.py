"""Add ivfflat index on nodes.embedding

Revision ID: 98e540cd67a2
Revises: 63ed37021165
Create Date: 2025-04-17 21:14:30.093547

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '98e540cd67a2'
down_revision: Union[str, None] = '63ed37021165'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2) Cambia el tipo de columna a VECTOR(384) (ajusta 384 a tu dimensión real)
    op.execute(
        "ALTER TABLE nodes ALTER COLUMN embedding "
        "TYPE vector(384) USING embedding::vector"
    )

    
    op.execute(
        "CREATE INDEX idx_nodes_embedding_ivfflat_cosine "
        "ON nodes USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_nodes_embedding_ivfflat_cosine")
    
    op.execute(
        "ALTER TABLE nodes ALTER COLUMN embedding "
        "TYPE double precision[] USING embedding::double precision[]"
    )
