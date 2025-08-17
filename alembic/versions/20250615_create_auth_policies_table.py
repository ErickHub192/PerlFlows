"""create auth_policies table for dynamic auth configuration

Revision ID: 20250615_auth_policies
Revises: 20250613_ai_agent_llm_ref
Create Date: 2025-06-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250615_auth_policies'
down_revision = '20250613_ai_agent_llm_ref'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create auth_policies table
    op.create_table(
        'auth_policies',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('service', sa.String(50), nullable=True),
        sa.Column('mechanism', sa.String(50), nullable=False),
        sa.Column('base_auth_url', sa.String(200), nullable=False),
        sa.Column('max_scopes', postgresql.JSONB(), nullable=True),
        sa.Column('auth_config', postgresql.JSONB(), nullable=True),
        sa.Column('display_name', sa.String(100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon_url', sa.String(200), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        
        # Generated column for auth_string compatibility
        sa.Column(
            'auth_string', 
            sa.String(100),
            sa.Computed(
                "CASE WHEN service IS NOT NULL THEN mechanism || '_' || provider || '_' || service "
                "ELSE mechanism || '_' || provider END"
            ),
            nullable=True
        )
    )
    
    # Create indexes for performance
    op.create_index('idx_auth_policies_provider_service', 'auth_policies', ['provider', 'service'])
    op.create_index('idx_auth_policies_active', 'auth_policies', ['is_active'])
    op.create_index('idx_auth_policies_auth_string', 'auth_policies', ['auth_string'])
    
    # Create unique constraint
    op.create_unique_constraint('uq_auth_policies_provider_service_mechanism', 'auth_policies', ['provider', 'service', 'mechanism'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_auth_policies_auth_string', 'auth_policies')
    op.drop_index('idx_auth_policies_active', 'auth_policies')
    op.drop_index('idx_auth_policies_provider_service', 'auth_policies')
    
    # Drop table
    op.drop_table('auth_policies')