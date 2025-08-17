"""create page templates table

Revision ID: page_templates
Revises: 0a063fe41356
Create Date: 2025-06-27 14:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'page_templates'
down_revision: Union[str, None] = '0a063fe41356'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create page_templates table"""
    op.create_table(
        'page_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('template_name', sa.String(length=100), nullable=False, server_default='default'),
        sa.Column('html_content', sa.Text(), nullable=True),
        sa.Column('css_content', sa.Text(), nullable=True),
        sa.Column('js_content', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('customization_prompt', sa.Text(), nullable=True),
        sa.Column('applied_changes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['agent_id'], ['ai_agents.agent_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('agent_id', 'template_name', 'version', name='uq_page_templates_agent_name_version')
    )
    
    # Create indexes
    op.create_index('idx_page_templates_agent_active', 'page_templates', ['agent_id', 'is_active'])
    op.create_index(op.f('ix_page_templates_agent_id'), 'page_templates', ['agent_id'])


def downgrade() -> None:
    """Drop page_templates table"""
    op.drop_index(op.f('ix_page_templates_agent_id'), table_name='page_templates')
    op.drop_index('idx_page_templates_agent_active', table_name='page_templates')
    op.drop_table('page_templates')