"""create action_auth_scopes table for granular action-level auth

Revision ID: 20250615_action_auth_scopes
Revises: 20250615_auth_policies
Create Date: 2025-06-15 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250615_action_auth_scopes'
down_revision = '20250615_auth_policies'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create action_auth_scopes table
    op.create_table(
        'action_auth_scopes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('action_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('actions.action_id', ondelete='CASCADE'), nullable=False),
        sa.Column('auth_policy_id', sa.Integer(), sa.ForeignKey('auth_policies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('required_scopes', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        
        # Note: No computed column here due to PostgreSQL limitations with subqueries
        # auth_string will be generated via application logic or database function
    )
    
    # Create indexes for performance
    op.create_index('idx_action_auth_scopes_action', 'action_auth_scopes', ['action_id'])
    op.create_index('idx_action_auth_scopes_policy', 'action_auth_scopes', ['auth_policy_id'])
    
    # Create unique constraint (one auth policy per action)
    op.create_unique_constraint('uq_action_auth_scopes_action', 'action_auth_scopes', ['action_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_action_auth_scopes_policy', 'action_auth_scopes')
    op.drop_index('idx_action_auth_scopes_action', 'action_auth_scopes')
    
    # Drop table
    op.drop_table('action_auth_scopes')