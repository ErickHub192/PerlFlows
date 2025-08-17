"""recrea_ivfflat_concurrently

Revision ID: 3534787c86ce
Revises: ca69ac846c94
Create Date: 2025-04-18 14:27:57.054366

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3534787c86ce'
down_revision: Union[str, None] = 'ca69ac846c94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        # Desactivar timeout para esta sesión
        op.execute("SET statement_timeout = 0;")
        # Crear índice concurrente
        op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_nodes_embedding_ivfflat_cosine
          ON nodes
          USING ivfflat (embedding vector_cosine_ops)
          WITH (lists = 200);
        """)


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_nodes_embedding_ivfflat_cosine;")
