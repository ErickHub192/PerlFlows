"""enhance ai_agents with llm references and cost tracking

Revision ID: 20250613_ai_agent_llm_ref
Revises: 20250612_llm_providers
Create Date: 2025-01-06 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250613_ai_agent_llm_ref'
down_revision = '20250612_llm_providers'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add LLM provider and model references to ai_agents
    op.add_column('ai_agents', sa.Column('llm_provider_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('ai_agents', sa.Column('llm_model_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Add usage tracking columns for cost analytics
    op.add_column('ai_agents', sa.Column('total_input_tokens', sa.BigInteger(), nullable=False, server_default='0'))
    op.add_column('ai_agents', sa.Column('total_output_tokens', sa.BigInteger(), nullable=False, server_default='0'))
    op.add_column('ai_agents', sa.Column('total_cost', sa.DECIMAL(precision=12, scale=6), nullable=False, server_default='0'))
    
    # Make model column nullable since we now have llm_model_id
    op.alter_column('ai_agents', 'model', nullable=True)
    
    # Create foreign key constraints
    op.create_foreign_key(
        'fk_ai_agents_llm_provider',
        'ai_agents', 
        'llm_providers',
        ['llm_provider_id'], 
        ['provider_id'],
        ondelete='RESTRICT'
    )
    op.create_foreign_key(
        'fk_ai_agents_llm_model',
        'ai_agents', 
        'llm_models',
        ['llm_model_id'], 
        ['model_id'],
        ondelete='RESTRICT'
    )
    
    # Create indexes for better query performance
    op.create_index('ix_ai_agents_llm_provider_id', 'ai_agents', ['llm_provider_id'])
    op.create_index('ix_ai_agents_llm_model_id', 'ai_agents', ['llm_model_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_ai_agents_llm_model_id', table_name='ai_agents')
    op.drop_index('ix_ai_agents_llm_provider_id', table_name='ai_agents')
    
    # Drop foreign keys
    op.drop_constraint('fk_ai_agents_llm_model', 'ai_agents', type_='foreignkey')
    op.drop_constraint('fk_ai_agents_llm_provider', 'ai_agents', type_='foreignkey')
    
    # Revert model column to non-nullable
    op.alter_column('ai_agents', 'model', nullable=False)
    
    # Drop usage tracking columns
    op.drop_column('ai_agents', 'total_cost')
    op.drop_column('ai_agents', 'total_output_tokens')
    op.drop_column('ai_agents', 'total_input_tokens')
    
    # Drop LLM reference columns
    op.drop_column('ai_agents', 'llm_model_id')
    op.drop_column('ai_agents', 'llm_provider_id')