"""add kind column and ivfflat index to agent_memories

Revision ID: 20250609_agent_memories
Revises: 20250608_extend_agents
Create Date: 2025-06-09 00:00:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '20250609_agent_memories'
down_revision: Union[str, None] = '20250608_extend_agents'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    kind_enum = sa.Enum('vector', 'episodic', name='memorykind')
    kind_enum.create(op.get_bind(), checkfirst=True)
    op.add_column('agent_memories', sa.Column('kind', kind_enum, nullable=False, server_default='episodic'))
    op.drop_constraint('agent_memories_agent_id_fkey', 'agent_memories', type_='foreignkey')
    op.create_foreign_key(None, 'agent_memories', 'ai_agents', ['agent_id'], ['agent_id'], ondelete='CASCADE')
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX IF EXISTS ix_agent_memories_embedding;")
        op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_agent_memories_embedding_ivfflat
          ON agent_memories
          USING ivfflat (embedding vector_cosine_ops)
          WITH (lists = 100);
        """)


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX IF EXISTS ix_agent_memories_embedding_ivfflat;")
    op.drop_constraint('agent_memories_agent_id_fkey', 'agent_memories', type_='foreignkey')
    op.create_foreign_key('agent_memories_agent_id_fkey', 'agent_memories', 'ai_agents', ['agent_id'], ['agent_id'])
    op.drop_column('agent_memories', 'kind')
    kind_enum = sa.Enum(name='memorykind')
    kind_enum.drop(op.get_bind(), checkfirst=True)
