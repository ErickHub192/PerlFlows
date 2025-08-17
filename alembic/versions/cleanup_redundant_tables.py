"""Cleanup redundant auth tables

Revision ID: cleanup_redundant
Revises: kill_flavors
Create Date: 2025-01-26

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'cleanup_redundant'
down_revision = 'kill_flavors'
branch_labels = None
depends_on = None

def upgrade():
    """Eliminar tablas redundantes del sistema auth"""
    
    # 1. Eliminar action_auth_scopes (será reemplazado por actions.auth_policy_id)
    op.drop_table('action_auth_scopes')
    
    # 2. Eliminar telegram_credentials (duplica credentials)
    op.drop_table('telegram_credentials')
    
    print("Cleanup completed: Eliminated redundant auth tables")

def downgrade():
    """Recrear tablas si es necesario (no recomendado)"""
    
    # Recrear action_auth_scopes
    op.create_table('action_auth_scopes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('action_id', sa.UUID(), nullable=False),
        sa.Column('auth_policy_id', sa.Integer(), nullable=False),
        sa.Column('required_scopes', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['action_id'], ['actions.action_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['auth_policy_id'], ['auth_policies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recrear telegram_credentials
    op.create_table('telegram_credentials',
        sa.Column('agent_id', sa.UUID(), nullable=False),
        sa.Column('bot_token', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['ai_agents.agent_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('agent_id')
    )